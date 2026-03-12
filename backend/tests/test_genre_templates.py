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
