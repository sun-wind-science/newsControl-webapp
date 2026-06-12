from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ResourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    type: str = "link"
    project_id: UUID | None = None
    original_url: str | None = None
    source_platform: str | None = None
    summary: str | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请输入内容")
        return value.strip()


class CaptureCreate(BaseModel):
    content: str = Field(min_length=1)
    capture_type: str = "link"
    title: str | None = None
    summary: str | None = None
    source_platform: str | None = None
    project_id: UUID | None = None
    process_goal: str = "学习"
    estimated_minutes: int = 20
    priority: int = 3
    tags: str | None = None
    next_action: str = "triage"

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请输入内容")
        return value.strip()


class ResourceUpdate(BaseModel):
    title: str | None = None
    project_id: UUID | None = None
    status: str | None = None
    decay_status: str | None = None
    summary: str | None = None
    type: str | None = None
    source_platform: str | None = None
    original_url: str | None = None
    tags: str | None = None
    estimated_minutes: int | None = None
    priority: int | None = None


class ResourceOut(BaseModel):
    id: UUID
    title: str
    type: str
    status: str
    decay_status: str
    source_platform: str | None
    original_url: str | None
    summary: str | None
    heat_score: float
    estimated_minutes: int = 20
    created_at: datetime
    last_touched_at: datetime

    model_config = {"from_attributes": True}


class InboxDecision(BaseModel):
    keep: bool
    purpose: str = "active_learning"
    estimated_minutes: int = 20


class EnergyModeIn(BaseModel):
    mode: str


class TaskOut(BaseModel):
    id: UUID
    title: str
    task_type: str
    priority: int
    status: str
    estimated_minutes: int
    resource_id: UUID | None

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class NoteCreate(BaseModel):
    title: str
    content: str = ""
    resource_id: UUID | None = None
    project_id: UUID | None = None
    note_type: str = "annotation"
    source_range: str | None = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请输入批注内容")
        return value.strip()


class AnnotationCreate(BaseModel):
    note_type: str = "annotation"
    content: str = Field(min_length=1)
    source_range: str | None = None
    title: str | None = None

    @field_validator("content")
    @classmethod
    def annotation_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请输入批注内容")
        return value.strip()


class SearchResult(BaseModel):
    kind: str
    id: UUID
    title: str
    snippet: str
    location: str | None = None
