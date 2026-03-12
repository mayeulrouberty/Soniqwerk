# SONIQWERK Phase 3 — Ableton Live Integration Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect SONIQWERK's AI agent to Ableton Live 11/12 via a Max for Live device, allowing natural-language control of the DAW (read session state, set parameters, fire clips). A LangChain ReAct agent orchestrates 6 tools that communicate through a WebSocket bridge.

**Architecture:**
```
Ableton Live (Live 11 / Live 12)
  └── Max for Live device (SONIQWERK.amxd)
       └── node.script SONIQWERK_bridge.js  ← WebSocket client (ws library)
            ↕ WebSocket ws://localhost:8001/ws
Python WebSocket Bridge (ws_bridge/bridge.py, port 8001, standalone)
  └── Receives tool commands, routes to Max for Live
  └── Returns LOM results back to tools
  └── asyncio.Future dict for request/response pairing

FastAPI (port 8000)
  └── POST /v1/agent (SSE streaming)
       └── LangChain ReAct agent
            └── 6 tools → bridge.send_command() → Max for Live → LOM
```

**Tech Stack:** Python 3.9, FastAPI 0.111, LangChain 0.2 (`langchain`, `langchain-openai`), websockets 12, Node.js `ws` ^8.0.0 (Max for Live node.script), pytest + pytest-asyncio.

**Compatibility:** All LOM paths used are core paths present in both Live 11 and Live 12. No Live 12-only APIs are used.

---

## Chunk 1: WebSocket Bridge

### Task 1: Protocol + message types (`ws_bridge/protocol.py`)

**Files:**
- Create: `backend/ws_bridge/__init__.py`
- Create: `backend/ws_bridge/protocol.py`

- [ ] **Step 1.1: Create `backend/ws_bridge/__init__.py`**

```python
```

Empty init file.

- [ ] **Step 1.2: Create `backend/ws_bridge/protocol.py`**

```python
"""WebSocket message protocol for Ableton Live bridge.

Defines typed message classes and a pending-request registry for
matching async responses to their originating tool calls.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


@dataclass
class BridgeRequest:
    """Message sent from Python tools to Max for Live."""
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BridgeResponse:
    """Message received from Max for Live."""
    id: str
    result: Optional[Any] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BridgeResponse":
        return cls(
            id=data["id"],
            result=data.get("result"),
            error=data.get("error"),
        )


class PendingRequests:
    """Thread-safe registry of in-flight requests awaiting responses.

    Each send_command() creates a Future, stores it by message ID,
    and awaits it.  When the Max for Live response arrives, resolve()
    completes the matching Future.
    """

    def __init__(self) -> None:
        self._futures: Dict[str, asyncio.Future] = {}

    def create(self, message_id: str) -> asyncio.Future:
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self._futures[message_id] = fut
        return fut

    def resolve(self, message_id: str, response: BridgeResponse) -> bool:
        """Resolve a pending future.  Returns True if found."""
        fut = self._futures.pop(message_id, None)
        if fut is None or fut.done():
            return False
        if response.error:
            fut.set_exception(RuntimeError(response.error))
        else:
            fut.set_result(response.result)
        return True

    def cancel_all(self) -> None:
        for fut in self._futures.values():
            if not fut.done():
                fut.cancel()
        self._futures.clear()

    @property
    def count(self) -> int:
        return len(self._futures)
```

- [ ] **Step 1.3: Create tests `backend/tests/unit/test_ws_protocol.py`**

```python
"""Unit tests for ws_bridge.protocol — no real WebSocket needed."""
from __future__ import annotations

import asyncio
import json
import pytest

from ws_bridge.protocol import BridgeRequest, BridgeResponse, PendingRequests


# ── BridgeRequest ──────────────────────────────────────────────────

class TestBridgeRequest:
    def test_to_dict_includes_all_fields(self):
        req = BridgeRequest(action="get_tracks", params={"foo": 1}, id="abc-123")
        d = req.to_dict()
        assert d == {"action": "get_tracks", "params": {"foo": 1}, "id": "abc-123"}

    def test_auto_generates_uuid_id(self):
        req = BridgeRequest(action="set_tempo", params={"bpm": 120})
        assert len(req.id) == 36  # UUID4 string length

    def test_serializes_to_json(self):
        req = BridgeRequest(action="fire_clip", params={"track_index": 0, "slot_index": 2})
        raw = json.dumps(req.to_dict())
        parsed = json.loads(raw)
        assert parsed["action"] == "fire_clip"
        assert parsed["params"]["slot_index"] == 2


# ── BridgeResponse ─────────────────────────────────────────────────

class TestBridgeResponse:
    def test_from_dict_success(self):
        data = {"id": "abc", "result": {"tempo": 128.0}, "error": None}
        resp = BridgeResponse.from_dict(data)
        assert resp.id == "abc"
        assert resp.result == {"tempo": 128.0}
        assert resp.error is None

    def test_from_dict_error(self):
        data = {"id": "xyz", "error": "Track not found"}
        resp = BridgeResponse.from_dict(data)
        assert resp.error == "Track not found"
        assert resp.result is None

    def test_from_dict_missing_optional_fields(self):
        data = {"id": "min"}
        resp = BridgeResponse.from_dict(data)
        assert resp.result is None
        assert resp.error is None


# ── PendingRequests ────────────────────────────────────────────────

class TestPendingRequests:
    @pytest.mark.asyncio
    async def test_create_and_resolve(self):
        pending = PendingRequests()
        fut = pending.create("id-1")
        assert pending.count == 1

        resp = BridgeResponse(id="id-1", result={"tempo": 140.0})
        assert pending.resolve("id-1", resp) is True
        assert await fut == {"tempo": 140.0}
        assert pending.count == 0

    @pytest.mark.asyncio
    async def test_resolve_with_error_raises(self):
        pending = PendingRequests()
        fut = pending.create("id-2")

        resp = BridgeResponse(id="id-2", error="Device offline")
        pending.resolve("id-2", resp)

        with pytest.raises(RuntimeError, match="Device offline"):
            await fut

    def test_resolve_unknown_id_returns_false(self):
        pending = PendingRequests()
        resp = BridgeResponse(id="no-such-id", result={})
        assert pending.resolve("no-such-id", resp) is False

    @pytest.mark.asyncio
    async def test_cancel_all(self):
        pending = PendingRequests()
        fut1 = pending.create("a")
        fut2 = pending.create("b")
        pending.cancel_all()
        assert pending.count == 0
        assert fut1.cancelled()
        assert fut2.cancelled()
```

- [ ] **Step 1.4: Run tests**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python -m pytest tests/unit/test_ws_protocol.py -v
```

Expected: 9 tests pass.

- [ ] **Step 1.5: Git commit**

```
feat(ws-bridge): add WebSocket protocol + pending-request registry
```

---

### Task 2: WebSocket bridge server (`ws_bridge/bridge.py`)

**Files:**
- Create: `backend/ws_bridge/bridge.py`

- [ ] **Step 2.1: Create `backend/ws_bridge/bridge.py`**

```python
"""WebSocket bridge between LangChain tools and Max for Live.

Runs as a standalone FastAPI/uvicorn process on port 8001.
A single Max for Live client connects at ws://localhost:8001/ws.
Tools call send_command() which creates a pending Future, sends the
request JSON, and awaits the response with a 10 s timeout.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ws_bridge.protocol import BridgeRequest, BridgeResponse, PendingRequests

logger = logging.getLogger("ws_bridge")

app = FastAPI(title="SONIQWERK WS Bridge", version="1.0.0")

# ── Singleton state ────────────────────────────────────────────────

_client_ws: Optional[WebSocket] = None
_pending = PendingRequests()
_TIMEOUT_SECONDS = 10.0


def is_connected() -> bool:
    return _client_ws is not None


async def send_command(action: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Send a command to Max for Live and await the response.

    Returns the result dict on success.
    Raises RuntimeError on error or if no client is connected.
    Raises asyncio.TimeoutError after 10 s.
    """
    global _client_ws
    if _client_ws is None:
        raise RuntimeError(
            "No Max for Live client connected. "
            "Open the SONIQWERK device in Ableton Live."
        )

    request = BridgeRequest(action=action, params=params or {})
    fut = _pending.create(request.id)

    try:
        await _client_ws.send_text(json.dumps(request.to_dict()))
    except Exception as exc:
        _pending.resolve(request.id, BridgeResponse(id=request.id, error=str(exc)))
        raise RuntimeError(f"Failed to send to Max for Live: {exc}") from exc

    return await asyncio.wait_for(fut, timeout=_TIMEOUT_SECONDS)


# ── WebSocket endpoint ────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global _client_ws
    await ws.accept()
    logger.info("Max for Live client connected")
    _client_ws = ws

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                response = BridgeResponse.from_dict(data)
                resolved = _pending.resolve(response.id, response)
                if not resolved:
                    logger.warning("Received response for unknown id: %s", response.id)
            except (json.JSONDecodeError, KeyError) as exc:
                logger.error("Invalid message from Max for Live: %s — %s", raw[:200], exc)
    except WebSocketDisconnect:
        logger.info("Max for Live client disconnected")
    finally:
        _client_ws = None
        _pending.cancel_all()


# ── Health check ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "client_connected": is_connected()}


# ── Entrypoint ─────────────────────────────────────────────────────

def main():
    """Run with: python -m ws_bridge.bridge"""
    import uvicorn

    uvicorn.run(
        "ws_bridge.bridge:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2.2: Add `backend/ws_bridge/__main__.py`** (allows `python -m ws_bridge`)

```python
from ws_bridge.bridge import main

main()
```

- [ ] **Step 2.3: Create tests `backend/tests/unit/test_ws_bridge.py`**

```python
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
```

- [ ] **Step 2.4: Run tests**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python -m pytest tests/unit/test_ws_bridge.py tests/unit/test_ws_protocol.py -v
```

Expected: 13 tests pass.

- [ ] **Step 2.5: Git commit**

```
feat(ws-bridge): add WebSocket bridge server on port 8001
```

---

## Chunk 2: ReAct Agent + Tools

### Task 3: LangChain tools — Live 11/12 LOM calls (`app/agent/tools.py`)

**Files:**
- Create: `backend/app/agent/__init__.py`
- Create: `backend/app/agent/tools.py`

- [ ] **Step 3.1: Create `backend/app/agent/__init__.py`**

```python
```

- [ ] **Step 3.2: Create `backend/app/agent/tools.py`**

```python
"""LangChain tools for Ableton Live control via the WebSocket bridge.

All 6 tools use send_command() from ws_bridge.bridge, which sends a
JSON message to the Max for Live node.script and awaits a response.

Every LOM path used here is compatible with both Live 11 and Live 12.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from langchain_core.tools import tool

from ws_bridge.bridge import send_command


def _sync_send(action: str, params: Optional[dict] = None) -> dict:
    """Run send_command in the current event loop.

    LangChain tools may be called synchronously by the agent executor.
    This wrapper handles both sync and async contexts.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — run directly
        return asyncio.run(send_command(action, params or {}))

    # Already in an async context — create a task
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return loop.run_in_executor(pool, asyncio.run, send_command(action, params or {}))


async def _safe_send(action: str, params: Optional[dict] = None) -> dict:
    """Send a command, returning an error dict instead of raising."""
    try:
        result = await send_command(action, params or {})
        return result
    except RuntimeError as exc:
        return {"error": str(exc)}
    except asyncio.TimeoutError:
        return {"error": "Timeout: Ableton Live did not respond within 10 seconds."}


@tool
async def get_session_info() -> dict:
    """Get current Ableton Live session info: tempo, time signature, track count, is_playing.

    Works with both Ableton Live 11 and Live 12.
    Returns a dict with keys: tempo, time_signature, track_count, is_playing.
    """
    return await _safe_send("get_session_info")


@tool
async def get_tracks() -> dict:
    """List all tracks in the current Ableton Live session.

    Works with both Ableton Live 11 and Live 12.
    Returns a list of dicts with keys: name, index, type, is_armed, volume.
    """
    return await _safe_send("get_tracks")


@tool
async def get_track_devices(track_index: int) -> dict:
    """List all devices (instruments, effects) on a specific track.

    Works with both Ableton Live 11 and Live 12.
    Args:
        track_index: 0-based index of the track.
    Returns a list of dicts with keys: name, index, type.
    """
    return await _safe_send("get_track_devices", {"track_index": track_index})


@tool
async def set_parameter(
    track_index: int,
    device_index: int,
    param_index: int,
    value: float,
) -> dict:
    """Set a device parameter value on a track.

    Works with both Ableton Live 11 and Live 12.
    Uses LOM path: live_set tracks N devices M parameters P value.

    Args:
        track_index: 0-based track index.
        device_index: 0-based device index on that track.
        param_index: 0-based parameter index on that device.
        value: New parameter value (float, typically 0.0–1.0).
    Returns confirmation dict or error.
    """
    return await _safe_send("set_parameter", {
        "track_index": track_index,
        "device_index": device_index,
        "param_index": param_index,
        "value": value,
    })


@tool
async def get_clips(track_index: int) -> dict:
    """List all clips on a specific track.

    Works with both Ableton Live 11 and Live 12.
    Args:
        track_index: 0-based index of the track.
    Returns a list of dicts with keys: name, slot_index, length, is_playing.
    """
    return await _safe_send("get_clips", {"track_index": track_index})


@tool
async def fire_clip(track_index: int, slot_index: int) -> dict:
    """Trigger (fire) a clip in a specific slot on a track.

    Works with both Ableton Live 11 and Live 12.
    Uses LOM path: live_set tracks N clip_slots M clip fire.

    Args:
        track_index: 0-based track index.
        slot_index: 0-based clip slot index.
    Returns confirmation dict or error.
    """
    return await _safe_send("fire_clip", {
        "track_index": track_index,
        "slot_index": slot_index,
    })


# Export all tools as a list for the agent
ALL_TOOLS = [
    get_session_info,
    get_tracks,
    get_track_devices,
    set_parameter,
    get_clips,
    fire_clip,
]
```

- [ ] **Step 3.3: Create tests `backend/tests/unit/test_agent_tools.py`**

```python
"""Unit tests for app.agent.tools — mocks send_command entirely."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.agent.tools import (
    get_session_info,
    get_tracks,
    get_track_devices,
    set_parameter,
    get_clips,
    fire_clip,
    ALL_TOOLS,
)


MODULE = "app.agent.tools"


@pytest.fixture
def mock_send():
    """Patch send_command and return the mock."""
    with patch(f"{MODULE}.send_command", new_callable=AsyncMock) as m:
        yield m


# ── Tool list ──────────────────────────────────────────────────────

def test_all_tools_has_six_entries():
    assert len(ALL_TOOLS) == 6


def test_all_tools_have_names():
    names = {t.name for t in ALL_TOOLS}
    assert names == {
        "get_session_info",
        "get_tracks",
        "get_track_devices",
        "set_parameter",
        "get_clips",
        "fire_clip",
    }


# ── get_session_info ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_session_info(mock_send):
    mock_send.return_value = {"tempo": 128.0, "is_playing": True, "track_count": 8}
    result = await get_session_info.ainvoke({})
    mock_send.assert_awaited_once_with("get_session_info", {})
    assert result["tempo"] == 128.0


# ── get_tracks ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_tracks(mock_send):
    mock_send.return_value = [
        {"name": "Bass", "index": 0, "type": "midi", "is_armed": False, "volume": 0.8},
    ]
    result = await get_tracks.ainvoke({})
    mock_send.assert_awaited_once_with("get_tracks", {})
    assert result[0]["name"] == "Bass"


# ── get_track_devices ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_track_devices(mock_send):
    mock_send.return_value = [{"name": "Wavetable", "index": 0, "type": "instrument"}]
    result = await get_track_devices.ainvoke({"track_index": 0})
    mock_send.assert_awaited_once_with("get_track_devices", {"track_index": 0})
    assert result[0]["name"] == "Wavetable"


# ── set_parameter ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_parameter(mock_send):
    mock_send.return_value = {"ok": True, "value": 0.5}
    result = await set_parameter.ainvoke({
        "track_index": 0,
        "device_index": 0,
        "param_index": 1,
        "value": 0.5,
    })
    mock_send.assert_awaited_once_with("set_parameter", {
        "track_index": 0,
        "device_index": 0,
        "param_index": 1,
        "value": 0.5,
    })
    assert result["ok"] is True


# ── get_clips ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_clips(mock_send):
    mock_send.return_value = [{"name": "Intro", "slot_index": 0, "length": 8.0, "is_playing": False}]
    result = await get_clips.ainvoke({"track_index": 0})
    mock_send.assert_awaited_once_with("get_clips", {"track_index": 0})
    assert result[0]["name"] == "Intro"


# ── fire_clip ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fire_clip(mock_send):
    mock_send.return_value = {"ok": True}
    result = await fire_clip.ainvoke({"track_index": 0, "slot_index": 2})
    mock_send.assert_awaited_once_with("fire_clip", {"track_index": 0, "slot_index": 2})
    assert result["ok"] is True


# ── Error handling ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_returns_error_on_disconnect(mock_send):
    mock_send.side_effect = RuntimeError("No Max for Live client connected")
    result = await get_session_info.ainvoke({})
    assert "error" in result
    assert "No Max for Live" in result["error"]


@pytest.mark.asyncio
async def test_tool_returns_error_on_timeout(mock_send):
    mock_send.side_effect = asyncio.TimeoutError()
    result = await get_tracks.ainvoke({})
    assert "error" in result
    assert "Timeout" in result["error"]
```

- [ ] **Step 3.4: Run tests**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python -m pytest tests/unit/test_agent_tools.py -v
```

Expected: 10 tests pass.

- [ ] **Step 3.5: Git commit**

```
feat(agent): add 6 LangChain tools for Ableton Live LOM control
```

---

### Task 4: ReAct agent (`app/agent/react_agent.py`)

**Files:**
- Create: `backend/app/agent/react_agent.py`

- [ ] **Step 4.1: Create `backend/app/agent/react_agent.py`**

```python
"""LangChain ReAct agent for Ableton Live control.

Uses the 6 tools defined in app.agent.tools to interact with Live 11/12
through the WebSocket bridge.  Streams intermediate steps and final
answer as dicts for the SSE endpoint.
"""
from __future__ import annotations

from typing import AsyncIterator, Dict, Any

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agent.tools import ALL_TOOLS
from app.config import settings

SYSTEM_PROMPT = """\
You are SONIQWERK, an AI assistant for electronic music production inside Ableton Live.
You have tools to read and control the user's Ableton Live session (works with Live 11 and Live 12).

Guidelines:
- Always read the session state first (get_session_info, get_tracks) before making changes.
- Explain what you are doing before and after each action.
- If a tool returns an error, explain the problem clearly.
- Parameter values are typically 0.0 to 1.0 (normalized).
- Be concise. Use music production terminology.
- Respond in the same language as the user (French or English).
"""


def _build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])


def create_agent() -> AgentExecutor:
    """Create a ReAct agent executor with the 6 Ableton tools."""
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        api_key=settings.openai_api_key,
        streaming=True,
    )
    prompt = _build_prompt()
    agent = create_openai_tools_agent(llm, ALL_TOOLS, prompt)
    return AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=False,
        max_iterations=10,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
    )


async def stream_agent(
    query: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """Stream agent execution as a series of typed events.

    Yields dicts like:
      {"type": "thought", "content": "I need to check the tracks..."}
      {"type": "tool_call", "tool": "get_tracks", "input": {}}
      {"type": "tool_result", "tool": "get_tracks", "output": [...]}
      {"type": "answer", "content": "Your session has 8 tracks..."}
    """
    executor = create_agent()

    async for event in executor.astream_events(
        {"input": query, "chat_history": chat_history or []},
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, "content") and chunk.content:
                yield {"type": "token", "content": chunk.content}

        elif kind == "on_tool_start":
            yield {
                "type": "tool_call",
                "tool": event["name"],
                "input": event["data"].get("input", {}),
            }

        elif kind == "on_tool_end":
            yield {
                "type": "tool_result",
                "tool": event["name"],
                "output": event["data"].get("output", ""),
            }
```

- [ ] **Step 4.2: Create tests `backend/tests/unit/test_react_agent.py`**

```python
"""Unit tests for app.agent.react_agent — mocks the LLM."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from app.agent.react_agent import _build_prompt, create_agent, SYSTEM_PROMPT


def test_system_prompt_mentions_live_11_and_12():
    assert "Live 11" in SYSTEM_PROMPT
    assert "Live 12" in SYSTEM_PROMPT


def test_build_prompt_has_required_variables():
    prompt = _build_prompt()
    variables = prompt.input_variables
    assert "input" in variables


@patch("app.agent.react_agent.ChatOpenAI")
def test_create_agent_returns_executor(mock_llm_cls):
    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    mock_llm_cls.return_value = mock_llm

    executor = create_agent()
    assert executor is not None
    assert executor.max_iterations == 10
    assert executor.return_intermediate_steps is True
    assert len(executor.tools) == 6
```

- [ ] **Step 4.3: Run tests**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python -m pytest tests/unit/test_react_agent.py -v
```

Expected: 3 tests pass.

- [ ] **Step 4.4: Git commit**

```
feat(agent): add LangChain ReAct agent with streaming events
```

---

### Task 5: `/v1/agent` SSE endpoint (`app/api/v1/agent.py`)

**Files:**
- Create: `backend/app/api/v1/agent.py`
- Modify: `backend/app/main.py` (add router)

- [ ] **Step 5.1: Create `backend/app/api/v1/agent.py`**

```python
"""POST /v1/agent — SSE endpoint for the Ableton Live ReAct agent.

Streams tool calls, tool results, and tokens as Server-Sent Events.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import verify_api_key
from app.agent.react_agent import stream_agent

router = APIRouter()


class AgentRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    chat_history: Optional[List[Dict[str, Any]]] = None


def _sse(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/agent")
async def agent_endpoint(
    request: AgentRequest,
    _: str = Depends(verify_api_key),
):
    conversation_id = request.conversation_id or str(uuid.uuid4())

    async def generate():
        try:
            async for event in stream_agent(
                query=request.message,
                chat_history=request.chat_history,
            ):
                event_type = event.get("type", "unknown")
                yield _sse(event_type, {
                    **event,
                    "conversation_id": conversation_id,
                })

            yield _sse("done", {"conversation_id": conversation_id})

        except Exception as exc:
            yield _sse("error", {
                "code": "AGENT_ERROR",
                "message": str(exc),
            })

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

- [ ] **Step 5.2: Modify `backend/app/main.py`** — add agent router

Add these two lines at the end of `main.py`:

```python
from app.api.v1.agent import router as agent_router
app.include_router(agent_router, prefix="/v1", tags=["agent"])
```

- [ ] **Step 5.3: Create tests `backend/tests/unit/test_agent_endpoint.py`**

```python
"""Unit tests for POST /v1/agent SSE endpoint."""
from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings


@pytest.fixture
def api_key():
    """Use the configured API key for auth."""
    return settings.api_secret_key or "test-key"


@pytest.fixture
def auth_headers(api_key):
    return {"X-API-Key": api_key}


@pytest.mark.asyncio
async def test_agent_endpoint_streams_events(auth_headers):
    """Mock the agent and verify SSE output format."""

    async def fake_stream(query, chat_history=None):
        yield {"type": "tool_call", "tool": "get_session_info", "input": {}}
        yield {"type": "tool_result", "tool": "get_session_info", "output": {"tempo": 128}}
        yield {"type": "token", "content": "Your tempo is 128 BPM."}

    with patch("app.api.v1.agent.stream_agent", side_effect=fake_stream):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v1/agent",
                json={"message": "What is the tempo?"},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            body = resp.text
            assert "event: tool_call" in body
            assert "event: tool_result" in body
            assert "event: token" in body
            assert "event: done" in body


@pytest.mark.asyncio
async def test_agent_endpoint_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/agent",
            json={"message": "Hello"},
        )
        # Should be 401 or 403 depending on deps implementation
        assert resp.status_code in (401, 403, 422)
```

- [ ] **Step 5.4: Run tests**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python -m pytest tests/unit/test_agent_endpoint.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5.5: Git commit**

```
feat(api): add POST /v1/agent SSE endpoint for Ableton ReAct agent
```

---

## Chunk 3: Max for Live Device

### Task 6: Max for Live bridge script (`ableton/SONIQWERK_bridge.js`)

**Files:**
- Create: `backend/ableton/SONIQWERK_bridge.js`
- Create: `backend/ableton/package.json`

- [ ] **Step 6.1: Create `backend/ableton/package.json`**

```json
{
  "name": "soniqwerk-ableton-bridge",
  "version": "1.0.0",
  "description": "SONIQWERK Max for Live WebSocket bridge (Live 11 + 12)",
  "private": true,
  "dependencies": {
    "ws": "^8.0.0"
  }
}
```

- [ ] **Step 6.2: Create `backend/ableton/SONIQWERK_bridge.js`**

```javascript
/**
 * SONIQWERK Max for Live Bridge — node.script
 *
 * Runs inside a Max for Live device as a node.script object.
 * Connects to the Python WebSocket bridge at ws://localhost:8001/ws.
 * Receives tool-call messages, executes them via LiveAPI (LOM),
 * and sends results back.
 *
 * Compatible with both Ableton Live 11 and Live 12.
 * All LOM paths used are core paths present in both versions.
 */

/* global post, outlet, LiveAPI, Task */
/* eslint-disable no-var */

var WebSocket = require("ws");

var WS_URL = "ws://localhost:8001/ws";
var RECONNECT_DELAY_MS = 3000;

var ws = null;
var reconnectTimer = null;

// ── WebSocket connection ──────────────────────────────────────────

function connect() {
    if (ws) {
        try { ws.close(); } catch (e) { /* ignore */ }
    }

    post("SONIQWERK: connecting to " + WS_URL + "...\n");
    ws = new WebSocket(WS_URL);

    ws.on("open", function () {
        post("SONIQWERK: connected to bridge\n");
        outlet(0, "connected");
    });

    ws.on("message", function (data) {
        try {
            var msg = JSON.parse(data.toString());
            handleMessage(msg);
        } catch (e) {
            post("SONIQWERK: invalid message: " + e.message + "\n");
        }
    });

    ws.on("close", function () {
        post("SONIQWERK: disconnected, reconnecting in " + RECONNECT_DELAY_MS + "ms\n");
        outlet(0, "disconnected");
        scheduleReconnect();
    });

    ws.on("error", function (err) {
        post("SONIQWERK: WebSocket error: " + err.message + "\n");
    });
}

function scheduleReconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(function () {
        connect();
    }, RECONNECT_DELAY_MS);
}

// ── Message dispatcher ───────────────────────────────────────────

function handleMessage(msg) {
    var id = msg.id;
    var action = msg.action;
    var params = msg.params || {};
    var result = null;
    var error = null;

    try {
        switch (action) {
            case "get_session_info":
                result = doGetSessionInfo();
                break;
            case "get_tracks":
                result = doGetTracks();
                break;
            case "get_track_devices":
                result = doGetTrackDevices(params.track_index);
                break;
            case "set_parameter":
                result = doSetParameter(
                    params.track_index,
                    params.device_index,
                    params.param_index,
                    params.value
                );
                break;
            case "get_clips":
                result = doGetClips(params.track_index);
                break;
            case "fire_clip":
                result = doFireClip(params.track_index, params.slot_index);
                break;
            default:
                error = "Unknown action: " + action;
        }
    } catch (e) {
        error = e.message || String(e);
    }

    sendResponse(id, result, error);
}

function sendResponse(id, result, error) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        post("SONIQWERK: cannot send response, WebSocket not open\n");
        return;
    }
    var resp = JSON.stringify({ id: id, result: result, error: error });
    ws.send(resp);
}

// ── LOM helpers (Live 11 + 12 compatible) ────────────────────────

/**
 * Safe LiveAPI getter — returns the value or a default.
 * LiveAPI.get() returns an array; first element is the value.
 * String values from LOM are returned as comma-separated ASCII codes
 * in Live 11/12 — this helper decodes them.
 */
function lomGet(path, property) {
    var api = new LiveAPI(null, path);
    if (!api) return null;
    var raw = api.get(property);
    return raw;
}

function lomGetString(path, property) {
    var api = new LiveAPI(null, path);
    if (!api) return "";
    var raw = api.get(property);
    // LiveAPI returns strings as "stringvalue" — strip quotes
    if (typeof raw === "string") {
        return raw.replace(/^"|"$/g, "");
    }
    if (Array.isArray(raw) && raw.length > 0) {
        return String(raw[0]).replace(/^"|"$/g, "");
    }
    return String(raw);
}

function lomGetNumber(path, property) {
    var api = new LiveAPI(null, path);
    if (!api) return 0;
    var raw = api.get(property);
    if (Array.isArray(raw)) return Number(raw[0]);
    return Number(raw);
}

function lomGetChildCount(path, childList) {
    var api = new LiveAPI(null, path);
    if (!api) return 0;
    var children = api.getcount(childList);
    return children || 0;
}

// ── Action implementations ───────────────────────────────────────

function doGetSessionInfo() {
    var tempo = lomGetNumber("live_set", "tempo");
    var sigNum = lomGetNumber("live_set", "signature_numerator");
    var sigDen = lomGetNumber("live_set", "signature_denominator");
    var isPlaying = lomGetNumber("live_set", "is_playing");
    var trackCount = lomGetChildCount("live_set", "tracks");

    return {
        tempo: tempo,
        time_signature: sigNum + "/" + sigDen,
        track_count: trackCount,
        is_playing: isPlaying === 1
    };
}

function doGetTracks() {
    var count = lomGetChildCount("live_set", "tracks");
    var tracks = [];

    for (var i = 0; i < count; i++) {
        var path = "live_set tracks " + i;
        var name = lomGetString(path, "name");
        var hasInput = lomGetNumber(path, "has_midi_input");
        var isArmed = lomGetNumber(path, "arm");
        var volume = lomGetNumber(path + " mixer_device volume", "value");

        tracks.push({
            name: name,
            index: i,
            type: hasInput === 1 ? "midi" : "audio",
            is_armed: isArmed === 1,
            volume: Math.round(volume * 1000) / 1000
        });
    }

    return { tracks: tracks };
}

function doGetTrackDevices(trackIndex) {
    var trackPath = "live_set tracks " + trackIndex;
    var count = lomGetChildCount(trackPath, "devices");
    var devices = [];

    for (var i = 0; i < count; i++) {
        var devPath = trackPath + " devices " + i;
        var name = lomGetString(devPath, "name");
        var className = lomGetString(devPath, "class_name");

        devices.push({
            name: name,
            index: i,
            type: className
        });
    }

    return { devices: devices };
}

function doSetParameter(trackIndex, deviceIndex, paramIndex, value) {
    var paramPath = "live_set tracks " + trackIndex +
                    " devices " + deviceIndex +
                    " parameters " + paramIndex;

    var api = new LiveAPI(null, paramPath);
    var paramName = lomGetString(paramPath, "name");
    var minVal = lomGetNumber(paramPath, "min");
    var maxVal = lomGetNumber(paramPath, "max");

    // Clamp value to valid range
    var clampedValue = Math.max(minVal, Math.min(maxVal, value));
    api.set("value", clampedValue);

    return {
        ok: true,
        parameter: paramName,
        value: clampedValue,
        range: [minVal, maxVal]
    };
}

function doGetClips(trackIndex) {
    var trackPath = "live_set tracks " + trackIndex;
    var slotCount = lomGetChildCount(trackPath, "clip_slots");
    var clips = [];

    for (var i = 0; i < slotCount; i++) {
        var slotPath = trackPath + " clip_slots " + i;
        var hasClip = lomGetNumber(slotPath, "has_clip");

        if (hasClip === 1) {
            var clipPath = slotPath + " clip";
            var name = lomGetString(clipPath, "name");
            var length = lomGetNumber(clipPath, "length");
            var isPlaying = lomGetNumber(clipPath, "is_playing");

            clips.push({
                name: name,
                slot_index: i,
                length: length,
                is_playing: isPlaying === 1
            });
        }
    }

    return { clips: clips };
}

function doFireClip(trackIndex, slotIndex) {
    var slotPath = "live_set tracks " + trackIndex + " clip_slots " + slotIndex;
    var hasClip = lomGetNumber(slotPath, "has_clip");

    if (hasClip !== 1) {
        throw new Error("No clip in track " + trackIndex + " slot " + slotIndex);
    }

    var clipPath = slotPath + " clip";
    var api = new LiveAPI(null, clipPath);
    api.call("fire");

    var clipName = lomGetString(clipPath, "name");
    return {
        ok: true,
        clip: clipName,
        track_index: trackIndex,
        slot_index: slotIndex
    };
}

// ── Lifecycle ─────────────────────────────────────────────────────

// Auto-connect when the script loads in Max for Live
connect();

// Expose connect/disconnect for Max messages
// In Max for Live, sending "connect" or "disconnect" to the node.script
// object triggers these functions.
module.exports = {
    connect: connect,
    disconnect: function () {
        if (reconnectTimer) clearTimeout(reconnectTimer);
        if (ws) ws.close();
        post("SONIQWERK: manually disconnected\n");
    }
};
```

- [ ] **Step 6.3: Git commit**

```
feat(ableton): add Max for Live WebSocket bridge script (Live 11 + 12)
```

---

### Task 7: README + setup guide (`ableton/README.md`)

**Files:**
- Create: `backend/ableton/README.md`

- [ ] **Step 7.1: Create `backend/ableton/README.md`**

```markdown
# SONIQWERK Ableton Live Bridge

Connect SONIQWERK's AI agent to Ableton Live for natural-language DAW control.

**Compatible with Ableton Live 11 and Live 12.**

## Architecture

```
Ableton Live 11/12
  └── Max for Live device (SONIQWERK.amxd)
       └── node.script (SONIQWERK_bridge.js)
            ↕ WebSocket ws://localhost:8001/ws
Python WebSocket Bridge (port 8001)
  └── LangChain ReAct agent (6 tools)
       └── FastAPI /v1/agent endpoint (port 8000)
```

## Prerequisites

- Ableton Live 11 or Live 12 (Suite or Standard with Max for Live)
- Max for Live enabled
- Node.js (bundled with Max 8.x — no separate install needed)
- Python 3.9+ with the SONIQWERK backend

## Setup

### 1. Install Node dependencies

```bash
cd backend/ableton
npm install
```

This installs the `ws` WebSocket library used by the bridge script.

### 2. Create the Max for Live device

1. Open Ableton Live (11 or 12)
2. Create a new MIDI track
3. In the browser, go to **Max for Live > Max MIDI Effect**
4. Drag it onto the track
5. Click **Edit** (the wrench icon) to open the Max editor
6. Add a `node.script` object to the patcher
7. Set the script path to: `SONIQWERK_bridge.js`
   - In the node.script inspector, set the **Script File** to the full path:
     `<your-path>/backend/ableton/SONIQWERK_bridge.js`
8. Save the device as `SONIQWERK.amxd`
9. Close the Max editor

### 3. Start the Python bridge

```bash
cd backend
python -m ws_bridge
```

The bridge starts on `ws://localhost:8001/ws` and waits for the Max for Live
device to connect.

### 4. Start the main API

```bash
cd backend
uvicorn app.main:app --port 8000
```

### 5. Connect

Once both servers are running and the Max for Live device is loaded,
you should see `SONIQWERK: connected to bridge` in the Max console.

## Available Commands

The AI agent can perform these actions through natural language:

| Action | What it does |
|--------|-------------|
| `get_session_info` | Read tempo, time signature, track count, play state |
| `get_tracks` | List all tracks (name, type, armed, volume) |
| `get_track_devices` | List devices on a track |
| `set_parameter` | Change a device parameter value |
| `get_clips` | List clips on a track |
| `fire_clip` | Trigger a clip |

**Example prompts:**
- "What's the current tempo?"
- "Show me all tracks in my session"
- "Set the filter cutoff on track 0, device 1 to 0.7"
- "Fire the clip in slot 2 on the bass track"

## Live 11 vs Live 12 Differences

This bridge uses only core LOM (Live Object Model) paths that are
identical in both versions:

- `live_set` — session root
- `live_set tracks N` — track access
- `live_set tracks N devices M parameters P` — parameter control
- `live_set tracks N clip_slots M clip` — clip access

**Live 12 additions** (not used by this bridge, but available for future tools):
- MIDI Transformations API
- New device types (Drift, Meld)
- Enhanced automation curves

The `node.script` JavaScript runtime and `LiveAPI` object work the same
in both Max for Live 8.x versions shipped with Live 11 and Live 12.

## Troubleshooting

### "No Max for Live client connected"
- Make sure the SONIQWERK.amxd device is loaded on a track
- Check the Max console for connection errors
- Verify the Python bridge is running on port 8001

### Connection drops / reconnects
The bridge auto-reconnects every 3 seconds. If you restart the Python
bridge, the Max for Live device will reconnect automatically.

### "Script not found" in Max
- Ensure you ran `npm install` in the `backend/ableton/` directory
- Verify the script path in the node.script inspector points to the
  correct absolute path of `SONIQWERK_bridge.js`
- Check that `node_modules/ws/` exists in the ableton directory

### Live 11: Max console shows errors
- Verify Max for Live is updated to the latest version (Max 8.5+)
- Both Live 11 and 12 ship with Max 8.x; the `node.script` and
  `LiveAPI` APIs are the same

### Port conflict on 8001
Change the port in `backend/app/config.py` (`ableton_ws_port`) and
update `WS_URL` in `SONIQWERK_bridge.js` to match.
```

- [ ] **Step 7.2: Git commit**

```
docs(ableton): add setup guide for Live 11 and Live 12
```

---

## Summary

| Chunk | Task | Files | Tests |
|-------|------|-------|-------|
| 1 | Protocol + message types | `ws_bridge/__init__.py`, `ws_bridge/protocol.py` | 9 |
| 1 | WebSocket bridge server | `ws_bridge/bridge.py`, `ws_bridge/__main__.py` | 4 |
| 2 | LangChain tools | `app/agent/__init__.py`, `app/agent/tools.py` | 10 |
| 2 | ReAct agent | `app/agent/react_agent.py` | 3 |
| 2 | `/v1/agent` endpoint | `app/api/v1/agent.py`, `app/main.py` (mod) | 2 |
| 3 | Max for Live bridge | `ableton/SONIQWERK_bridge.js`, `ableton/package.json` | — |
| 3 | README | `ableton/README.md` | — |

**Total: 7 tasks, 12 files, 28 unit tests, 7 git commits.**

### Full test command

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python -m pytest tests/unit/test_ws_protocol.py tests/unit/test_ws_bridge.py tests/unit/test_agent_tools.py tests/unit/test_react_agent.py tests/unit/test_agent_endpoint.py -v
```

### Dependencies to add to `requirements.txt`

```
langchain>=0.2.0
langchain-openai>=0.1.0
langchain-core>=0.2.0
websockets>=12.0
```
