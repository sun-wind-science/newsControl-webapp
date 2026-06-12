from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.responses import fail, ok
from app.db.session import get_db
from app.models import (
    AIOutput,
    AnkiCard,
    DecayStatus,
    Note,
    Project,
    Resource,
    ResourceChunk,
    ResourceStatus,
    ReviewItem,
    StoredFile,
    Task,
    TaskStatus,
)
from app.schemas.dto import AnnotationCreate, CaptureCreate, EnergyModeIn, InboxDecision, NoteCreate, ProjectCreate, ProjectUpdate, ResourceCreate, ResourceUpdate
from app.services.bootstrap import get_or_create_local_user
from app.services.files import save_upload_file
from app.services.resources import (
    create_capture,
    create_resource,
    dashboard,
    decide_inbox,
    export_anki_csv,
    resource_detail,
    search_all,
    seed_review_and_cards,
    serialize_chunk,
    serialize_note,
    serialize_resource,
    serialize_task,
    set_resource_tags,
    task_order,
    touch_resource,
)

router = APIRouter(prefix="/api")


def local_user(db: Session):
    user = get_or_create_local_user(db)
    seed_review_and_cards(db, user.id)
    return user


def owned_resource(db: Session, user_id: UUID, resource_id: UUID) -> Resource:
    resource = db.get(Resource, resource_id)
    if not resource or resource.user_id != user_id:
        raise HTTPException(status_code=404, detail="资源不存在")
    return resource


def owned_project(db: Session, user_id: UUID, project_id: UUID | None) -> Project | None:
    if project_id is None:
        return None
    project = db.get(Project, project_id)
    if not project or project.user_id != user_id:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def close_open_tasks_for_resource(db: Session, resource_id: UUID) -> None:
    tasks = db.scalars(
        select(Task).where(
            Task.resource_id == resource_id,
            Task.status.in_([TaskStatus.pending, TaskStatus.in_progress]),
        )
    ).all()
    for task in tasks:
        task.status = TaskStatus.skipped
        task.completed_at = datetime.now(UTC)


def serialize_project(project: Project, db: Session) -> dict:
    resource_ids = list(db.scalars(select(Resource.id).where(Resource.project_id == project.id, Resource.status != ResourceStatus.discarded)).all())
    resource_count = db.scalar(select(func.count()).select_from(Resource).where(Resource.project_id == project.id, Resource.status != ResourceStatus.discarded)) or 0
    note_filters = [Note.project_id == project.id]
    if resource_ids:
        note_filters.append(Note.resource_id.in_(resource_ids))
    note_count = db.scalar(select(func.count()).select_from(Note).where(or_(*note_filters))) or 0
    task_count = (
        db.scalar(select(func.count()).select_from(Task).where(Task.project_id == project.id, Task.status.in_([TaskStatus.pending, TaskStatus.in_progress])))
        or 0
    )
    return {
        "id": str(project.id),
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "resource_count": resource_count,
        "note_count": note_count,
        "task_count": task_count,
    }


@router.get("/health")
def health():
    return ok({"status": "ok"}, "操作成功")


@router.get("/session/dashboard")
def get_dashboard(energy_mode: str = "focus", db: Session = Depends(get_db)):
    user = local_user(db)
    return ok(dashboard(db, user.id, energy_mode))


@router.post("/session/energy-mode")
def set_energy_mode(payload: EnergyModeIn):
    return ok({"mode": payload.mode}, "今日能量状态已更新")


@router.post("/capture")
def capture(payload: CaptureCreate, db: Session = Depends(get_db)):
    user = local_user(db)
    owned_project(db, user.id, payload.project_id)
    resource = create_capture(db, user.id, payload)
    return ok(resource_detail(db, resource), "已采集，请确认保存原因和处理计划")


@router.post("/resources")
def add_resource(payload: ResourceCreate, db: Session = Depends(get_db)):
    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="请输入内容")
    user = local_user(db)
    owned_project(db, user.id, payload.project_id)
    resource = create_resource(db, user.id, payload)
    return ok(serialize_resource(resource, db), "资源已进入 Inbox")


@router.get("/resources")
def list_resources(status: str | None = None, resource_type: str | None = None, project_id: UUID | None = None, db: Session = Depends(get_db)):
    user = local_user(db)
    stmt = select(Resource).where(Resource.user_id == user.id).order_by(Resource.created_at.desc())
    if status:
        stmt = stmt.where(Resource.status == status)
    else:
        stmt = stmt.where(Resource.status != ResourceStatus.discarded)
    if resource_type and resource_type != "all":
        stmt = stmt.where(Resource.type == resource_type)
    if project_id:
        owned_project(db, user.id, project_id)
        stmt = stmt.where(Resource.project_id == project_id)
    resources = db.scalars(stmt).all()
    return ok([serialize_resource(item, db) for item in resources])


@router.get("/resources/cold")
def list_cold_resources(db: Session = Depends(get_db)):
    user = local_user(db)
    resources = db.scalars(select(Resource).where(Resource.user_id == user.id, Resource.decay_status.in_([DecayStatus.cold, DecayStatus.decaying]))).all()
    return ok([serialize_resource(item, db) for item in resources])


@router.get("/resources/{resource_id}")
def get_resource(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    touch_resource(db, resource, "view", 0.3)
    db.commit()
    return ok(resource_detail(db, resource))


@router.patch("/resources/{resource_id}")
def update_resource(resource_id: UUID, payload: ResourceUpdate, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "title" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=422, detail="标题不能为空")
        if key == "summary" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=422, detail="请填写保存原因")
        if key == "status" and value is not None:
            try:
                value = ResourceStatus(value)
            except ValueError:
                raise HTTPException(status_code=422, detail="资源状态不支持") from None
        if key == "project_id":
            owned_project(db, user.id, value)
            resource.project_id = value
            continue
        if key == "tags":
            set_resource_tags(db, user.id, resource.id, value)
            continue
        if key == "estimated_minutes":
            resource.duration = max(1, int(value)) * 180 if value is not None else resource.duration
            continue
        if key == "priority":
            resource.heat_score = float(value) if value is not None else resource.heat_score
            continue
        if value is not None:
            setattr(resource, key, value)
    touch_resource(db, resource, "edit", 0.8)
    db.commit()
    return ok(serialize_resource(resource, db), "资源已更新")


@router.delete("/resources/{resource_id}")
def delete_resource(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    resource.status = ResourceStatus.discarded
    resource.decay_status = DecayStatus.discarded
    close_open_tasks_for_resource(db, resource.id)
    db.commit()
    return ok({"id": str(resource.id)}, "资源已放弃")


@router.post("/resources/{resource_id}/archive")
def archive_resource(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    resource.status = ResourceStatus.archived
    resource.archived_at = datetime.now(UTC)
    close_open_tasks_for_resource(db, resource.id)
    db.commit()
    return ok(serialize_resource(resource, db), "资源已归档")


@router.post("/resources/{resource_id}/discard")
def discard_resource(resource_id: UUID, db: Session = Depends(get_db)):
    return delete_resource(resource_id, db)


@router.post("/resources/{resource_id}/touch")
def touch(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    touch_resource(db, resource)
    db.commit()
    return ok(serialize_resource(resource, db), "热度已更新")


@router.post("/resources/{resource_id}/confirm")
def confirm_resource(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    resource.status = ResourceStatus.inbox
    touch_resource(db, resource, "confirm", 1)
    db.commit()
    return ok(serialize_resource(resource, db), "录入信息已确认")


@router.post("/resources/{resource_id}/plan")
def plan_resource(resource_id: UUID, payload: InboxDecision, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    task = decide_inbox(db, resource, payload.keep, payload.purpose, payload.estimated_minutes)
    return ok({"task": serialize_task(task) if task else None}, "处理计划已生成")


@router.get("/resources/{resource_id}/chunks")
def list_chunks(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    chunks = db.scalars(select(ResourceChunk).where(ResourceChunk.resource_id == resource.id).order_by(ResourceChunk.chunk_index.asc())).all()
    return ok([serialize_chunk(chunk) for chunk in chunks])


@router.get("/resources/{resource_id}/annotations")
def list_annotations(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    notes = db.scalars(select(Note).where(Note.resource_id == resource.id).order_by(Note.created_at.desc())).all()
    return ok([serialize_note(note) for note in notes])


@router.post("/resources/{resource_id}/annotations")
def create_annotation(resource_id: UUID, payload: AnnotationCreate, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    note = Note(
        user_id=user.id,
        resource_id=resource.id,
        project_id=resource.project_id,
        title=payload.title or annotation_title(payload.note_type),
        content=payload.content,
        note_type=payload.note_type,
        source_range=payload.source_range,
    )
    db.add(note)
    touch_resource(db, resource, "note", 1.2)
    db.commit()
    db.refresh(note)
    return ok(serialize_note(note), "批注已保存")


@router.post("/resources/{resource_id}/process/complete")
def complete_resource_process(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    resource.status = ResourceStatus.reviewing
    db.add(
        ReviewItem(
            user_id=user.id,
            resource_id=resource.id,
            project_id=resource.project_id,
            review_type="active_recall",
            prompt=f"复述：{resource.title} 的核心价值是什么？",
            next_review_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    db.commit()
    return ok(serialize_resource(resource, db), "处理完成，已安排复习")


@router.get("/inbox/next")
def inbox_next(db: Session = Depends(get_db)):
    user = local_user(db)
    now = datetime.now(UTC)
    resource = db.scalars(
        select(Resource)
        .where(
            Resource.user_id == user.id,
            Resource.status == ResourceStatus.inbox,
            Resource.last_touched_at <= now,
        )
        .order_by(Resource.created_at.asc())
        .limit(1)
    ).first()
    return ok(resource_detail(db, resource) if resource else None)


@router.post("/inbox/{resource_id}/decide")
def inbox_decide(resource_id: UUID, payload: InboxDecision, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    task = decide_inbox(db, resource, payload.keep, payload.purpose, payload.estimated_minutes)
    return ok({"task_id": str(task.id) if task else None}, "快判已提交")


@router.post("/inbox/{resource_id}/defer")
def inbox_defer(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    resource.last_touched_at = datetime.now(UTC) + timedelta(days=1)
    db.commit()
    return ok(serialize_resource(resource, db), "已延后 24 小时")


@router.post("/resources/{resource_id}/summarize")
def summarize(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    output = AIOutput(
        user_id=user.id,
        resource_id=resource.id,
        output_type="summary",
        model_name="local-mock",
        content=f"《{resource.title}》摘要草稿：请确认核心问题、关键结论、可转化知识点和需要二次验证的证据。",
        confidence_score=0.62,
    )
    db.add(output)
    db.commit()
    return ok({"id": str(output.id), "content": output.content, "verification_status": output.verification_status.value}, "AI 摘要草稿已生成")


@router.post("/resources/{resource_id}/generate-anki")
def generate_anki(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    card = AnkiCard(
        user_id=user.id,
        resource_id=resource.id,
        project_id=resource.project_id,
        front=f"{resource.title} 的核心价值是什么？",
        back=resource.summary or "等待你在处理台中补全。",
        tags=f"{resource.type} 自动生成",
        source_reference=resource.title,
    )
    db.add(card)
    db.commit()
    return ok({"id": str(card.id)}, "Anki 草稿卡已生成")


@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    user = local_user(db)
    tasks = db.scalars(
        select(Task)
        .where(Task.user_id == user.id, Task.status.in_([TaskStatus.pending, TaskStatus.in_progress]))
        .order_by(*task_order())
    ).all()
    return ok([serialize_task(task) for task in tasks])


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    task = db.get(Task, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = TaskStatus.done
    task.completed_at = datetime.now(UTC)
    if task.resource_id:
        resource = db.get(Resource, task.resource_id)
        if resource:
            resource.status = ResourceStatus.reviewing
            touch_resource(db, resource, "note", 2)
            existing_review = db.scalars(
                select(ReviewItem)
                .where(
                    ReviewItem.user_id == user.id,
                    ReviewItem.resource_id == resource.id,
                    ReviewItem.status == "pending",
                )
                .limit(1)
            ).first()
            if not existing_review:
                db.add(
                    ReviewItem(
                        user_id=user.id,
                        resource_id=resource.id,
                        project_id=resource.project_id,
                        review_type="active_recall",
                        prompt=f"复述：{resource.title} 的核心价值、一个证据点和下一步动作是什么？",
                        next_review_at=datetime.now(UTC) + timedelta(days=1),
                    )
                )
    db.commit()
    return ok({"id": str(task.id)}, "任务完成，已进入复习沉淀")


@router.post("/notes")
def create_note(payload: NoteCreate, db: Session = Depends(get_db)):
    user = local_user(db)
    if payload.resource_id:
        owned_resource(db, user.id, payload.resource_id)
    if payload.project_id:
        owned_project(db, user.id, payload.project_id)
    note = Note(user_id=user.id, **payload.model_dump())
    db.add(note)
    db.commit()
    return ok(serialize_note(note), "笔记已保存")


@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    user = local_user(db)
    projects = db.scalars(select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())).all()
    return ok([serialize_project(item, db) for item in projects])


@router.post("/projects")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    user = local_user(db)
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="项目名称不能为空")
    project = Project(user_id=user.id, name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return ok(serialize_project(project, db), "项目已创建")


@router.get("/projects/{project_id}")
def get_project(project_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    project = owned_project(db, user.id, project_id)
    resources = db.scalars(
        select(Resource)
        .where(Resource.user_id == user.id, Resource.project_id == project.id, Resource.status != ResourceStatus.discarded)
        .order_by(Resource.last_touched_at.desc())
    ).all()
    note_filters = [Note.project_id == project.id]
    if resources:
        note_filters.append(Note.resource_id.in_([item.id for item in resources]))
    notes = db.scalars(select(Note).where(Note.user_id == user.id, or_(*note_filters)).order_by(Note.created_at.desc()).limit(20)).all()
    tasks = db.scalars(
        select(Task)
        .where(Task.user_id == user.id, Task.project_id == project.id, Task.status.in_([TaskStatus.pending, TaskStatus.in_progress]))
        .order_by(*task_order())
    ).all()
    return ok(
        {
            "project": serialize_project(project, db),
            "resources": [serialize_resource(item, db) for item in resources],
            "notes": [serialize_note(item) for item in notes],
            "tasks": [serialize_task(item) for item in tasks],
        }
    )


@router.patch("/projects/{project_id}")
def update_project(project_id: UUID, payload: ProjectUpdate, db: Session = Depends(get_db)):
    user = local_user(db)
    project = owned_project(db, user.id, project_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "name" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(status_code=422, detail="项目名称不能为空")
        if value is not None:
            setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return ok(serialize_project(project, db), "项目已更新")


@router.get("/reviews/today")
def reviews_today(db: Session = Depends(get_db)):
    user = local_user(db)
    reviews = db.scalars(select(ReviewItem).where(ReviewItem.user_id == user.id, ReviewItem.status == "pending").order_by(ReviewItem.next_review_at.asc())).all()
    return ok([{"id": str(item.id), "prompt": item.prompt, "review_type": item.review_type, "interval_days": item.interval_days} for item in reviews])


@router.post("/reviews/{review_id}/complete")
def complete_review(review_id: UUID, quality: str = "known", db: Session = Depends(get_db)):
    review = db.get(ReviewItem, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="复习项不存在")
    review.status = "done"
    review.interval_days = 3 if quality == "known" else 1
    review.next_review_at = datetime.now(UTC) + timedelta(days=review.interval_days)
    db.commit()
    return ok({"id": str(review.id), "next_review_at": review.next_review_at.isoformat()}, "复习已记录")


@router.get("/search")
def search(q: str, db: Session = Depends(get_db)):
    user = local_user(db)
    if not q.strip():
        return ok([])
    return ok(search_all(db, user.id, q.strip()))


@router.post("/export/anki")
def export_anki(db: Session = Depends(get_db)):
    user = local_user(db)
    csv = export_anki_csv(db, user.id)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=anki.csv"})


@router.post("/uploads/file")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = local_user(db)
    resource = save_upload_file(db, user.id, file)
    return ok(resource_detail(db, resource), "文件已上传，请补充保存原因和处理计划")


@router.get("/resources/{resource_id}/file")
def get_resource_file(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = owned_resource(db, user.id, resource_id)
    stored = db.scalars(select(StoredFile).where(StoredFile.resource_id == resource.id).order_by(StoredFile.created_at.desc()).limit(1)).first()
    if not stored:
        raise HTTPException(status_code=404, detail="文件不存在")
    return ok({"file": {"id": str(stored.id), "name": stored.file_name, "download_url": f"/api/files/{stored.id}/download"}})


@router.get("/files/{file_id}/download")
def download_file(file_id: UUID, db: Session = Depends(get_db)):
    stored = db.get(StoredFile, file_id)
    if not stored:
        raise HTTPException(status_code=404, detail="文件不存在")
    path = Path(stored.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件已丢失")
    return FileResponse(path, filename=stored.file_name, media_type=stored.file_type or "application/octet-stream")


def annotation_title(note_type: str) -> str:
    names = {
        "annotation": "普通批注",
        "excerpt": "摘录",
        "question": "问题",
        "evidence": "证据",
        "action": "行动项",
        "anki_candidate": "Anki 候选",
        "project_material": "项目素材",
    }
    return names.get(note_type, "批注")
