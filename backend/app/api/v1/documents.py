from __future__ import annotations
import hashlib
import os
import tempfile
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from app.api.deps import verify_api_key
from app.db.session import AsyncSessionLocal
from app.db.models import Document, IngestionJob
from workers.tasks import ingest_document

router = APIRouter()

VALID_CATEGORIES = {"manuals", "plugins", "books", "articles"}
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/documents/ingest", status_code=202)
async def ingest(
    file: UploadFile = File(...),
    category: str = Form(...),
    _: str = Depends(verify_api_key),
):
    if category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category. Valid: {sorted(VALID_CATEGORIES)}")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted (.pdf)")

    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "File exceeds 50 MB limit")

    file_hash = hashlib.sha256(content).hexdigest()
    doc_id = str(uuid.uuid4())

    # Persist to temp file for Celery worker (runs in separate process)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(content)
    tmp.flush()
    tmp_path = tmp.name
    tmp.close()

    async with AsyncSessionLocal() as session:
        # Duplicate detection
        existing = await session.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        if existing.scalar_one_or_none():
            os.unlink(tmp_path)
            raise HTTPException(409, "Document already ingested (duplicate file hash)")

        doc = Document(
            id=uuid.UUID(doc_id),
            filename=file.filename,
            category=category,
            status="queued",
            file_hash=file_hash,
        )
        session.add(doc)
        await session.flush()

        task = ingest_document.delay(doc_id, tmp_path, category)

        job = IngestionJob(
            document_id=uuid.UUID(doc_id),
            celery_task_id=task.id,
            status="queued",
        )
        session.add(job)
        await session.commit()

    return {"task_id": task.id, "document_id": doc_id, "status": "queued"}


@router.get("/documents/ingest/{task_id}/status")
async def ingest_status(
    task_id: str,
    _: str = Depends(verify_api_key),
):
    from celery.result import AsyncResult
    from workers.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)
    state_map = {
        "PENDING": "queued",
        "STARTED": "processing",
        "PROGRESS": "processing",
        "SUCCESS": "ready",
        "FAILURE": "error",
    }
    return {
        "status": state_map.get(result.state, "processing"),
        "chunks_count": result.result.get("chunks_count") if result.successful() else None,
        "error": str(result.result) if result.failed() else None,
    }
