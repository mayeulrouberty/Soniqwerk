import os
import pytest
from app.agent.sample_library import SampleLibrary


def make_audio_files(tmp_path, names):
    for name in names:
        (tmp_path / name).touch()
    return str(tmp_path)


def test_search_finds_exact_match(tmp_path):
    path = make_audio_files(tmp_path, ["kick_01.wav", "snare_01.wav", "hihat.wav"])
    lib = SampleLibrary([path])
    results = lib.search("kick")
    assert len(results) == 1
    assert results[0]["name"] == "kick_01.wav"


def test_search_is_case_insensitive(tmp_path):
    path = make_audio_files(tmp_path, ["Kick_Heavy.wav"])
    lib = SampleLibrary([path])
    assert len(lib.search("kick")) == 1


def test_search_returns_empty_on_no_match(tmp_path):
    path = make_audio_files(tmp_path, ["kick.wav"])
    lib = SampleLibrary([path])
    assert lib.search("amen") == []


def test_search_respects_limit(tmp_path):
    names = [f"kick_{i:02d}.wav" for i in range(20)]
    path = make_audio_files(tmp_path, names)
    lib = SampleLibrary([path])
    assert len(lib.search("kick", limit=5)) == 5


def test_non_audio_files_excluded(tmp_path):
    path = make_audio_files(tmp_path, ["kick.wav", "README.txt", "image.png"])
    lib = SampleLibrary([path])
    names = [r["name"] for r in lib.search("", limit=100)]
    assert "README.txt" not in names
    assert "image.png" not in names


def test_missing_directory_skipped():
    lib = SampleLibrary(["/nonexistent/path/xyz_abc"])
    assert lib.search("kick") == []


def test_multiple_paths(tmp_path):
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    (dir1 / "kick.wav").touch()
    (dir2 / "snare.wav").touch()
    lib = SampleLibrary([str(dir1), str(dir2)])
    assert len(lib.search("kick")) == 1
    assert len(lib.search("snare")) == 1


def test_supports_multiple_extensions(tmp_path):
    path = make_audio_files(tmp_path, ["a.aif", "b.flac", "c.aiff", "d.mp3"])
    lib = SampleLibrary([path])
    assert len(lib.search("", limit=100)) == 4
