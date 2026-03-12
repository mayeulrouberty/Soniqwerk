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
                  "pentatonic_major", "pentatonic_minor", "blues",
                  "diminished", "whole_tone", "chromatic"]:
        assert scale in SCALES, f"Missing scale: {scale}"


def test_quantize_to_scale_already_in_scale():
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
