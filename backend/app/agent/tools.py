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
        value: New parameter value (float, typically 0.0-1.0).
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
