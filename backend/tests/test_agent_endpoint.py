import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_agent_endpoint_streams_events():
    async def fake_stream(*args, **kwargs):
        yield {"type": "text", "content": "Hello"}
        yield {"type": "done", "content": "Done"}

    with patch("app.api.v1.agent.stream_agent", side_effect=fake_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/v1/agent",
                json={"query": "test query"},
                headers={"X-API-Key": "test-secret"},
            ) as response:
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/event-stream")
                body = await response.aread()
                text = body.decode()
                assert "text" in text
                assert "Hello" in text


@pytest.mark.asyncio
async def test_agent_endpoint_requires_api_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/agent", json={"query": "test"})
    assert response.status_code == 401
