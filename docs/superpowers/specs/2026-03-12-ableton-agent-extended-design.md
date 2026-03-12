# Ableton Live Agent — Extended Tools (C1) Design Spec

**Date:** 2026-03-12
**Sub-project:** C1 — Extended LOM tools + Music intelligence
**Status:** Approved

---

## Goal

Extend the Soniqwerk Ableton Live agent with 12 composite LOM tools and a music theory/genre knowledge layer, enabling the agent to create complete tracks from a single natural language prompt — instruments, MIDI sequences in any scale/mode, arrangement structure, mix settings, and automation.

## Architecture

**Approach:** Composite grouped tools (Option 2). Each tool performs multiple LOM operations in one agent call, reducing round-trips and keeping the agent context manageable. The music theory layer is a pure Python module (no LOM calls) that the agent uses internally to compute note data before writing to clips.

**Three new backend modules** + extensions to existing files + extended bridge JS.

---

## Module Breakdown

### `backend/app/agent/music_theory.py` *(new)*

Pure Python music theory engine. No external dependencies.

**Responsibilities:**
- All scale/mode definitions as semitone intervals
- `get_scale_notes(root: str, scale: str, octave: int) -> List[int]` → MIDI pitches
- `note_name_to_midi(note: str) -> int` (e.g. "C3" → 48, "F#4" → 66)
- `quantize_to_scale(pitches: List[int], root: str, scale: str) -> List[int]`
- `humanize_notes(notes: List[dict], velocity_range: int=10, timing_range: float=0.02) -> List[dict]`

**Supported scales:** major, natural_minor, harmonic_minor, melodic_minor, dorian, phrygian, lydian, mixolydian, locrian, pentatonic_major, pentatonic_minor, blues, diminished, whole_tone, chromatic

### `backend/app/agent/genre_templates.py` *(new)*

Genre knowledge base. Pure Python dataclasses.

**Responsibilities:**
- `GenreTemplate` dataclass: bpm_range, typical_bpm, time_signature, arrangement (list of sections with name+bars), track_types, mix_hints
- Templates for: dnb, techno, house, trap, ambient, lofi
- `get_template(genre: str) -> GenreTemplate`
- `get_arrangement_sections(genre: str, total_bars: int) -> List[Section]`

**Example DnB template:**
```python
GenreTemplate(
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
    track_types=["kick", "snare", "amen_break", "bass", "pad", "lead", "fx"],
    mix_hints={"kick": {"volume": 0.9, "pan": 0.0}, "bass": {"volume": 0.85, "pan": 0.0}},
)
```

### `backend/app/agent/tools.py` *(extended)*

Add 12 composite tools to the existing 6. Total: 18 tools.

**New tools:**

#### Session
- `set_session(bpm: float, time_signature: str = "4/4", name: str = "")` → sets tempo + signature

#### Tracks
- `create_instrument_track(name: str, instrument: str, color: str = "")` → create MIDI track + load instrument + set name/color. Returns track_index.
- `create_audio_track(name: str, color: str = "")` → create audio track. Returns track_index.
- `delete_track(track_index: int)` → delete track
- `set_track_mix(track_index: int, volume: float = 0.85, pan: float = 0.0, mute: bool = False)` → volume + pan in one call

#### Clips & MIDI
- `create_midi_clip(track_index: int, slot_index: int, length_bars: int = 2)` → create empty clip
- `write_notes(track_index: int, slot_index: int, notes: List[dict])` → write MIDI notes. Note format: `{"pitch": 60, "time": 0.0, "duration": 0.25, "velocity": 100}`. Time and duration in beats (quarter notes).
- `set_clip_name(track_index: int, slot_index: int, name: str)` → rename clip

#### Devices & Effects
- `get_device_parameters(track_index: int, device_index: int)` → list all params with current values (already exists, keep)
- `load_effect(track_index: int, effect_name: str, position: int = -1)` → load audio effect on track

#### Arrangement
- `create_scene(name: str, scene_index: int = -1)` → create named scene

#### Automation
- `write_automation(track_index: int, device_index: int, param_index: int, points: List[dict])` → write automation envelope. Point format: `{"time": 0.0, "value": 0.5}`. Time in beats.

### `backend/app/agent/react_agent.py` *(modified)*

System prompt significantly enriched with:
- Music theory awareness (scales, modes, intervals, chord progressions)
- Arrangement knowledge (section names, typical bar counts per genre)
- Mix philosophy (frequency separation, gain staging, stereo field)
- Workflow: always call `get_tracks` first to understand current state, use `music_theory` knowledge to compute notes before writing
- Note format documentation for `write_notes`
- Instructions to humanize velocity (vary 80-110 for groove, 100-127 for emphasis)
- Instruction to name all tracks and clips descriptively

### `ableton/SONIQWERK_bridge.js` *(extended)*

Add bridge handlers for new LOM actions:
- `create_midi_track` → `live_set call create_midi_track -1`
- `create_audio_track` → `live_set call create_audio_track -1`
- `delete_track` → `live_set tracks N call delete`
- `set_tempo` → `live_set set tempo <bpm>`
- `set_time_signature` → `live_set set signature_numerator N` + `set signature_denominator M`
- `load_instrument` → `live_set tracks N call load_device "<path>"`
- `load_effect` → `live_set tracks N call load_device "<path>"`
- `create_clip` → `live_set tracks N clip_slots M call create_clip <length>`
- `set_notes` → `live_set tracks N clip_slots M clip call set_notes` (with note data)
- `set_clip_name` → `live_set tracks N clip_slots M clip set name "<name>"`
- `set_track_name` → `live_set tracks N set name "<name>"`
- `set_track_color` → `live_set tracks N set color <hex>`
- `set_volume` → `live_set tracks N mixer_device volume set value <v>`
- `set_pan` → `live_set tracks N mixer_device panning set value <p>`
- `create_scene` → `live_set call create_scene -1`
- `write_automation` → `live_set tracks N devices M parameters P call set_automation_points`

---

## Example Prompt Flow

**Input:** "crée un morceau DnB avec un amen break dans un slicer, une reese bass avec Drift en C mineur à 174 BPM"

**Agent sequence:**
1. `set_session(bpm=174, time_signature="4/4")`
2. `create_instrument_track(name="Amen Break", instrument="Simpler", color="orange")` → track 0
3. `create_midi_clip(track_index=0, slot_index=0, length_bars=2)`
4. `write_notes(track_index=0, slot_index=0, notes=[drum slice trigger pattern])`
5. `create_instrument_track(name="Reese Bass", instrument="Drift", color="blue")` → track 1
6. `create_midi_clip(track_index=1, slot_index=0, length_bars=2)`
7. `write_notes(track_index=1, slot_index=0, notes=[C minor bass line, humanized])`
8. `set_track_mix(track_index=1, volume=0.82, pan=0.0)`
9. `create_scene(name="Drop 1")`

---

## Data Formats

### Note object
```python
{
    "pitch": 60,        # MIDI note number (0-127). C3=48, C4=60
    "time": 0.0,        # beat position (0.0 = bar start, 0.5 = 8th note, 0.25 = 16th)
    "duration": 0.25,   # duration in beats
    "velocity": 100,    # 0-127
    "mute": False       # optional
}
```

### Automation point object
```python
{
    "time": 0.0,    # beat position
    "value": 0.5    # normalized 0.0–1.0
}
```

---

## Testing Strategy

- `tests/test_music_theory.py` — unit tests for scale generation, note conversion, humanization
- `tests/test_genre_templates.py` — unit tests for template retrieval, section generation
- `tests/test_extended_tools.py` — mock-based tests for all 12 new tools (mock `_safe_send`)
- Bridge JS: manual testing with Ableton Live 11 and 12

---

## Constraints

- All LOM paths compatible with Live 11 and Live 12
- Device loading paths vary by Live version: agent uses friendly names ("Drift", "Simpler"), bridge maps to version-appropriate LOM path
- `set_notes` LOM format: `notes <count>\nnote <pitch> <time> <duration> <velocity> <mute>\n...\ndone`
- Python 3.9 compatible throughout (no `X | Y` union syntax, use `Optional[X]`)
- `music_theory.py` and `genre_templates.py` are pure Python — no LOM calls, usable in tests without mocking

---

## Out of Scope (future sub-projects)

- C2: `.amxd` device UI (separate sub-project)
- C3: Sample library search (separate sub-project)
- Audio recording, real-time MIDI learn
- Plugin preset management beyond parameter setting
