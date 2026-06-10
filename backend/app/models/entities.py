import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def new_id() -> uuid.UUID:
    return uuid.uuid4()


class ResourceStatus(str, enum.Enum):
    inbox = "inbox"
    triaged = "triaged"
    to_preview = "to_preview"
    to_process = "to_process"
    processing = "processing"
    to_convert = "to_convert"
    reviewing = "reviewing"
    archived = "archived"
    discarded = "discarded"
    cold_stored = "cold_stored"


class DecayStatus(str, enum.Enum):
    active = "active"
    cold = "cold"
    decaying = "decaying"
    discarded = "discarded"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"
    skipped = "skipped"


class VerificationStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    rejected = "rejected"
    modified = "modified"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str] = mapped_column(String(80), default="本地用户")
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False)


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    default_language: Mapped[str] = mapped_column(String(20), default="zh-CN")
    default_ai_model: Mapped[str] = mapped_column(String(80), default="gpt-4o-mini")
    daily_process_limit: Mapped[int] = mapped_column(Integer, default=3)
    review_reminder_preference: Mapped[str] = mapped_column(String(80), default="daily")
    auto_generate_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_generate_tags: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_generate_anki: Mapped[bool] = mapped_column(Boolean, default=False)
    resource_decay_threshold_days: Mapped[int] = mapped_column(Integer, default=30)
    energy_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="settings")


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    type: Mapped[str] = mapped_column(String(50), default="link", index=True)
    source_platform: Mapped[str | None] = mapped_column(String(120))
    original_url: Mapped[str | None] = mapped_column(String(1000))
    file_url: Mapped[str | None] = mapped_column(String(1000))
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[ResourceStatus] = mapped_column(Enum(ResourceStatus), default=ResourceStatus.inbox, index=True)
    decay_status: Mapped[DecayStatus] = mapped_column(Enum(DecayStatus), default=DecayStatus.active, index=True)
    language: Mapped[str] = mapped_column(String(20), default="zh-CN")
    duration: Mapped[int | None] = mapped_column(Integer)
    word_count: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    heat_score: Mapped[float] = mapped_column(Float, default=0)
    last_touched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    cold_stored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    chunks: Mapped[list["ResourceChunk"]] = relationship(back_populates="resource", cascade="all, delete-orphan")


class ResourceMetadata(Base):
    __tablename__ = "resource_metadata"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"), index=True)
    author: Mapped[str | None] = mapped_column(String(255))
    publish_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    platform: Mapped[str | None] = mapped_column(String(120))
    channel: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    raw_metadata_json: Mapped[dict | None] = mapped_column(JSON)


class ResourceChunk(Base):
    __tablename__ = "resource_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    chunk_type: Mapped[str] = mapped_column(String(40), default="paragraph")
    content: Mapped[str] = mapped_column(Text)
    start_time: Mapped[int | None] = mapped_column(Integer)
    end_time: Mapped[int | None] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(255))
    embedding: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resource: Mapped[Resource] = relationship(back_populates="chunks")


class ResourceHeatSignal(Base):
    __tablename__ = "resource_heat_signals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    signal_type: Mapped[str] = mapped_column(String(40))
    signal_value: Mapped[float] = mapped_column(Float, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, default="")
    note_type: Mapped[str] = mapped_column(String(50), default="general")
    source_range: Mapped[str | None] = mapped_column(String(255))
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    user_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(60), default="preview")
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.pending, index=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=20)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    output_result_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    category: Mapped[str | None] = mapped_column(String(80))


class ResourceTag(Base):
    __tablename__ = "resource_tags"

    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id"), primary_key=True)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id"), primary_key=True)


class AIOutput(Base):
    __tablename__ = "ai_outputs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"), index=True)
    output_type: Mapped[str] = mapped_column(String(80), index=True)
    model_name: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.6)
    user_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus), default=VerificationStatus.draft)
    source_range: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"), index=True)
    note_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("notes.id"), index=True)
    card_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("anki_cards.id"), index=True)
    review_type: Mapped[str] = mapped_column(String(60), default="active_recall")
    prompt: Mapped[str] = mapped_column(Text)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnkiCard(Base):
    __tablename__ = "anki_cards"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(String(500))
    difficulty: Mapped[str] = mapped_column(String(40), default="normal")
    source_reference: Mapped[str | None] = mapped_column(String(500))
    source_timestamp: Mapped[int | None] = mapped_column(Integer)
    exported: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StoredFile(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(120))
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String(1000))
    checksum: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=new_id)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"), index=True)
    job_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
