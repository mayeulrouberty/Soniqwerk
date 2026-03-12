"""Unit tests for ws_bridge.bridge — uses httpx + websockets test client."""
from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport

from ws_bridge.bridge import app, send_command, is_connected, _pending
import ws_bridge.bridge as bridge_module


# ── Health endpoint ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_no_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["client_connected"] is False


# ── send_command without client ────────────────────────────────────

@pytest.mark.asyncio
async def test_send_command_no_client_raises():
    # Ensure no client
    bridge_module._client_ws = None
    with pytest.raises(RuntimeError, match="No Max for Live client connected"):
        await send_command("get_tracks")


# ── send_command with mock WebSocket ───────────────────────────────

@pytest.mark.asyncio
async def test_send_command_success():
    """Simulate a successful round-trip: send_command → mock WS → resolve."""
    mock_ws = AsyncMock()
    sent_messages = []

    async def capture_send(text):
        sent_messages.append(json.loads(text))

    mock_ws.send_text = capture_send
    bridge_module._client_ws = mock_ws

    try:
        # Start send_command in background
        task = asyncio.create_task(send_command("get_tracks", {}))

        # Give event loop a tick so the future is created and message sent
        await asyncio.sleep(0.05)

        assert len(sent_messages) == 1
        msg_id = sent_messages[0]["id"]
        assert sent_messages[0]["action"] == "get_tracks"

        # Simulate response from Max for Live
        from ws_bridge.protocol import BridgeResponse
        resp = BridgeResponse(id=msg_id, result={"tracks": [{"name": "Bass", "index": 0}]})
        _pending.resolve(msg_id, resp)

        result = await task
        assert result == {"tracks": [{"name": "Bass", "index": 0}]}
    finally:
        bridge_module._client_ws = None
        _pending.cancel_all()


@pytest.mark.asyncio
async def test_send_command_timeout():
    """send_command should raise TimeoutError after timeout."""
    mock_ws = AsyncMock()
    mock_ws.send_text = AsyncMock()
    bridge_module._client_ws = mock_ws

    # Temporarily shorten timeout
    original_timeout = bridge_module._TIMEOUT_SECONDS
    bridge_module._TIMEOUT_SECONDS = 0.1

    try:
        with pytest.raises(asyncio.TimeoutError):
            await send_command("get_tracks", {})
    finally:
        bridge_module._client_ws = None
        bridge_module._TIMEOUT_SECONDS = original_timeout
        _pending.cancel_all()
