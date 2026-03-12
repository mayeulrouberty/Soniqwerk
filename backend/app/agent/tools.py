"""LangChain tools for Ableton Live control via the WebSocket bridge.

All 6 tools use send_command() from ws_bridge.bridge, which sends a
JSON message to the Max for Live node.script and awaits a response.

Every LOM path used here is compatible with both Live 11 and Live 12.
"""
from __future__ import annotations

import asyncio
from typing import List, Optional

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


# ── Session ─────────────────────────────────────────────────────────────────

@tool
async def set_session(bpm: float, time_signature: str = "4/4", name: str = "") -> dict:
    """Set session-level properties: tempo (BPM), time signature, and project name.

    Args:
        bpm: Tempo in beats per minute (e.g. 174 for DnB, 135 for Techno).
        time_signature: Time signature string, e.g. "4/4", "3/4", "6/8".
        name: Optional project name to set.
    """
    return await _safe_send("set_session", {"bpm": bpm, "time_signature": time_signature, "name": name})


# ── Tracks ───────────────────────────────────────────────────────────────────

@tool
async def create_instrument_track(name: str, instrument: str, color: str = "") -> dict:
    """Create a new MIDI track, load an instrument, and set name and color.

    Args:
        name: Track name (e.g. "Reese Bass", "Amen Break").
        instrument: Instrument to load, e.g. "Drift", "Operator", "Wavetable", "Simpler", "Sampler", "Drum Rack".
        color: Optional color hint (e.g. "blue", "orange", "green").
    Returns:
        Dict with track_index of the newly created track.
    """
    return await _safe_send("create_instrument_track", {"name": name, "instrument": instrument, "color": color})


@tool
async def create_audio_track(name: str, color: str = "") -> dict:
    """Create a new audio track with a name and optional color.

    Args:
        name: Track name (e.g. "Vocals", "Guitar").
        color: Optional color hint.
    Returns:
        Dict with track_index of the newly created track.
    """
    return await _safe_send("create_audio_track", {"name": name, "color": color})


@tool
async def delete_track(track_index: int) -> dict:
    """Delete a track by its index.

    Args:
        track_index: 0-based index of the track to delete.
    """
    return await _safe_send("delete_track", {"track_index": track_index})


@tool
async def set_track_mix(
    track_index: int,
    volume: float = 0.85,
    pan: float = 0.0,
    mute: bool = False,
) -> dict:
    """Set volume, panning and mute state for a track in one call.

    Args:
        track_index: 0-based track index.
        volume: Volume level 0.0-1.0 (0.85 approx -3dB, good default).
        pan: Panning -1.0 (left) to 1.0 (right). 0.0 = center.
        mute: Whether to mute the track.
    """
    return await _safe_send("set_track_mix", {
        "track_index": track_index,
        "volume": volume,
        "pan": pan,
        "mute": mute,
    })


# ── Clips & MIDI ─────────────────────────────────────────────────────────────

@tool
async def create_midi_clip(track_index: int, slot_index: int, length_bars: int = 2) -> dict:
    """Create an empty MIDI clip in a clip slot.

    Args:
        track_index: 0-based track index.
        slot_index: 0-based clip slot index.
        length_bars: Clip length in bars (default 2). Assumes 4/4 time.
    """
    return await _safe_send("create_midi_clip", {
        "track_index": track_index,
        "slot_index": slot_index,
        "length_bars": length_bars,
    })


@tool
async def write_notes(track_index: int, slot_index: int, notes: List[dict]) -> dict:
    """Write MIDI notes into an existing clip, replacing any existing notes.

    Each note dict must have:
      - pitch (int): MIDI note 0-127. C3=48, C4=60, A4=69.
      - time (float): Start position in beats. 0.0=bar start, 0.25=16th, 0.5=8th, 1.0=quarter.
      - duration (float): Duration in beats.
      - velocity (int): 1-127. 64=medium, 100=strong.
      - mute (bool, optional): Whether note is muted.

    Args:
        track_index: 0-based track index.
        slot_index: 0-based clip slot index (clip must already exist).
        notes: List of note dicts.
    """
    return await _safe_send("write_notes", {
        "track_index": track_index,
        "slot_index": slot_index,
        "notes": notes,
    })


@tool
async def set_clip_name(track_index: int, slot_index: int, name: str) -> dict:
    """Rename a clip.

    Args:
        track_index: 0-based track index.
        slot_index: 0-based clip slot index.
        name: New clip name (e.g. "Drop 1 Bass", "Intro Pad").
    """
    return await _safe_send("set_clip_name", {
        "track_index": track_index,
        "slot_index": slot_index,
        "name": name,
    })


# ── Devices & Effects ─────────────────────────────────────────────────────────

@tool
async def load_effect(track_index: int, effect_name: str, position: int = -1) -> dict:
    """Load an audio effect onto a track's device chain.

    Args:
        track_index: 0-based track index.
        effect_name: Effect name, e.g. "Reverb", "Delay", "Compressor", "EQ Eight",
                     "Auto Filter", "Saturator", "Chorus", "Phaser", "Redux".
        position: Position in device chain. -1 = append at end (default).
    """
    return await _safe_send("load_effect", {
        "track_index": track_index,
        "effect_name": effect_name,
        "position": position,
    })


# ── Arrangement ───────────────────────────────────────────────────────────────

@tool
async def create_scene(name: str, scene_index: int = -1) -> dict:
    """Create a new scene (row in session view) with a name.

    Args:
        name: Scene name (e.g. "Intro", "Drop 1", "Break", "Outro").
        scene_index: Position to insert. -1 = append at end.
    Returns:
        Dict with scene_index of the created scene.
    """
    return await _safe_send("create_scene", {"name": name, "scene_index": scene_index})


# ── Automation ────────────────────────────────────────────────────────────────

@tool
async def write_automation(
    track_index: int,
    device_index: int,
    param_index: int,
    points: List[dict],
) -> dict:
    """Write an automation envelope for a device parameter.

    Each point: {"time": <beat_position>, "value": <0.0-1.0>}.
    Points are interpolated linearly.

    Args:
        track_index: 0-based track index.
        device_index: 0-based device index on that track.
        param_index: 0-based parameter index on that device.
        points: List of automation points, e.g. [{"time": 0.0, "value": 0.1}, {"time": 8.0, "value": 0.9}]
    """
    return await _safe_send("write_automation", {
        "track_index": track_index,
        "device_index": device_index,
        "param_index": param_index,
        "points": points,
    })


# ── Sample library ────────────────────────────────────────────────────────────

@tool
async def search_samples(query: str, limit: int = 10) -> dict:
    """Search the local sample library by filename keyword.

    Returns a list of matching samples with their full file paths.
    Use load_sample() to load a result into a track's Simpler or Sampler device.

    Args:
        query: Search keyword, e.g. "kick", "snare 909", "amen break", "bass 808"
        limit: Maximum results to return (default 10)
    """
    from app.agent.sample_library import get_library
    results = get_library().search(query, limit)
    return {"samples": results, "count": len(results)}


@tool
async def load_sample(track_index: int, sample_path: str) -> dict:
    """Load a sample file into the instrument on a track (Simpler or Sampler).

    The track must already have a Simpler or Sampler device loaded.
    Get sample_path from search_samples() results.

    Args:
        track_index: 0-based track index
        sample_path: Absolute path to the audio file (from search_samples results)
    """
    return await _safe_send("load_sample", {
        "track_index": track_index,
        "sample_path": sample_path,
    })


# ── Device presets ────────────────────────────────────────────────────────────

@tool
async def get_device_parameters(track_index: int, device_index: int) -> dict:
    """Get all parameters of a device with their current values.

    Returns a list of {index, name, value, min, max} dicts.
    Useful before save_device_preset to inspect what will be saved.

    Args:
        track_index: 0-based track index
        device_index: 0-based device index on that track
    """
    return await _safe_send("get_device_parameters", {
        "track_index": track_index,
        "device_index": device_index,
    })


@tool
async def save_device_preset(name: str, track_index: int, device_index: int) -> dict:
    """Save the current state of a device as a named preset.

    Reads all device parameters and writes them to backend/data/presets/{name}.json.
    Works with any device — native Live instruments, effects, or VSTs.

    Args:
        name: Preset name, e.g. "Reese Bass V1", "Dark Pad"
        track_index: 0-based track index
        device_index: 0-based device index on that track
    """
    params_result = await _safe_send("get_device_parameters", {
        "track_index": track_index,
        "device_index": device_index,
    })
    if "error" in params_result:
        return params_result

    devices_result = await _safe_send("get_track_devices", {"track_index": track_index})
    device_name = "Unknown"
    devices = devices_result.get("devices", [])
    if device_index < len(devices):
        device_name = devices[device_index].get("name", "Unknown")

    from app.agent.preset_store import save_preset
    params = params_result.get("params", [])
    path = save_preset(name, track_index, device_index, device_name, params)
    return {"success": True, "name": name, "path": path, "params_count": len(params)}


@tool
async def load_device_preset(name: str, track_index: int, device_index: int) -> dict:
    """Restore a previously saved preset to a device.

    Reads the preset JSON and applies each saved parameter value.
    The target device should be the same type as when the preset was saved.

    Args:
        name: Preset name (from list_device_presets)
        track_index: 0-based track index to apply preset to
        device_index: 0-based device index to apply preset to
    """
    from app.agent.preset_store import load_preset
    try:
        preset = load_preset(name)
    except FileNotFoundError:
        return {"error": f"Preset not found: {name!r}. Use list_device_presets() to see available."}

    params = preset.get("params", [])
    errors = 0
    for param in params:
        res = await _safe_send("set_parameter", {
            "track_index": track_index,
            "device_index": device_index,
            "param_index": param["index"],
            "value": param["value"],
        })
        if "error" in res:
            errors += 1

    return {
        "success": True,
        "name": name,
        "params_restored": len(params) - errors,
        "errors": errors,
    }


@tool
async def list_device_presets() -> dict:
    """List all saved device presets.

    Returns a sorted list of {name, device_name, created_at} dicts.
    """
    from app.agent.preset_store import list_presets
    presets = list_presets()
    return {"presets": presets, "count": len(presets)}


# Export all tools as a list for the agent
ALL_TOOLS = [
    # Original 6
    get_session_info,
    get_tracks,
    get_track_devices,
    set_parameter,
    get_clips,
    fire_clip,
    # New 11
    set_session,
    create_instrument_track,
    create_audio_track,
    delete_track,
    set_track_mix,
    create_midi_clip,
    write_notes,
    set_clip_name,
    load_effect,
    create_scene,
    write_automation,
    # C3 — Sample library
    search_samples,
    load_sample,
    # C4 — Device presets
    get_device_parameters,
    save_device_preset,
    load_device_preset,
    list_device_presets,
]
