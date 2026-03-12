import pytest
import app.agent.preset_store as ps_module
from app.agent.preset_store import (
    save_preset,
    load_preset,
    list_presets,
    delete_preset,
    _sanitize_name,
)

SAMPLE_PARAMS = [
    {"index": 0, "name": "Osc Type", "value": 0.5, "min": 0.0, "max": 1.0},
    {"index": 1, "name": "Filter Cutoff", "value": 0.8, "min": 0.0, "max": 1.0},
]


@pytest.fixture(autouse=True)
def tmp_presets(tmp_path, monkeypatch):
    monkeypatch.setattr(ps_module, "PRESETS_DIR", str(tmp_path))


def test_save_and_load():
    save_preset("My Drift Bass", 1, 0, "Drift", SAMPLE_PARAMS)
    data = load_preset("My Drift Bass")
    assert data["name"] == "My Drift Bass"
    assert data["device_name"] == "Drift"
    assert len(data["params"]) == 2
    assert data["params"][0]["value"] == 0.5


def test_load_not_found_raises():
    with pytest.raises(FileNotFoundError):
        load_preset("ghost preset")


def test_list_presets_sorted(tmp_path, monkeypatch):
    monkeypatch.setattr(ps_module, "PRESETS_DIR", str(tmp_path))
    save_preset("Zebra Pad", 0, 0, "Wavetable", SAMPLE_PARAMS)
    save_preset("Alpha Bass", 0, 0, "Drift", SAMPLE_PARAMS)
    result = list_presets()
    names = [r["name"] for r in result]
    assert names.index("Alpha Bass") < names.index("Zebra Pad")


def test_list_presets_empty():
    assert list_presets() == []


def test_delete_existing():
    save_preset("Temp", 0, 0, "Operator", SAMPLE_PARAMS)
    assert delete_preset("Temp") is True
    with pytest.raises(FileNotFoundError):
        load_preset("Temp")


def test_delete_missing():
    assert delete_preset("does not exist") is False


def test_sanitize_name_spaces():
    assert _sanitize_name("My Drift Bass") == "my_drift_bass"


def test_sanitize_name_special_chars():
    assert _sanitize_name("Bass! V2 #1") == "bass_v2_1"


def test_sanitize_name_strips():
    assert _sanitize_name("  spaces  ") == "spaces"


def test_preset_contains_metadata():
    save_preset("Meta Test", 2, 1, "Reverb", SAMPLE_PARAMS)
    data = load_preset("Meta Test")
    assert "created_at" in data
    assert data["track_index"] == 2
    assert data["device_index"] == 1
