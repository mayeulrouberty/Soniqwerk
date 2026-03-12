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
