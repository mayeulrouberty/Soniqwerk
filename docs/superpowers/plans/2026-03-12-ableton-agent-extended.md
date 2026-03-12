# Ableton Live Agent — Extended Tools (C1) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Soniqwerk Ableton agent with 12 composite LOM tools, a music theory engine, genre templates, and an enriched system prompt — enabling the agent to create complete tracks from a single natural language prompt.

**Architecture:** Three new Python modules (music_theory, genre_templates, extended tools) + extended bridge JS. All Python code is Python 3.9 compatible. Music theory and genre template modules are pure Python (no LOM calls) — fully testable without Ableton. Bridge JS changes require manual testing with Live 11/12.

**Tech Stack:** Python 3.9, LangChain `@tool`, asyncio, `max-api` (Max for Live node.script), WebSocket bridge

---

## Chunk 1: Music theory engine

### Task 1: `music_theory.py` — Scale engine + note utilities

**Files:**
- Create: `backend/app/agent/music_theory.py`
- Create: `backend/tests/test_music_theory.py`

**Context:** Pure Python module. No LOM calls, no LangChain dependencies. Used by the agent to compute MIDI pitches before calling `write_notes`. Must be testable standalone.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_music_theory.py`:

```python
import pytest
from app.agent.music_theory import (
    note_name_to_midi,
    get_scale_notes,
    quantize_to_scale,
    humanize_notes,
    SCALES,
)


def test_note_name_to_midi_c4():
    assert note_name_to_midi("C4") == 60


def test_note_name_to_midi_c3():
    assert note_name_to_midi("C3") == 48


def test_note_name_to_midi_fsharp4():
    assert note_name_to_midi("F#4") == 66


def test_note_name_to_midi_bb3():
    assert note_name_to_midi("Bb3") == 58


def test_get_scale_notes_c_major():
    notes = get_scale_notes("C", "major", octave=4)
    assert notes == [60, 62, 64, 65, 67, 69, 71, 72]


def test_get_scale_notes_c_minor():
    notes = get_scale_notes("C", "natural_minor", octave=3)
    assert notes == [48, 50, 51, 53, 55, 56, 58, 60]


def test_get_scale_notes_dorian():
    notes = get_scale_notes("D", "dorian", octave=4)
    assert 62 in notes  # D4 = 62
    assert len(notes) == 8


def test_get_scale_notes_pentatonic_minor():
    notes = get_scale_notes("A", "pentatonic_minor", octave=3)
    assert len(notes) == 5


def test_scales_dict_contains_expected_scales():
    for scale in ["major", "natural_minor", "dorian", "phrygian", "lydian",
                  "mixolydian", "locrian", "harmonic_minor", "melodic_minor",
                  "pentatonic_major", "pentatonic_minor", "blues"]:
        assert scale in SCALES, f"Missing scale: {scale}"


def test_quantize_to_scale_already_in_scale():
    scale_notes = get_scale_notes("C", "major", octave=4)
    result = quantize_to_scale([60, 62, 64], "C", "major")
    assert result == [60, 62, 64]


def test_quantize_to_scale_out_of_scale_pitch():
    # C# (61) is not in C major — should snap to C (60) or D (62)
    result = quantize_to_scale([61], "C", "major")
    assert result[0] in [60, 62]


def test_humanize_notes_preserves_pitch():
    notes = [{"pitch": 60, "time": 0.0, "duration": 0.25, "velocity": 100}]
    result = humanize_notes(notes, velocity_range=10, timing_range=0.02)
    assert result[0]["pitch"] == 60


def test_humanize_notes_varies_velocity():
    notes = [{"pitch": 60, "time": 0.0, "duration": 0.25, "velocity": 100}] * 20
    result = humanize_notes(notes, velocity_range=20, timing_range=0.0)
    velocities = [n["velocity"] for n in result]
    assert len(set(velocities)) > 1  # must vary


def test_humanize_notes_velocity_clamped():
    notes = [{"pitch": 60, "time": 0.0, "duration": 0.25, "velocity": 127}] * 10
    result = humanize_notes(notes, velocity_range=30, timing_range=0.0)
    for n in result:
        assert 1 <= n["velocity"] <= 127
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python3 -m pytest tests/test_music_theory.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'app.agent.music_theory'`

- [ ] **Step 3: Implement `app/agent/music_theory.py`**

Create `backend/app/agent/music_theory.py`:

```python
from __future__ import annotations

import random
from typing import Dict, List

# Semitone intervals from root for each scale
SCALES: Dict[str, List[int]] = {
    "major":            [0, 2, 4, 5, 7, 9, 11, 12],
    "natural_minor":    [0, 2, 3, 5, 7, 8, 10, 12],
    "harmonic_minor":   [0, 2, 3, 5, 7, 8, 11, 12],
    "melodic_minor":    [0, 2, 3, 5, 7, 9, 11, 12],
    "dorian":           [0, 2, 3, 5, 7, 9, 10, 12],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10, 12],
    "lydian":           [0, 2, 4, 6, 7, 9, 11, 12],
    "mixolydian":       [0, 2, 4, 5, 7, 9, 10, 12],
    "locrian":          [0, 1, 3, 5, 6, 8, 10, 12],
    "pentatonic_major": [0, 2, 4, 7, 9, 12],
    "pentatonic_minor": [0, 3, 5, 7, 10, 12],
    "blues":            [0, 3, 5, 6, 7, 10, 12],
    "diminished":       [0, 2, 3, 5, 6, 8, 9, 11, 12],
    "whole_tone":       [0, 2, 4, 6, 8, 10, 12],
    "chromatic":        list(range(13)),
}

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_NOTE_ALIASES = {"Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#", "Ab": "G#", "Bb": "A#", "Cb": "B"}


def note_name_to_midi(note: str) -> int:
    """Convert note name like 'C4', 'F#3', 'Bb2' to MIDI pitch number.

    C4 = 60 (middle C). Supports sharps (#) and flats (b).
    """
    # Split note name from octave number
    if len(note) >= 2 and note[-1].isdigit():
        pitch_part = note[:-1]
        octave = int(note[-1])
    elif len(note) >= 3 and note[-2:].lstrip("-").isdigit():
        pitch_part = note[:-2]
        octave = int(note[-2:])
    else:
        raise ValueError(f"Cannot parse note: {note!r}")

    pitch_part = _NOTE_ALIASES.get(pitch_part, pitch_part)
    if pitch_part not in _NOTE_NAMES:
        raise ValueError(f"Unknown note name: {pitch_part!r}")

    semitone = _NOTE_NAMES.index(pitch_part)
    return (octave + 1) * 12 + semitone


def get_scale_notes(root: str, scale: str, octave: int = 4) -> List[int]:
    """Return MIDI pitch numbers for a scale starting at root in given octave.

    Args:
        root: Root note name, e.g. "C", "F#", "Bb"
        scale: Scale name from SCALES dict, e.g. "major", "dorian", "pentatonic_minor"
        octave: Octave number (C4 = 60)

    Returns:
        List of MIDI pitch numbers, ascending, including the octave root.
    """
    if scale not in SCALES:
        raise ValueError(f"Unknown scale: {scale!r}. Available: {list(SCALES)}")

    root_midi = note_name_to_midi(f"{root}{octave}")
    intervals = SCALES[scale]
    return [root_midi + interval for interval in intervals]


def quantize_to_scale(pitches: List[int], root: str, scale: str) -> List[int]:
    """Snap each pitch to the nearest note in the given scale (any octave).

    Args:
        pitches: List of MIDI pitch numbers to quantize
        root: Root note name, e.g. "C"
        scale: Scale name from SCALES dict

    Returns:
        List of quantized MIDI pitch numbers.
    """
    root_semitone = _NOTE_NAMES.index(_NOTE_ALIASES.get(root, root))
    intervals = set(i % 12 for i in SCALES[scale])

    result = []
    for pitch in pitches:
        semitone = (pitch - root_semitone) % 12
        if semitone in intervals:
            result.append(pitch)
        else:
            # Find nearest semitone in scale
            best = min(intervals, key=lambda s: min(abs(semitone - s), 12 - abs(semitone - s)))
            diff = best - semitone
            if diff > 6:
                diff -= 12
            elif diff < -6:
                diff += 12
            result.append(pitch + diff)
    return result


def humanize_notes(
    notes: List[dict],
    velocity_range: int = 10,
    timing_range: float = 0.02,
) -> List[dict]:
    """Add subtle velocity and timing variations to a list of note dicts.

    Args:
        notes: List of dicts with keys: pitch, time, duration, velocity
        velocity_range: Max ± velocity variation (e.g. 10 means ±10)
        timing_range: Max ± timing shift in beats (e.g. 0.02 = ±0.02 beats)

    Returns:
        New list of note dicts with humanized velocity and time values.
    """
    result = []
    for note in notes:
        humanized = dict(note)
        if velocity_range > 0:
            delta_v = random.randint(-velocity_range, velocity_range)
            humanized["velocity"] = max(1, min(127, note["velocity"] + delta_v))
        if timing_range > 0:
            delta_t = random.uniform(-timing_range, timing_range)
            humanized["time"] = max(0.0, note["time"] + delta_t)
        result.append(humanized)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python3 -m pytest tests/test_music_theory.py -v
```

Expected: **14/14 PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
git add app/agent/music_theory.py tests/test_music_theory.py
git commit -m "feat(agent): add music theory engine — scales, note conversion, humanization"
```

---

### Task 2: `genre_templates.py` — Genre knowledge base

**Files:**
- Create: `backend/app/agent/genre_templates.py`
- Create: `backend/tests/test_genre_templates.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_genre_templates.py`:

```python
import pytest
from app.agent.genre_templates import (
    get_template,
    get_arrangement_sections,
    list_genres,
    GenreTemplate,
    Section,
)


def test_list_genres_contains_expected():
    genres = list_genres()
    for g in ["dnb", "techno", "house", "trap", "ambient", "lofi"]:
        assert g in genres


def test_get_template_dnb():
    t = get_template("dnb")
    assert isinstance(t, GenreTemplate)
    assert t.typical_bpm == 174
    assert t.time_signature == "4/4"
    assert len(t.arrangement) >= 5


def test_get_template_techno():
    t = get_template("techno")
    assert 125 <= t.typical_bpm <= 145


def test_get_template_house():
    t = get_template("house")
    assert 120 <= t.typical_bpm <= 130


def test_get_template_unknown_raises():
    with pytest.raises(ValueError, match="Unknown genre"):
        get_template("jazz")


def test_get_arrangement_sections_returns_sections():
    sections = get_arrangement_sections("dnb", total_bars=120)
    assert len(sections) > 0
    assert all(isinstance(s, Section) for s in sections)


def test_section_has_name_and_bars():
    sections = get_arrangement_sections("techno", total_bars=64)
    for s in sections:
        assert s.name
        assert s.bars > 0


def test_genre_template_has_mix_hints():
    t = get_template("dnb")
    assert "kick" in t.mix_hints or "bass" in t.mix_hints


def test_genre_template_track_types():
    t = get_template("dnb")
    assert len(t.track_types) >= 4
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python3 -m pytest tests/test_genre_templates.py -v 2>&1 | head -15
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `app/agent/genre_templates.py`**

Create `backend/app/agent/genre_templates.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class Section:
    name: str
    bars: int


@dataclass
class GenreTemplate:
    genre: str
    typical_bpm: int
    bpm_range: Tuple[int, int]
    time_signature: str
    arrangement: List[Section]
    track_types: List[str]
    mix_hints: Dict[str, Dict[str, float]]


_TEMPLATES: Dict[str, GenreTemplate] = {
    "dnb": GenreTemplate(
        genre="dnb",
        typical_bpm=174,
        bpm_range=(160, 180),
        time_signature="4/4",
        arrangement=[
            Section("Intro", 16),
            Section("Build", 8),
            Section("Drop 1", 32),
            Section("Break", 16),
            Section("Build 2", 8),
            Section("Drop 2", 32),
            Section("Outro", 8),
        ],
        track_types=["kick", "snare", "amen_break", "bass", "pad", "lead", "fx", "atmospheric"],
        mix_hints={
            "kick":       {"volume": 0.9,  "pan": 0.0},
            "snare":      {"volume": 0.85, "pan": 0.0},
            "amen_break": {"volume": 0.8,  "pan": 0.0},
            "bass":       {"volume": 0.82, "pan": 0.0},
            "pad":        {"volume": 0.65, "pan": 0.0},
            "lead":       {"volume": 0.75, "pan": 0.0},
        },
    ),
    "techno": GenreTemplate(
        genre="techno",
        typical_bpm=135,
        bpm_range=(125, 145),
        time_signature="4/4",
        arrangement=[
            Section("Intro", 32),
            Section("Build", 16),
            Section("Main", 64),
            Section("Break", 32),
            Section("Drop", 64),
            Section("Outro", 16),
        ],
        track_types=["kick", "hihat", "clap", "bass", "synth_lead", "synth_pad", "fx", "percussion"],
        mix_hints={
            "kick":       {"volume": 0.92, "pan": 0.0},
            "hihat":      {"volume": 0.7,  "pan": 0.1},
            "bass":       {"volume": 0.8,  "pan": 0.0},
            "synth_lead": {"volume": 0.72, "pan": 0.0},
            "synth_pad":  {"volume": 0.6,  "pan": 0.0},
        },
    ),
    "house": GenreTemplate(
        genre="house",
        typical_bpm=124,
        bpm_range=(118, 130),
        time_signature="4/4",
        arrangement=[
            Section("Intro", 16),
            Section("Verse 1", 32),
            Section("Build", 8),
            Section("Drop", 32),
            Section("Break", 16),
            Section("Verse 2", 32),
            Section("Drop 2", 32),
            Section("Outro", 16),
        ],
        track_types=["kick", "hihat", "clap", "bass", "chord", "lead", "vocal_chop", "fx"],
        mix_hints={
            "kick":       {"volume": 0.9,  "pan": 0.0},
            "bass":       {"volume": 0.8,  "pan": 0.0},
            "chord":      {"volume": 0.65, "pan": 0.0},
            "lead":       {"volume": 0.72, "pan": 0.05},
        },
    ),
    "trap": GenreTemplate(
        genre="trap",
        typical_bpm=140,
        bpm_range=(130, 160),
        time_signature="4/4",
        arrangement=[
            Section("Intro", 8),
            Section("Verse 1", 16),
            Section("Hook", 16),
            Section("Verse 2", 16),
            Section("Hook", 16),
            Section("Bridge", 8),
            Section("Outro", 8),
        ],
        track_types=["808", "kick", "snare", "hihat", "bass", "melody", "pad", "fx"],
        mix_hints={
            "808":    {"volume": 0.88, "pan": 0.0},
            "kick":   {"volume": 0.85, "pan": 0.0},
            "melody": {"volume": 0.72, "pan": 0.0},
        },
    ),
    "ambient": GenreTemplate(
        genre="ambient",
        typical_bpm=90,
        bpm_range=(60, 110),
        time_signature="4/4",
        arrangement=[
            Section("Intro", 32),
            Section("Development", 64),
            Section("Climax", 32),
            Section("Resolution", 32),
        ],
        track_types=["pad", "texture", "melody", "bass_drone", "fx", "field_recording"],
        mix_hints={
            "pad":     {"volume": 0.7, "pan": 0.0},
            "texture": {"volume": 0.6, "pan": 0.1},
            "melody":  {"volume": 0.65, "pan": 0.0},
        },
    ),
    "lofi": GenreTemplate(
        genre="lofi",
        typical_bpm=85,
        bpm_range=(70, 95),
        time_signature="4/4",
        arrangement=[
            Section("Intro", 8),
            Section("Main", 32),
            Section("Break", 8),
            Section("Main 2", 32),
            Section("Outro", 8),
        ],
        track_types=["drums", "bass", "piano", "guitar", "pad", "fx"],
        mix_hints={
            "drums": {"volume": 0.75, "pan": 0.0},
            "bass":  {"volume": 0.78, "pan": 0.0},
            "piano": {"volume": 0.7,  "pan": 0.05},
        },
    ),
}


def list_genres() -> List[str]:
    """Return list of available genre names."""
    return list(_TEMPLATES.keys())


def get_template(genre: str) -> GenreTemplate:
    """Get genre template by name.

    Args:
        genre: Genre name (e.g. "dnb", "techno", "house")

    Raises:
        ValueError: If genre is not found.
    """
    key = genre.lower().replace("-", "").replace(" ", "")
    if key not in _TEMPLATES:
        raise ValueError(f"Unknown genre: {genre!r}. Available: {list_genres()}")
    return _TEMPLATES[key]


def get_arrangement_sections(genre: str, total_bars: int = 120) -> List[Section]:
    """Return arrangement sections for a genre, scaled to total_bars if needed.

    Args:
        genre: Genre name
        total_bars: Target total bar count (sections may be proportionally adjusted)

    Returns:
        List of Section objects with name and bars.
    """
    template = get_template(genre)
    sections = template.arrangement

    # Scale sections proportionally if total_bars differs significantly
    template_total = sum(s.bars for s in sections)
    if total_bars and abs(total_bars - template_total) > 8:
        ratio = total_bars / template_total
        scaled = [Section(s.name, max(4, round(s.bars * ratio))) for s in sections]
        return scaled

    return list(sections)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python3 -m pytest tests/test_genre_templates.py -v
```

Expected: **9/9 PASS**

- [ ] **Step 5: Commit**

```bash
git add app/agent/genre_templates.py tests/test_genre_templates.py
git commit -m "feat(agent): add genre templates — DnB, Techno, House, Trap, Ambient, Lofi"
```

---

## Chunk 2: Extended LOM tools

### Task 3: Add 12 composite tools to `tools.py`

**Files:**
- Modify: `backend/app/agent/tools.py`
- Create: `backend/tests/test_extended_tools.py`

**Context:** The existing 6 tools stay unchanged. Add 12 new composite tools using the same `@tool` + `_safe_send` pattern. All tools are Python 3.9 compatible (`List[dict]` not `list[dict]`).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_extended_tools.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_set_session_sends_correct_params():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        import importlib
        import app.agent.tools as tools_module
        importlib.reload(tools_module)
        from app.agent.tools import set_session
        result = await set_session.ainvoke({"bpm": 174, "time_signature": "4/4", "name": "My Track"})
        mock_send.assert_called_once_with("set_session", {"bpm": 174, "time_signature": "4/4", "name": "My Track"})


@pytest.mark.asyncio
async def test_create_instrument_track():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"track_index": 0}
        from app.agent.tools import create_instrument_track
        result = await create_instrument_track.ainvoke({
            "name": "Bass", "instrument": "Drift", "color": "blue"
        })
        mock_send.assert_called_once_with("create_instrument_track", {
            "name": "Bass", "instrument": "Drift", "color": "blue"
        })


@pytest.mark.asyncio
async def test_create_audio_track():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"track_index": 1}
        from app.agent.tools import create_audio_track
        await create_audio_track.ainvoke({"name": "Vocals", "color": ""})
        mock_send.assert_called_once_with("create_audio_track", {"name": "Vocals", "color": ""})


@pytest.mark.asyncio
async def test_delete_track():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import delete_track
        await delete_track.ainvoke({"track_index": 2})
        mock_send.assert_called_once_with("delete_track", {"track_index": 2})


@pytest.mark.asyncio
async def test_set_track_mix():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import set_track_mix
        await set_track_mix.ainvoke({"track_index": 0, "volume": 0.8, "pan": 0.0, "mute": False})
        mock_send.assert_called_once_with("set_track_mix", {
            "track_index": 0, "volume": 0.8, "pan": 0.0, "mute": False
        })


@pytest.mark.asyncio
async def test_create_midi_clip():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import create_midi_clip
        await create_midi_clip.ainvoke({"track_index": 0, "slot_index": 0, "length_bars": 2})
        mock_send.assert_called_once_with("create_midi_clip", {
            "track_index": 0, "slot_index": 0, "length_bars": 2
        })


@pytest.mark.asyncio
async def test_write_notes():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import write_notes
        notes = [{"pitch": 60, "time": 0.0, "duration": 0.25, "velocity": 100}]
        await write_notes.ainvoke({"track_index": 0, "slot_index": 0, "notes": notes})
        mock_send.assert_called_once_with("write_notes", {
            "track_index": 0, "slot_index": 0, "notes": notes
        })


@pytest.mark.asyncio
async def test_load_effect():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import load_effect
        await load_effect.ainvoke({"track_index": 0, "effect_name": "Reverb", "position": -1})
        mock_send.assert_called_once_with("load_effect", {
            "track_index": 0, "effect_name": "Reverb", "position": -1
        })


@pytest.mark.asyncio
async def test_create_scene():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"scene_index": 0}
        from app.agent.tools import create_scene
        await create_scene.ainvoke({"name": "Drop 1", "scene_index": -1})
        mock_send.assert_called_once_with("create_scene", {"name": "Drop 1", "scene_index": -1})


@pytest.mark.asyncio
async def test_write_automation():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import write_automation
        points = [{"time": 0.0, "value": 0.0}, {"time": 8.0, "value": 1.0}]
        await write_automation.ainvoke({
            "track_index": 0, "device_index": 0,
            "param_index": 1, "points": points
        })
        mock_send.assert_called_once_with("write_automation", {
            "track_index": 0, "device_index": 0,
            "param_index": 1, "points": points
        })


@pytest.mark.asyncio
async def test_all_tools_list_contains_new_tools():
    from app.agent.tools import ALL_TOOLS
    tool_names = [t.name for t in ALL_TOOLS]
    for expected in [
        "set_session", "create_instrument_track", "create_audio_track",
        "delete_track", "set_track_mix", "create_midi_clip", "write_notes",
        "set_clip_name", "load_effect", "create_scene", "write_automation",
    ]:
        assert expected in tool_names, f"Missing tool: {expected}"
    assert len(ALL_TOOLS) == 18
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python3 -m pytest tests/test_extended_tools.py -v 2>&1 | head -20
```

Expected: FAIL — tools not found

- [ ] **Step 3: Add 12 new tools to `app/agent/tools.py`**

Append the following to `backend/app/agent/tools.py` (after the existing `fire_clip` tool, before `ALL_TOOLS`):

```python
from typing import List  # add to existing imports at top of file


# ── Session ────────────────────────────────────────────────────────────────

@tool
async def set_session(bpm: float, time_signature: str = "4/4", name: str = "") -> dict:
    """Set session-level properties: tempo (BPM), time signature, and project name.

    Args:
        bpm: Tempo in beats per minute (e.g. 174 for DnB, 135 for Techno).
        time_signature: Time signature string, e.g. "4/4", "3/4", "6/8".
        name: Optional project name to set.
    """
    return await _safe_send("set_session", {"bpm": bpm, "time_signature": time_signature, "name": name})


# ── Tracks ─────────────────────────────────────────────────────────────────

@tool
async def create_instrument_track(name: str, instrument: str, color: str = "") -> dict:
    """Create a new MIDI track, load an instrument, and set name and color.

    Combines track creation + instrument loading + naming in one call.
    Compatible with Live 11 and Live 12.

    Args:
        name: Track name (e.g. "Reese Bass", "Amen Break").
        instrument: Instrument name to load, e.g. "Drift", "Operator", "Wavetable",
                    "Simpler", "Sampler", "Drum Rack".
        color: Optional color hint (e.g. "blue", "orange", "green"). Bridge maps to hex.
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
        volume: Volume level 0.0–1.0 (0.85 ≈ -3dB, good default).
        pan: Panning -1.0 (full left) to 1.0 (full right). 0.0 = center.
        mute: Whether to mute the track.
    """
    return await _safe_send("set_track_mix", {
        "track_index": track_index,
        "volume": volume,
        "pan": pan,
        "mute": mute,
    })


# ── Clips & MIDI ───────────────────────────────────────────────────────────

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

    Each note is a dict with keys:
      - pitch (int): MIDI note number 0-127. C3=48, C4=60, A4=69.
      - time (float): Start position in beats from clip start. 0.0=bar start, 0.5=8th note, 0.25=16th.
      - duration (float): Note duration in beats.
      - velocity (int): Note velocity 1-127. 64=medium, 100=strong, 127=max.
      - mute (bool, optional): Whether the note is muted (default False).

    Args:
        track_index: 0-based track index.
        slot_index: 0-based clip slot index (clip must already exist).
        notes: List of note dicts. Use music_theory.get_scale_notes() to get pitches.

    Example notes for a C minor bass line (2 bars, 4/4):
        [
            {"pitch": 48, "time": 0.0,  "duration": 0.5, "velocity": 100},
            {"pitch": 51, "time": 1.0,  "duration": 0.25, "velocity": 90},
            {"pitch": 55, "time": 2.0,  "duration": 0.5, "velocity": 100},
            {"pitch": 48, "time": 3.0,  "duration": 1.0, "velocity": 110},
        ]
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


# ── Devices & Effects ──────────────────────────────────────────────────────

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


# ── Arrangement ────────────────────────────────────────────────────────────

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


# ── Automation ─────────────────────────────────────────────────────────────

@tool
async def write_automation(
    track_index: int,
    device_index: int,
    param_index: int,
    points: List[dict],
) -> dict:
    """Write an automation envelope for a device parameter.

    Each point is a dict: {"time": <beat_position>, "value": <0.0–1.0>}.
    Points are interpolated linearly between them.

    Args:
        track_index: 0-based track index.
        device_index: 0-based device index on that track.
        param_index: 0-based parameter index on that device.
        points: List of automation points. E.g. for a filter sweep:
                [{"time": 0.0, "value": 0.1}, {"time": 8.0, "value": 0.9}]
    """
    return await _safe_send("write_automation", {
        "track_index": track_index,
        "device_index": device_index,
        "param_index": param_index,
        "points": points,
    })
```

Also update `ALL_TOOLS` at the bottom of `tools.py`:

```python
ALL_TOOLS = [
    # Original 6
    get_session_info,
    get_tracks,
    get_track_devices,
    set_parameter,
    get_clips,
    fire_clip,
    # New 12
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
    # get_device_parameters already exists as get_track_devices — reuse
]
```

**Note:** Total = 17 tools (not 18 — `get_device_parameters` maps to existing `get_track_devices`). Update the test to expect 17 if that's what you implement. Count what you actually added.

Also add `from typing import List` to the imports at the top if not already present.

- [ ] **Step 4: Run tests**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python3 -m pytest tests/test_extended_tools.py -v
```

Expected: all PASS. Fix any count mismatches in `test_all_tools_list_contains_new_tools`.

- [ ] **Step 5: Run full suite to check for regressions**

```bash
python3 -m pytest tests/ -v 2>&1 | tail -15
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add app/agent/tools.py tests/test_extended_tools.py
git commit -m "feat(agent): add 12 composite LOM tools — tracks, clips, MIDI, effects, automation"
```

---

## Chunk 3: Bridge + agent update

### Task 4: Extend `SONIQWERK_bridge.js` with new LOM actions

**Files:**
- Modify: `ableton/SONIQWERK_bridge.js`

**No automated tests** — requires a running Ableton Live instance. This task is manual testing only.

**Important LOM notes for Live 11/12 compatibility:**
- `create_midi_track -1` creates at the end
- `set_notes_extended` requires `maxApi.setDict()` + dict reference (Live 11+)
- Device loading uses friendly name → path mapping defined in the bridge
- Color codes are hex integers in LOM

- [ ] **Step 1: Add device name → LOM path mapping at top of bridge**

Add after the `RECONNECT_DELAY_MS` constant in `SONIQWERK_bridge.js`:

```javascript
// Instrument name → Live browser path mapping (Live 11 + Live 12 compatible)
const INSTRUMENT_PATHS = {
    "drift":      "Instruments/Drift/Drift.adv",
    "operator":   "Instruments/Operator/Operator.adv",
    "wavetable":  "Instruments/Wavetable/Wavetable.adv",
    "simpler":    "Instruments/Simpler/Simpler.adv",
    "sampler":    "Instruments/Sampler/Sampler.adv",
    "drum rack":  "Instruments/Drum Rack/Drum Rack.adv",
};

const EFFECT_PATHS = {
    "reverb":      "Audio Effects/Reverb/Reverb.adv",
    "delay":       "Audio Effects/Delay/Delay.adv",
    "compressor":  "Audio Effects/Compressor/Compressor.adv",
    "eq eight":    "Audio Effects/EQ Eight/EQ Eight.adv",
    "eq3":         "Audio Effects/EQ Three/EQ Three.adv",
    "auto filter": "Audio Effects/Auto Filter/Auto Filter.adv",
    "saturator":   "Audio Effects/Saturator/Saturator.adv",
    "chorus":      "Audio Effects/Chorus-Ensemble/Chorus-Ensemble.adv",
    "phaser":      "Audio Effects/Phaser-Flanger/Phaser-Flanger.adv",
    "redux":       "Audio Effects/Redux/Redux.adv",
    "limiter":     "Audio Effects/Limiter/Limiter.adv",
};

const COLOR_MAP = {
    "red": 14368691, "orange": 15631116, "yellow": 14785536,
    "green": 5537095, "blue": 4473924, "purple": 8756399,
    "pink": 12450367, "white": 16579836, "": 0,
};
```

- [ ] **Step 2: Add new action handlers in `handleCommand()`**

Add the following `else if` blocks inside `handleCommand()`, before the final `else` block:

```javascript
} else if (action === "set_session") {
    const { bpm, time_signature, name } = params;
    if (bpm) await setLom(id + "_bpm", "live_set", "tempo", bpm);
    if (time_signature) {
        const [num, den] = time_signature.split("/").map(Number);
        await setLom(id + "_num", "live_set", "signature_numerator", num);
        await setLom(id + "_den", "live_set", "signature_denominator", den);
    }
    if (name) await setLom(id + "_name", "live_set", "name", name);
    result = { success: true };

} else if (action === "create_instrument_track") {
    const { name, instrument, color } = params;
    const newIdx = await callLom(id + "_ct", "live_set", "create_midi_track -1");
    const trackIdx = await queryLom(id + "_tidx", "live_set tracks", "length");
    const idx = trackIdx[0] - 1;
    await setLom(id + "_tname", `live_set tracks ${idx}`, "name", name);
    const instrKey = (instrument || "").toLowerCase();
    const instrPath = INSTRUMENT_PATHS[instrKey];
    if (instrPath) {
        await callLom(id + "_ld", `live_set tracks ${idx}`, `load_device "${instrPath}"`);
    }
    if (color && COLOR_MAP[color.toLowerCase()] !== undefined) {
        await setLom(id + "_col", `live_set tracks ${idx}`, "color", COLOR_MAP[color.toLowerCase()]);
    }
    result = { track_index: idx };

} else if (action === "create_audio_track") {
    const { name, color } = params;
    await callLom(id + "_cat", "live_set", "create_audio_track -1");
    const trackIdx = await queryLom(id + "_atidx", "live_set tracks", "length");
    const idx = trackIdx[0] - 1;
    await setLom(id + "_atname", `live_set tracks ${idx}`, "name", name);
    result = { track_index: idx };

} else if (action === "delete_track") {
    const { track_index } = params;
    await callLom(id, `live_set tracks ${track_index}`, "delete");
    result = { success: true };

} else if (action === "set_track_mix") {
    const { track_index, volume, pan, mute } = params;
    if (volume !== undefined)
        await setLom(id + "_vol", `live_set tracks ${track_index} mixer_device volume`, "value", volume);
    if (pan !== undefined)
        await setLom(id + "_pan", `live_set tracks ${track_index} mixer_device panning`, "value", pan);
    if (mute !== undefined)
        await setLom(id + "_mute", `live_set tracks ${track_index}`, "mute", mute ? 1 : 0);
    result = { success: true };

} else if (action === "create_midi_clip") {
    const { track_index, slot_index, length_bars } = params;
    const lengthBeats = (length_bars || 2) * 4;
    await callLom(id, `live_set tracks ${track_index} clip_slots ${slot_index}`, `create_clip ${lengthBeats}`);
    result = { success: true };

} else if (action === "write_notes") {
    const { track_index, slot_index, notes } = params;
    // Format notes for set_notes_extended (Live 11+)
    const dictName = "soniqwerk_notes_" + id;
    const noteDicts = notes.map(n => ({
        pitch: n.pitch,
        start_time: n.time,
        duration: n.duration,
        velocity: n.velocity,
        mute: n.mute ? 1 : 0,
        probability: 1.0,
        velocity_deviation: 0,
        release_velocity: 64,
    }));
    await maxApi.setDict(dictName, { notes: noteDicts });
    await callLom(id, `live_set tracks ${track_index} clip_slots ${slot_index} clip`,
        `set_notes_extended ${dictName}`);
    result = { success: true, count: notes.length };

} else if (action === "set_clip_name") {
    const { track_index, slot_index, name } = params;
    await setLom(id, `live_set tracks ${track_index} clip_slots ${slot_index} clip`, "name", name);
    result = { success: true };

} else if (action === "load_effect") {
    const { track_index, effect_name, position } = params;
    const key = (effect_name || "").toLowerCase();
    const path = EFFECT_PATHS[key];
    if (!path) {
        sendError(id, `Unknown effect: ${effect_name}. Available: ${Object.keys(EFFECT_PATHS).join(", ")}`);
        return;
    }
    await callLom(id, `live_set tracks ${track_index}`, `load_device "${path}"`);
    result = { success: true };

} else if (action === "create_scene") {
    const { name, scene_index } = params;
    await callLom(id + "_cs", "live_set", `create_scene ${scene_index !== undefined ? scene_index : -1}`);
    const sceneCount = await queryLom(id + "_sc", "live_set scenes", "length");
    const idx = sceneCount[0] - 1;
    await setLom(id + "_sn", `live_set scenes ${idx}`, "name", name);
    result = { scene_index: idx };

} else if (action === "write_automation") {
    const { track_index, device_index, param_index, points } = params;
    const dictName = "soniqwerk_auto_" + id;
    await maxApi.setDict(dictName, { automation_points: points });
    await callLom(id, `live_set tracks ${track_index} devices ${device_index} parameters ${param_index}`,
        `set_automation_points ${dictName}`);
    result = { success: true };
```

- [ ] **Step 3: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add ableton/SONIQWERK_bridge.js
git commit -m "feat(bridge): add LOM handlers for track creation, MIDI notes, effects, automation"
```

---

### Task 5: Enrich `react_agent.py` system prompt

**Files:**
- Modify: `backend/app/agent/react_agent.py`
- Modify: `backend/tests/test_react_agent.py` (update tool count assertion)

- [ ] **Step 1: Replace SYSTEM_PROMPT**

In `backend/app/agent/react_agent.py`, replace the `SYSTEM_PROMPT` constant with:

```python
SYSTEM_PROMPT = """You are SONIQWERK, an expert AI music producer that controls Ableton Live via a WebSocket bridge.
You support Ableton Live 11 and Live 12. You can create complete tracks from a single prompt.

## Workflow
1. Always call get_session_info first to understand the current state.
2. For genre-based requests, apply standard arrangement structures (intro/build/drop/break/outro).
3. Create tracks in order: drums/percussion → bass → chords/pads → melody/lead → fx.
4. After creating each track, immediately create clips and write notes.
5. Name all tracks and clips descriptively (e.g. "Reese Bass", "Amen Break", "Drop 1 Pad").

## Music Theory
- Notes are MIDI numbers: C3=48, C4=60, C5=72. Each semitone = +1.
- Octave reference: C(0), D(+2), E(+4), F(+5), G(+7), A(+9), B(+11).
- Time in beats: 1 bar = 4 beats (4/4). 0.25 = 16th note, 0.5 = 8th, 1.0 = quarter.
- Scales from root C: major=[0,2,4,5,7,9,11], natural_minor=[0,2,3,5,7,8,10],
  dorian=[0,2,3,5,7,9,10], phrygian=[0,1,3,5,7,8,10].

## Arrangement by genre
- DnB (174 BPM): Intro 16 bars → Build 8 → Drop 32 → Break 16 → Build 8 → Drop 32 → Outro 8
- Techno (135 BPM): Intro 32 → Build 16 → Main 64 → Break 32 → Drop 64 → Outro 16
- House (124 BPM): Intro 16 → Verse 32 → Build 8 → Drop 32 → Break 16 → Drop 32 → Outro 16
- Trap (140 BPM): Intro 8 → Verse 16 → Hook 16 → Verse 16 → Hook 16 → Bridge 8 → Outro 8

## Mix guidelines
- Kick and bass: pan=0.0 (always centered), volume 0.85-0.92.
- Pads/chords: volume 0.60-0.70, can use subtle pan ±0.1.
- Lead/melody: volume 0.70-0.78.
- Humanize bass and melody velocity (vary ±10-15) for groove.
- Use load_effect to add: Reverb on pads, Compressor on bass, EQ Eight on all major tracks.

## Error handling
- If a tool returns an error, acknowledge it and try an alternative approach.
- If Ableton is not connected, report clearly and stop.
- Do not hallucinate track indices — always verify with get_tracks after creating tracks.

You have access to these tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
```

Also update `max_iterations` from `10` to `25` in `create_agent()` to handle complex multi-track requests.

- [ ] **Step 2: Run existing react_agent tests**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
python3 -m pytest tests/test_react_agent.py -v
```

Expected: 3/3 PASS (tests mock create_agent, not affected by prompt changes)

- [ ] **Step 3: Run full test suite**

```bash
python3 -m pytest tests/ -v 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add app/agent/react_agent.py
git commit -m "feat(agent): enrich system prompt with music theory, arrangement, mix guidelines"
```

- [ ] **Step 5: Push to public repo**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git push public phase-3-ableton:main
```
