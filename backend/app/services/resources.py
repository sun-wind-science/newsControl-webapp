from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AIOutput,
    AnkiCard,
    DecayStatus,
    Note,
    Resource,
    ResourceChunk,
    ResourceHeatSignal,
    ResourceMetadata,
    ResourceStatus,
    ResourceTag,
    ReviewItem,
    StoredFile,
    Tag,
    Task,
    TaskStatus,
)


def summarize_url(value: str) -> str:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(value)
        path = "/".join([item for item in parsed.path.split("/") if item][:2])
        return f"{parsed.netloc}/{path}" if path else parsed.netloc
    except Exception:
        return value[:80]


def fetch_webpage_metadata(url: str) -> dict:
    try:
        from urllib.parse import urlparse

        import httpx
        from bs4 import BeautifulSoup

        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=6,
            headers={"User-Agent": "ContentDigestBot/0.1 (+local personal archive)"},
        )
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, "html.parser")

        def meta_value(*selectors: tuple[str, str]) -> str:
            for attr, value in selectors:
                found = soup.find("meta", attrs={attr: value})
                content = found.get("content") if found else ""
                if content:
                    return str(content).strip()
            return ""

        title = meta_value(("property", "og:title"), ("name", "twitter:title")) or (soup.title.string.strip() if soup.title and soup.title.string else "")
        description = meta_value(("property", "og:description"), ("name", "description"), ("name", "twitter:description"))
        site_name = meta_value(("property", "og:site_name")) or urlparse(str(response.url)).netloc

        readable_text = ""
        try:
            from readability import Document

            doc = Document(html)
            readable_html = doc.summary(html_partial=True)
            readable_text = BeautifulSoup(readable_html, "html.parser").get_text("\n", strip=True)
        except Exception:
            readable_text = soup.get_text("\n", strip=True)

        return {
            "title": title[:500],
            "description": description[:2000],
            "site_name": site_name[:120],
            "text": readable_text[:16000],
            "final_url": str(response.url),
        }
    except Exception:
        return {}


def infer_resource_type(file_name: str | None = None, content_type: str | None = None, explicit: str | None = None) -> str:
    if explicit and explicit != "auto":
        return explicit
    name = (file_name or "").lower()
    ctype = (content_type or "").lower()
    if name.endswith(".pdf") or "pdf" in ctype:
        return "pdf"
    if name.endswith((".doc", ".docx")):
        return "word"
    if name.endswith((".mp4", ".mov", ".mkv", ".webm")) or ctype.startswith("video/"):
        return "video"
    if name.endswith((".txt", ".md", ".markdown")) or ctype.startswith("text/"):
        return "text"
    return "mixed"


def parse_tags(value: str | None) -> list[str]:
    if not value:
        return []
    raw_items = value.replace(",", " ").replace("，", " ").split()
    seen: set[str] = set()
    tags: list[str] = []
    for item in raw_items:
        name = item.strip().lstrip("#")
        if name and name not in seen:
            seen.add(name)
            tags.append(name)
    return tags


def get_resource_tags(db: Session, resource_id: UUID) -> list[str]:
    stmt = (
        select(Tag.name)
        .join(ResourceTag, ResourceTag.tag_id == Tag.id)
        .where(ResourceTag.resource_id == resource_id)
        .order_by(Tag.name.asc())
    )
    return list(db.scalars(stmt).all())


def set_resource_tags(db: Session, user_id: UUID, resource_id: UUID, value: str | None) -> None:
    db.query(ResourceTag).filter(ResourceTag.resource_id == resource_id).delete()
    for name in parse_tags(value):
        tag = db.scalars(select(Tag).where(Tag.user_id == user_id, Tag.name == name).limit(1)).first()
        if not tag:
            tag = Tag(user_id=user_id, name=name)
            db.add(tag)
            db.flush()
        db.add(ResourceTag(resource_id=resource_id, tag_id=tag.id))


def serialize_resource(resource: Resource, db: Session | None = None) -> dict:
    estimated = resource.duration // 180 if resource.duration else 20
    metadata = db.scalars(select(ResourceMetadata).where(ResourceMetadata.resource_id == resource.id).limit(1)).first() if db else None
    return {
        "id": str(resource.id),
        "title": resource.title,
        "type": resource.type,
        "status": resource.status.value,
        "decay_status": resource.decay_status.value,
        "source_platform": resource.source_platform,
        "original_url": resource.original_url,
        "file_url": resource.file_url,
        "source_description": metadata.description if metadata else None,
        "summary": resource.summary,
        "tags": get_resource_tags(db, resource.id) if db else [],
        "heat_score": resource.heat_score,
        "estimated_minutes": max(10, min(90, estimated)),
        "created_at": resource.created_at.isoformat(),
        "last_touched_at": resource.last_touched_at.isoformat(),
    }


def serialize_task(task: Task) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "task_type": task.task_type,
        "priority": task.priority,
        "status": task.status.value,
        "estimated_minutes": task.estimated_minutes,
        "resource_id": str(task.resource_id) if task.resource_id else None,
    }


def serialize_note(note: Note) -> dict:
    return {
        "id": str(note.id),
        "title": note.title,
        "content": note.content,
        "note_type": note.note_type,
        "source_range": note.source_range,
        "created_at": note.created_at.isoformat(),
    }


def serialize_file(file: StoredFile) -> dict:
    return {
        "id": str(file.id),
        "resource_id": str(file.resource_id) if file.resource_id else None,
        "file_name": file.file_name,
        "file_type": file.file_type,
        "file_size": file.file_size,
        "storage_path": file.storage_path,
        "download_url": f"/api/files/{file.id}/download",
    }


def serialize_ai_output(output: AIOutput) -> dict:
    return {
        "id": str(output.id),
        "output_type": output.output_type,
        "content": output.content,
        "verification_status": output.verification_status.value,
        "created_at": output.created_at.isoformat(),
    }


def serialize_anki_card(card: AnkiCard) -> dict:
    return {
        "id": str(card.id),
        "front": card.front,
        "back": card.back,
        "tags": card.tags,
        "exported": card.exported,
        "created_at": card.created_at.isoformat(),
    }


def serialize_chunk(chunk: ResourceChunk) -> dict:
    return {
        "id": str(chunk.id),
        "resource_id": str(chunk.resource_id),
        "chunk_index": chunk.chunk_index,
        "chunk_type": chunk.chunk_type,
        "content": chunk.content,
        "page_number": chunk.page_number,
        "start_time": chunk.start_time,
        "end_time": chunk.end_time,
        "heading": chunk.heading,
    }


def task_order():
    return (Task.priority.desc(), Task.created_at.asc())


def touch_resource(db: Session, resource: Resource, signal_type: str = "view", signal_value: float = 1) -> None:
    resource.last_touched_at = datetime.now(UTC)
    resource.heat_score = round((resource.heat_score or 0) + signal_value, 2)
    db.add(ResourceHeatSignal(resource_id=resource.id, user_id=resource.user_id, signal_type=signal_type, signal_value=signal_value))


def create_resource(db: Session, user_id: UUID, payload) -> Resource:
    title = payload.title.strip()
    resource = Resource(
        user_id=user_id,
        title=title,
        type=payload.type,
        original_url=payload.original_url,
        source_platform=payload.source_platform,
        summary=payload.summary or "已进入 Inbox，等待补充保存原因和处理计划。",
    )
    db.add(resource)
    db.flush()
    set_resource_tags(db, user_id, resource.id, None)
    db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="summary", content=resource.summary or resource.title))
    db.commit()
    db.refresh(resource)
    return resource


def create_capture(db: Session, user_id: UUID, payload) -> Resource:
    content = payload.content.strip()
    is_url = content.startswith("http://") or content.startswith("https://")
    metadata = fetch_webpage_metadata(content) if is_url else {}
    title = (payload.title or "").strip()
    if not title:
      title = metadata.get("title") or (summarize_url(content) if is_url else content[:60])
    summary = (payload.summary or "").strip()
    if not summary:
        source_description = metadata.get("description")
        summary = f"来源描述：{source_description}\n保存原因：请补充为什么保存它、后续要如何处理。" if source_description else "请补充：为什么保存它？后续要如何处理？"

    resource = Resource(
        user_id=user_id,
        title=title,
        type="webpage" if is_url else payload.capture_type,
        original_url=metadata.get("final_url") or (content if is_url else None),
        source_platform=payload.source_platform or (metadata.get("site_name") if is_url else "手动录入") or "链接采集",
        summary=summary,
        duration=payload.estimated_minutes * 180,
        heat_score=float(payload.priority),
    )
    db.add(resource)
    db.flush()
    set_resource_tags(db, user_id, resource.id, payload.tags)
    if is_url and metadata:
        db.add(
            ResourceMetadata(
                resource_id=resource.id,
                platform=metadata.get("site_name"),
                description=metadata.get("description"),
                raw_metadata_json={key: value for key, value in metadata.items() if key != "text"},
            )
        )
    chunk_content = metadata.get("text") if is_url and metadata.get("text") else content
    db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="webpage_text" if is_url else "paragraph", content=chunk_content, heading="网页正文" if is_url and metadata.get("text") else "采集内容"))
    db.add(
        Note(
            user_id=user_id,
            resource_id=resource.id,
            title="录入计划",
            content=f"处理目标：{payload.process_goal}\n预计时间：{payload.estimated_minutes} 分钟\n下一步：{payload.next_action}\n标签：{payload.tags or '未设置'}",
            note_type="action",
        )
    )
    db.commit()
    db.refresh(resource)
    return resource


def decide_inbox(db: Session, resource: Resource, keep: bool, purpose: str, estimated_minutes: int) -> Task | None:
    touch_resource(db, resource, "triage", 1.5)
    if not keep:
        resource.status = ResourceStatus.discarded
        resource.decay_status = DecayStatus.discarded
        db.commit()
        return None

    if purpose == "reference":
        resource.status = ResourceStatus.archived
        resource.archived_at = datetime.now(UTC)
        db.add(
            Note(
                user_id=resource.user_id,
                resource_id=resource.id,
                title="参考存档",
                content="已作为参考资料留存，不进入今日任务台。",
                note_type="action",
            )
        )
        db.commit()
        return None

    existing_task = db.scalars(
        select(Task)
        .where(Task.resource_id == resource.id, Task.status.in_([TaskStatus.pending, TaskStatus.in_progress]))
        .order_by(*task_order())
        .limit(1)
    ).first()
    if existing_task:
        resource.status = ResourceStatus.to_process if purpose == "active_learning" else ResourceStatus.to_preview
        existing_task.estimated_minutes = estimated_minutes
        existing_task.priority = max(existing_task.priority, 4 if estimated_minutes >= 30 else 3)
        db.commit()
        db.refresh(existing_task)
        return existing_task

    status = ResourceStatus.to_process if purpose == "active_learning" else ResourceStatus.to_preview
    resource.status = status
    task = Task(
        user_id=resource.user_id,
        resource_id=resource.id,
        task_type="deep_process" if purpose == "active_learning" else "preview",
        title=f"处理：{resource.title}",
        description="由 Inbox 快判生成。请在处理台完成核心价值、知识点和下一步动作。",
        priority=4 if estimated_minutes >= 30 else 3,
        estimated_minutes=estimated_minutes,
        due_date=datetime.now(UTC) + timedelta(days=1),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def dashboard(db: Session, user_id: UUID, energy_mode: str = "focus") -> dict:
    now = datetime.now(UTC)
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    stale_before = datetime.now(UTC) - timedelta(days=7)
    pending_stmt = select(Task).where(Task.user_id == user_id, Task.status == "pending").order_by(*task_order()).limit(5)
    pending_tasks = db.scalars(pending_stmt).all()
    inbox_count = db.scalar(
        select(func.count()).select_from(Resource).where(Resource.user_id == user_id, Resource.status == ResourceStatus.inbox, Resource.last_touched_at <= now)
    ) or 0
    captured_today = db.scalar(select(func.count()).select_from(Resource).where(Resource.user_id == user_id, Resource.created_at >= today_start)) or 0
    processed_today = db.scalar(select(func.count()).select_from(Task).where(Task.user_id == user_id, Task.status == TaskStatus.done, Task.completed_at >= today_start)) or 0
    stale_count = db.scalar(
        select(func.count())
        .select_from(Resource)
        .where(
            Resource.user_id == user_id,
            Resource.created_at < stale_before,
            Resource.status.in_([ResourceStatus.inbox, ResourceStatus.to_preview, ResourceStatus.to_process]),
        )
    ) or 0
    ai_count = db.scalar(select(func.count()).select_from(AIOutput).where(AIOutput.user_id == user_id, AIOutput.verification_status == "draft")) or 0
    review_count = db.scalar(select(func.count()).select_from(ReviewItem).where(ReviewItem.user_id == user_id, ReviewItem.status == "pending")) or 0
    cold_count = db.scalar(
        select(func.count()).select_from(Resource).where(Resource.user_id == user_id, Resource.decay_status.in_([DecayStatus.cold, DecayStatus.decaying]))
    ) or 0
    annotated_count = db.scalar(select(func.count(func.distinct(Note.resource_id))).where(Note.user_id == user_id, Note.resource_id.is_not(None))) or 0

    if energy_mode == "scan":
        recommended = "快速清理 Inbox 和 10-15 分钟速看任务"
    elif energy_mode == "review":
        recommended = "只显示复习与已沉淀材料，不摄入新资源"
    else:
        recommended = "锁定 1-2 个高价值资源深处理"

    return {
        "energy_mode": energy_mode,
        "recommended": recommended,
        "stats": {
            "pending_tasks": len(pending_tasks),
            "inbox": inbox_count,
            "captured_today": captured_today,
            "processed_today": processed_today,
            "stale": stale_count,
            "ai_drafts": ai_count,
            "reviews": review_count,
            "cold": cold_count,
            "annotated": annotated_count,
        },
        "tasks": [serialize_task(task) for task in pending_tasks],
    }


def resource_detail(db: Session, resource: Resource) -> dict:
    notes = db.scalars(select(Note).where(Note.resource_id == resource.id).order_by(Note.created_at.desc())).all()
    chunks = db.scalars(select(ResourceChunk).where(ResourceChunk.resource_id == resource.id).order_by(ResourceChunk.chunk_index.asc()).limit(50)).all()
    files = db.scalars(select(StoredFile).where(StoredFile.resource_id == resource.id).order_by(StoredFile.created_at.desc())).all()
    tasks = db.scalars(select(Task).where(Task.resource_id == resource.id).order_by(*task_order())).all()
    ai_outputs = db.scalars(select(AIOutput).where(AIOutput.resource_id == resource.id).order_by(AIOutput.created_at.desc()).limit(10)).all()
    anki_cards = db.scalars(select(AnkiCard).where(AnkiCard.resource_id == resource.id).order_by(AnkiCard.created_at.desc()).limit(10)).all()
    return {
        "resource": serialize_resource(resource, db),
        "notes": [serialize_note(note) for note in notes],
        "chunks": [serialize_chunk(chunk) for chunk in chunks],
        "files": [serialize_file(file) for file in files],
        "tasks": [serialize_task(task) for task in tasks],
        "ai_outputs": [serialize_ai_output(output) for output in ai_outputs],
        "anki_cards": [serialize_anki_card(card) for card in anki_cards],
    }


def search_all(db: Session, user_id: UUID, q: str) -> list[dict]:
    pattern = f"%{q}%"
    resources = db.scalars(
        select(Resource).where(Resource.user_id == user_id, or_(Resource.title.ilike(pattern), Resource.summary.ilike(pattern))).limit(15)
    ).all()
    tagged_resource_ids = db.scalars(
        select(ResourceTag.resource_id)
        .join(Tag, Tag.id == ResourceTag.tag_id)
        .where(Tag.user_id == user_id, Tag.name.ilike(pattern))
        .limit(15)
    ).all()
    metadata_resource_ids = db.scalars(
        select(ResourceMetadata.resource_id)
        .join(Resource, Resource.id == ResourceMetadata.resource_id)
        .where(Resource.user_id == user_id, ResourceMetadata.description.ilike(pattern))
        .limit(15)
    ).all()
    related_ids = list(tagged_resource_ids) + list(metadata_resource_ids)
    if related_ids:
        related_resources = db.scalars(select(Resource).where(Resource.id.in_(related_ids))).all()
        existing_ids = {item.id for item in resources}
        resources.extend([item for item in related_resources if item.id not in existing_ids])
    chunks = db.scalars(select(ResourceChunk).where(ResourceChunk.content.ilike(pattern)).limit(15)).all()
    notes = db.scalars(select(Note).where(Note.user_id == user_id, or_(Note.title.ilike(pattern), Note.content.ilike(pattern))).limit(15)).all()

    results = [
        {"kind": "resource", "id": str(item.id), "title": item.title, "snippet": item.summary or item.title, "location": item.original_url}
        for item in resources
    ]
    results.extend(
        {"kind": chunk.chunk_type, "id": str(chunk.id), "title": chunk.heading or "内容片段", "snippet": chunk.content[:180], "location": f"chunk:{chunk.chunk_index}", "resource_id": str(chunk.resource_id)}
        for chunk in chunks
    )
    results.extend(
        {"kind": note.note_type, "id": str(note.id), "title": note.title, "snippet": note.content[:180], "location": note.source_range, "resource_id": str(note.resource_id) if note.resource_id else None}
        for note in notes
    )
    return results


def export_anki_csv(db: Session, user_id: UUID) -> str:
    cards = db.scalars(select(AnkiCard).where(AnkiCard.user_id == user_id)).all()
    lines = ["front,back,tags,source,difficulty"]
    for card in cards:
        lines.append(f'"{card.front}","{card.back}","{card.tags or ""}","{card.source_reference or ""}","{card.difficulty}"')
    return "\n".join(lines)


def seed_review_and_cards(db: Session, user_id: UUID) -> None:
    existing = db.scalars(select(AnkiCard).where(AnkiCard.user_id == user_id).limit(1)).first()
    if existing:
        return
    card = AnkiCard(
        user_id=user_id,
        front="为什么 AI 草稿不能直接进入正式笔记？",
        back="因为系统要求用户确认，科研结论默认保持草稿状态，避免误把生成内容当证据。",
        tags="系统设计 AI可信度",
        source_reference="设计方案",
    )
    db.add(card)
    db.flush()
    db.add(ReviewItem(user_id=user_id, card_id=card.id, prompt=card.front, next_review_at=datetime.now(UTC)))
    db.commit()


def storage_root() -> Path:
    return Path("storage") / "users" / "local" / "resources"
