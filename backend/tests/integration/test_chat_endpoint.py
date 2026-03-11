import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock


async def _mock_stream(*args, **kwargs):
    for chunk in ["Bonjour", ", voici", " ma réponse."]:
        yield chunk


@pytest.fixture
def app_chat():
    with patch("app.api.v1.chat.stream_response", side_effect=_mock_stream):
        with patch("app.api.v1.chat.retrieve", new_callable=AsyncMock, return_value=[]):
            from app.main import app
            yield app


@pytest.mark.asyncio
async def test_chat_returns_200_with_sse_content_type(app_chat):
    async with AsyncClient(transport=ASGITransport(app=app_chat), base_url="http://test") as c:
        async with c.stream(
            "POST", "/v1/chat",
            json={"message": "test"},
            headers={"X-API-Key": "test-secret"},
        ) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            body = await r.aread()

    assert b"event: chunk" in body
    assert b"Bonjour" in body
    assert b"event: done" in body


@pytest.mark.asyncio
async def test_chat_requires_api_key(app_chat):
    async with AsyncClient(transport=ASGITransport(app=app_chat), base_url="http://test") as c:
        r = await c.post("/v1/chat", json={"message": "test"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_chat_emits_sources_event_when_chunks_present(app_chat):
    chunks = [{"text": "Serum...", "metadata": {"title": "Serum Manual", "source": "serum.pdf"}, "score": 0.9}]
    with patch("app.api.v1.chat.retrieve", new_callable=AsyncMock, return_value=chunks):
        async with AsyncClient(transport=ASGITransport(app=app_chat), base_url="http://test") as c:
            async with c.stream(
                "POST", "/v1/chat",
                json={"message": "serum oscillators"},
                headers={"X-API-Key": "test-secret"},
            ) as r:
                body = await r.aread()

    assert b"event: sources" in body
    assert b"Serum Manual" in body
