from __future__ import annotations

from dataclasses import dataclass
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
            "kick":  {"volume": 0.9,  "pan": 0.0},
            "bass":  {"volume": 0.8,  "pan": 0.0},
            "chord": {"volume": 0.65, "pan": 0.0},
            "lead":  {"volume": 0.72, "pan": 0.05},
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
            Section("Hook 2", 16),
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
            "pad":     {"volume": 0.7,  "pan": 0.0},
            "texture": {"volume": 0.6,  "pan": 0.1},
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

    Raises:
        ValueError: If genre is not found.
    """
    key = genre.lower().replace("-", "").replace(" ", "")
    if key not in _TEMPLATES:
        raise ValueError(f"Unknown genre: {genre!r}. Available: {list_genres()}")
    return _TEMPLATES[key]


def get_arrangement_sections(genre: str, total_bars: int = 120) -> List[Section]:
    """Return arrangement sections for a genre, scaled to total_bars if needed."""
    template = get_template(genre)
    sections = template.arrangement

    template_total = sum(s.bars for s in sections)
    if total_bars and abs(total_bars - template_total) > 8:
        ratio = total_bars / template_total
        scaled = [Section(s.name, max(4, round(s.bars * ratio))) for s in sections]
        return scaled

    return list(sections)
