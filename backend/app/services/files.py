import hashlib
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models import Resource, ResourceChunk, StoredFile
from app.services.resources import infer_resource_type, storage_root


TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


def safe_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-（）()[] " else "_" for ch in name).strip()
    return cleaned or "uploaded-file"


def save_upload_file(db: Session, user_id: UUID, file: UploadFile) -> Resource:
    filename = safe_filename(file.filename or "uploaded-file")
    resource_type = infer_resource_type(filename, file.content_type)
    resource = Resource(
        user_id=user_id,
        title=filename,
        type=resource_type,
        source_platform="本地文件",
        summary="请补充：为什么保存这个文件？后续要如何处理？",
    )
    db.add(resource)
    db.flush()

    original_dir = storage_root() / str(resource.id) / "original"
    original_dir.mkdir(parents=True, exist_ok=True)
    target_path = original_dir / filename

    hasher = hashlib.sha256()
    with target_path.open("wb") as target:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
            target.write(chunk)

    stored = StoredFile(
        user_id=user_id,
        resource_id=resource.id,
        file_name=filename,
        file_type=file.content_type or resource_type,
        file_size=target_path.stat().st_size,
        storage_path=str(target_path),
        checksum=hasher.hexdigest(),
    )
    resource.file_url = f"/api/files/{stored.id}/download"
    db.add(stored)
    db.flush()
    extract_chunks(db, resource, target_path, resource_type)
    db.commit()
    db.refresh(resource)
    return resource


def extract_chunks(db: Session, resource: Resource, path: Path, resource_type: str) -> None:
    if resource_type == "pdf":
        extract_pdf_chunks(db, resource, path)
    elif resource_type == "word":
        extract_word_chunks(db, resource, path)
    elif path.suffix.lower() in TEXT_EXTENSIONS:
        extract_text_chunks(db, resource, path)
    elif path.suffix.lower() in VIDEO_EXTENSIONS:
        db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="video", content="视频已保存，可在详情页播放并添加时间点批注。", heading="视频文件"))
    else:
        db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="file", content="文件已保存，暂不支持预览解析。", heading="文件"))


def extract_pdf_chunks(db: Session, resource: Resource, path: Path) -> None:
    try:
        reader = PdfReader(str(path))
        for index, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            if text:
                db.add(ResourceChunk(resource_id=resource.id, chunk_index=index, chunk_type="pdf_text", content=text[:8000], page_number=index + 1, heading=f"第 {index + 1} 页"))
        if not reader.pages:
            db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="pdf_text", content="PDF 已保存，但没有提取到文本。", heading="PDF"))
    except Exception as exc:
        db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="pdf_text", content=f"PDF 已保存，但文本提取失败：{exc}", heading="PDF 解析"))


def extract_word_chunks(db: Session, resource: Resource, path: Path) -> None:
    try:
        from docx import Document

        doc = Document(str(path))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs)
        if text:
            for index, start in enumerate(range(0, len(text), 4000)):
                db.add(ResourceChunk(resource_id=resource.id, chunk_index=index, chunk_type="doc_text", content=text[start:start + 4000], heading=f"Word 片段 {index + 1}"))
        else:
            db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="doc_text", content="Word 已保存，但没有提取到文本。", heading="Word"))
    except Exception as exc:
        db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="doc_text", content=f"Word 已保存，但文本提取失败：{exc}", heading="Word 解析"))


def extract_text_chunks(db: Session, resource: Resource, path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.strip():
        db.add(ResourceChunk(resource_id=resource.id, chunk_index=0, chunk_type="text", content="文本文件为空或无法读取。", heading="文本"))
        return
    for index, start in enumerate(range(0, len(text), 4000)):
        db.add(ResourceChunk(resource_id=resource.id, chunk_index=index, chunk_type="text", content=text[start:start + 4000], heading=f"文本片段 {index + 1}"))


def copy_demo_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
