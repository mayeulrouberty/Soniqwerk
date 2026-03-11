from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from workers.celery_app import celery_app


@celery_app.task(bind=True, name="workers.tasks.ingest_document")
def ingest_document(self, document_id: str, file_path: str, category: str) -> dict:
    """
    Sync Celery task: PDF → chunk → embed (sync OpenAI) → ChromaDB → PostgreSQL.
    Fully synchronous — no asyncio.run(), no async session.
    """
    try:
        self.update_state(state="STARTED", meta={"step": "loading"})

        # 1. Load and chunk PDF
        from app.ingestion.pdf_loader import load_pdf
        chunks = load_pdf(file_path, category)
        if not chunks:
            raise ValueError(f"No text extracted from {file_path}")

        self.update_state(state="PROGRESS", meta={"step": "embedding", "chunks": len(chunks)})

        # 2. Embed with sync OpenAI client (Celery runs in its own process)
        from openai import OpenAI
        from app.config import settings
        sync_client = OpenAI(api_key=settings.openai_api_key)
        texts = [c["text"] for c in chunks]
        response = sync_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]

        # 3. Upsert into ChromaDB
        from app.rag.collections import get_collection
        collection = get_collection(category)
        ids = [f"{document_id}_{i}" for i in range(len(chunks))]
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=[c["metadata"] for c in chunks],
        )

        # 4. Update document status in PostgreSQL (sync session)
        from app.db.session import SessionLocal
        from app.db.models import Document
        with SessionLocal() as session:
            doc = session.query(Document).filter(
                Document.id == uuid.UUID(document_id)
            ).one_or_none()
            if doc:
                doc.status = "ready"
                doc.chunks_count = len(chunks)
                doc.ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)
                session.commit()

        # 5. Clean up temp file
        try:
            os.unlink(file_path)
        except OSError:
            pass

        return {"document_id": document_id, "chunks_count": len(chunks), "status": "ready"}

    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise
