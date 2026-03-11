import uuid
from app.db.models import Conversation, Message, Document, IngestionJob

def test_conversation_model_has_required_columns():
    c = Conversation()
    assert hasattr(c, "id")
    assert hasattr(c, "created_at")
    assert hasattr(c, "model")

def test_message_model_has_required_columns():
    m = Message(role="user", content="test")
    assert m.role == "user"
    assert m.content == "test"
    assert hasattr(m, "conversation_id")
    assert hasattr(m, "sources")
    assert hasattr(m, "model_used")
    assert hasattr(m, "tokens_used")

def test_document_model_has_required_columns():
    doc = Document(id=uuid.uuid4(), filename="manual.pdf", category="manuals", status="queued", file_hash="abc123")
    assert doc.filename == "manual.pdf"
    assert doc.status == "queued"

def test_ingestion_job_model_has_required_columns():
    job = IngestionJob(document_id=uuid.uuid4(), celery_task_id="celery-uuid-123", status="queued")
    assert job.celery_task_id == "celery-uuid-123"
    assert hasattr(job, "error")
    assert hasattr(job, "updated_at")
