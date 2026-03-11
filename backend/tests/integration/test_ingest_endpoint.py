import pytest
import io
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def app_docs():
    mock_task = MagicMock()
    mock_task.id = "celery-test-123"
    with patch("app.api.v1.documents.ingest_document") as mock_ingest:
        mock_ingest.delay.return_value = mock_task
        with patch("app.api.v1.documents.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
            )
            mock_session.flush = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.add = MagicMock()
            mock_session_cls.return_value = mock_session
            from app.main import app
            yield app


@pytest.mark.asyncio
async def test_ingest_returns_202_with_task_id(app_docs):
    async with AsyncClient(transport=ASGITransport(app=app_docs), base_url="http://test") as c:
        r = await c.post(
            "/v1/documents/ingest",
            files={"file": ("manual.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
            data={"category": "manuals"},
            headers={"X-API-Key": "test-secret"},
        )
    assert r.status_code == 202
    body = r.json()
    assert "task_id" in body
    assert "document_id" in body
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_ingest_rejects_non_pdf(app_docs):
    async with AsyncClient(transport=ASGITransport(app=app_docs), base_url="http://test") as c:
        r = await c.post(
            "/v1/documents/ingest",
            files={"file": ("doc.txt", io.BytesIO(b"text"), "text/plain")},
            data={"category": "manuals"},
            headers={"X-API-Key": "test-secret"},
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_ingest_rejects_invalid_category(app_docs):
    async with AsyncClient(transport=ASGITransport(app=app_docs), base_url="http://test") as c:
        r = await c.post(
            "/v1/documents/ingest",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
            data={"category": "invalid_cat"},
            headers={"X-API-Key": "test-secret"},
        )
    assert r.status_code == 400
