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
