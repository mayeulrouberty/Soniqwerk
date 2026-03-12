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
    assert len(ALL_TOOLS) == 17


def test_all_tools_have_names():
    names = {t.name for t in ALL_TOOLS}
    assert {
        "get_session_info",
        "get_tracks",
        "get_track_devices",
        "set_parameter",
        "get_clips",
        "fire_clip",
    }.issubset(names)


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
