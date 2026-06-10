from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AIOutput,
    AnkiCard,
    DecayStatus,
    Resource,
    ResourceChunk,
    ResourceHeatSignal,
    ResourceStatus,
    ReviewItem,
    Task,
)


def serialize_resource(resource: Resource) -> dict:
    estimated = resource.duration // 180 if resource.duration else 20
    return {
        "id": str(resource.id),
        "title": resource.title,
        "type": resource.type,
        "status": resource.status.value,
        "decay_status": resource.decay_status.value,
        "source_platform": resource.source_platform,
        "original_url": resource.original_url,
        "summary": resource.summary,
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


def task_order():
    return (Task.priority.desc(), Task.created_at.asc())


def touch_resource(db: Session, resource: Resource, signal_type: str = "view", signal_value: float = 1) -> None:
    resource.last_touched_at = datetime.now(UTC)
    resource.heat_score = round((resource.heat_score or 0) + signal_value, 2)
    db.add(ResourceHeatSignal(resource_id=resource.id, user_id=resource.user_id, signal_type=signal_type, signal_value=signal_value))


def create_resource(db: Session, user_id: UUID, payload) -> Resource:
    resource = Resource(
        user_id=user_id,
        title=payload.title,
        type=payload.type,
        original_url=payload.original_url,
        source_platform=payload.source_platform,
        summary=payload.summary or "已进入 Inbox，等待三步快判。",
    )
    db.add(resource)
    db.flush()
    db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="summary", content=resource.summary or resource.title))
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

    status = ResourceStatus.to_process if purpose == "active_learning" else ResourceStatus.to_preview
    resource.status = status
    task = Task(
        user_id=resource.user_id,
        resource_id=resource.id,
        task_type="deep_process" if purpose == "active_learning" else "preview",
        title=f"处理：{resource.title}",
        description="由 Inbox 三步快判生成。",
        priority=4 if estimated_minutes >= 30 else 3,
        estimated_minutes=estimated_minutes,
        due_date=datetime.now(UTC) + timedelta(days=1),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def dashboard(db: Session, user_id: UUID, energy_mode: str = "focus") -> dict:
    pending_stmt = select(Task).where(Task.user_id == user_id, Task.status == "pending").order_by(*task_order()).limit(5)
    pending_tasks = db.scalars(pending_stmt).all()
    inbox_count = db.scalar(select(func.count()).select_from(Resource).where(Resource.user_id == user_id, Resource.status == ResourceStatus.inbox)) or 0
    ai_count = db.scalar(select(func.count()).select_from(AIOutput).where(AIOutput.user_id == user_id, AIOutput.verification_status == "draft")) or 0
    review_count = db.scalar(select(func.count()).select_from(ReviewItem).where(ReviewItem.user_id == user_id, ReviewItem.status == "pending")) or 0
    cold_count = db.scalar(
        select(func.count()).select_from(Resource).where(Resource.user_id == user_id, Resource.decay_status.in_([DecayStatus.cold, DecayStatus.decaying]))
    ) or 0

    if energy_mode == "scan":
        recommended = "快速清理 Inbox 和 10-15 分钟速看任务"
    elif energy_mode == "review":
        recommended = "只显示复习与已沉淀材料，不摄入新资源"
    else:
        recommended = "锁定 1-2 个高价值资源深处理"

    return {
        "energy_mode": energy_mode,
        "recommended": recommended,
        "stats": {"pending_tasks": len(pending_tasks), "inbox": inbox_count, "ai_drafts": ai_count, "reviews": review_count, "cold": cold_count},
        "tasks": [serialize_task(task) for task in pending_tasks],
    }


def search_all(db: Session, user_id: UUID, q: str) -> list[dict]:
    pattern = f"%{q}%"
    resources = db.scalars(
        select(Resource).where(Resource.user_id == user_id, or_(Resource.title.ilike(pattern), Resource.summary.ilike(pattern))).limit(10)
    ).all()
    chunks = db.scalars(select(ResourceChunk).where(ResourceChunk.content.ilike(pattern)).limit(10)).all()
    results = [
        {"kind": "resource", "id": str(item.id), "title": item.title, "snippet": item.summary or item.title, "location": item.original_url}
        for item in resources
    ]
    results.extend(
        {"kind": chunk.chunk_type, "id": str(chunk.id), "title": chunk.heading or "内容片段", "snippet": chunk.content[:180], "location": f"chunk:{chunk.chunk_index}"}
        for chunk in chunks
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
