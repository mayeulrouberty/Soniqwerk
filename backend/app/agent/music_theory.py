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
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
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
    """Return MIDI pitch numbers for a scale starting at root in given octave."""
    if scale not in SCALES:
        raise ValueError(f"Unknown scale: {scale!r}. Available: {list(SCALES)}")

    root_midi = note_name_to_midi(f"{root}{octave}")
    intervals = SCALES[scale]
    return [root_midi + interval for interval in intervals]


def quantize_to_scale(pitches: List[int], root: str, scale: str) -> List[int]:
    """Snap each pitch to the nearest note in the given scale (any octave)."""
    root_semitone = _NOTE_NAMES.index(_NOTE_ALIASES.get(root, root))
    intervals = set(i % 12 for i in SCALES[scale])

    result = []
    for pitch in pitches:
        semitone = (pitch - root_semitone) % 12
        if semitone in intervals:
            result.append(pitch)
        else:
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
    """Add subtle velocity and timing variations to a list of note dicts."""
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
