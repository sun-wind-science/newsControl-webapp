from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.responses import ok
from app.db.session import get_db
from app.models import AIOutput, AnkiCard, DecayStatus, Note, Project, Resource, ResourceStatus, ReviewItem, Task, TaskStatus
from app.schemas.dto import EnergyModeIn, InboxDecision, NoteCreate, ProjectCreate, ResourceCreate, ResourceUpdate
from app.services.bootstrap import get_or_create_local_user
from app.services.resources import create_resource, dashboard, decide_inbox, export_anki_csv, search_all, seed_review_and_cards, serialize_resource, serialize_task, task_order, touch_resource

router = APIRouter(prefix="/api")


def local_user(db: Session):
    user = get_or_create_local_user(db)
    seed_review_and_cards(db, user.id)
    return user


@router.get("/health")
def health():
    return ok({"status": "ok"})


@router.get("/session/dashboard")
def get_dashboard(energy_mode: str = "focus", db: Session = Depends(get_db)):
    user = local_user(db)
    return ok(dashboard(db, user.id, energy_mode))


@router.post("/session/energy-mode")
def set_energy_mode(payload: EnergyModeIn):
    return ok({"mode": payload.mode}, "今日能量状态已更新")


@router.post("/resources")
def add_resource(payload: ResourceCreate, db: Session = Depends(get_db)):
    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="请输入内容")
    user = local_user(db)
    resource = create_resource(db, user.id, payload)
    return ok(serialize_resource(resource), "资源已进入 Inbox")


@router.get("/resources")
def list_resources(status: str | None = None, db: Session = Depends(get_db)):
    user = local_user(db)
    stmt = select(Resource).where(Resource.user_id == user.id).order_by(Resource.created_at.desc())
    if status:
        stmt = stmt.where(Resource.status == status)
    resources = db.scalars(stmt).all()
    return ok([serialize_resource(item) for item in resources])


@router.get("/resources/cold")
def list_cold_resources(db: Session = Depends(get_db)):
    user = local_user(db)
    resources = db.scalars(select(Resource).where(Resource.user_id == user.id, Resource.decay_status.in_([DecayStatus.cold, DecayStatus.decaying]))).all()
    return ok([serialize_resource(item) for item in resources])


@router.get("/resources/{resource_id}")
def get_resource(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = db.get(Resource, resource_id)
    if not resource or resource.user_id != user.id:
        raise HTTPException(status_code=404, detail="资源不存在")
    touch_resource(db, resource, "view", 0.3)
    db.commit()
    return ok(serialize_resource(resource))


@router.patch("/resources/{resource_id}")
def update_resource(resource_id: UUID, payload: ResourceUpdate, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = db.get(Resource, resource_id)
    if not resource or resource.user_id != user.id:
        raise HTTPException(status_code=404, detail="资源不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(resource, key, value)
    touch_resource(db, resource, "edit", 0.8)
    db.commit()
    return ok(serialize_resource(resource))


@router.delete("/resources/{resource_id}")
def delete_resource(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = db.get(Resource, resource_id)
    if not resource or resource.user_id != user.id:
        raise HTTPException(status_code=404, detail="资源不存在")
    resource.status = ResourceStatus.discarded
    resource.decay_status = DecayStatus.discarded
    db.commit()
    return ok({"id": str(resource.id)}, "资源已放弃")


@router.post("/resources/{resource_id}/archive")
def archive_resource(resource_id: UUID, db: Session = Depends(get_db)):
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    resource.status = ResourceStatus.archived
    resource.archived_at = datetime.now(UTC)
    db.commit()
    return ok(serialize_resource(resource), "资源已归档")


@router.post("/resources/{resource_id}/discard")
def discard_resource(resource_id: UUID, db: Session = Depends(get_db)):
    return delete_resource(resource_id, db)


@router.post("/resources/{resource_id}/touch")
def touch(resource_id: UUID, db: Session = Depends(get_db)):
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    touch_resource(db, resource)
    db.commit()
    return ok(serialize_resource(resource), "热度已更新")


@router.get("/inbox/next")
def inbox_next(db: Session = Depends(get_db)):
    user = local_user(db)
    resource = db.scalars(select(Resource).where(Resource.user_id == user.id, Resource.status == ResourceStatus.inbox).order_by(Resource.created_at.asc()).limit(1)).first()
    return ok(serialize_resource(resource) if resource else None)


@router.post("/inbox/{resource_id}/decide")
def inbox_decide(resource_id: UUID, payload: InboxDecision, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = db.get(Resource, resource_id)
    if not resource or resource.user_id != user.id:
        raise HTTPException(status_code=404, detail="资源不存在")
    task = decide_inbox(db, resource, payload.keep, payload.purpose, payload.estimated_minutes)
    return ok({"task_id": str(task.id) if task else None}, "快判已提交")


@router.post("/inbox/{resource_id}/defer")
def inbox_defer(resource_id: UUID, db: Session = Depends(get_db)):
    resource = db.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    resource.last_touched_at = datetime.now(UTC) + timedelta(days=1)
    db.commit()
    return ok(serialize_resource(resource), "已延后 24 小时")


@router.post("/resources/{resource_id}/summarize")
def summarize(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = db.get(Resource, resource_id)
    if not resource or resource.user_id != user.id:
        raise HTTPException(status_code=404, detail="资源不存在")
    output = AIOutput(
        user_id=user.id,
        resource_id=resource.id,
        output_type="summary",
        model_name="local-mock",
        content=f"这是《{resource.title}》的结构化摘要草稿：核心问题、主要结论、可转化知识点仍需你确认。",
        confidence_score=0.62,
    )
    db.add(output)
    db.commit()
    return ok({"id": str(output.id), "content": output.content, "verification_status": output.verification_status.value}, "AI 摘要草稿已生成")


@router.post("/resources/{resource_id}/generate-anki")
def generate_anki(resource_id: UUID, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = db.get(Resource, resource_id)
    if not resource or resource.user_id != user.id:
        raise HTTPException(status_code=404, detail="资源不存在")
    card = AnkiCard(user_id=user.id, resource_id=resource.id, front=f"{resource.title} 的核心价值是什么？", back=resource.summary or "等待你在处理台中补全。", tags=f"{resource.type} 自动生成", source_reference=resource.title)
    db.add(card)
    db.commit()
    return ok({"id": str(card.id)}, "Anki 草稿卡已生成")


@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    user = local_user(db)
    tasks = db.scalars(select(Task).where(Task.user_id == user.id).order_by(*task_order())).all()
    return ok([serialize_task(task) for task in tasks])


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: UUID, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = TaskStatus.done
    task.completed_at = datetime.now(UTC)
    if task.resource_id:
        resource = db.get(Resource, task.resource_id)
        if resource:
            resource.status = ResourceStatus.reviewing
            touch_resource(db, resource, "note", 2)
    db.commit()
    return ok({"id": str(task.id)}, "任务完成，已进入复习沉淀")


@router.post("/notes")
def create_note(payload: NoteCreate, db: Session = Depends(get_db)):
    user = local_user(db)
    note = Note(user_id=user.id, **payload.model_dump())
    db.add(note)
    db.commit()
    return ok({"id": str(note.id)}, "笔记已保存")


@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    user = local_user(db)
    projects = db.scalars(select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())).all()
    return ok([{"id": str(item.id), "name": item.name, "description": item.description, "status": item.status} for item in projects])


@router.post("/projects")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    user = local_user(db)
    project = Project(user_id=user.id, name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    return ok({"id": str(project.id)}, "项目已创建")


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
    return ok(search_all(db, user.id, q))


@router.post("/export/anki")
def export_anki(db: Session = Depends(get_db)):
    user = local_user(db)
    csv = export_anki_csv(db, user.id)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=anki.csv"})


@router.post("/uploads/file")
async def upload_file(file: UploadFile, db: Session = Depends(get_db)):
    user = local_user(db)
    resource = Resource(user_id=user.id, title=file.filename or "未命名文件", type="pdf" if file.filename and file.filename.endswith(".pdf") else "mixed", summary="文件已登记，MVP 版本先记录元数据，后续接入 MinIO 保存原文件。")
    db.add(resource)
    db.commit()
    return ok(serialize_resource(resource), "文件资源已登记")
