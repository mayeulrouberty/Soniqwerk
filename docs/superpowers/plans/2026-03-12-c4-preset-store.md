# C4 — Device Preset Store Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Save and restore complete device parameter snapshots as named JSON presets so the agent can recall any device state by name.

**Architecture:** Pure Python `preset_store.py` reads/writes JSON to `backend/data/presets/`; new bridge handler `get_device_parameters` reads all param values via LOM; four new agent tools wire it together.

**Tech Stack:** Python 3.9, LangChain `@tool`, Max for Live LOM

---

## Chunk 1: Preset store + bridge

### Task 1: `preset_store.py` + tests

**Files:**
- Create: `backend/app/agent/preset_store.py`
- Create: `backend/tests/test_preset_store.py`
- Create: `backend/data/presets/.gitkeep`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_preset_store.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
source venv/bin/activate
python3 -m pytest tests/test_preset_store.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create `backend/data/presets/.gitkeep`**

```bash
mkdir -p /Users/charlotte/Desktop/Soniqwerk/backend/data/presets
touch /Users/charlotte/Desktop/Soniqwerk/backend/data/presets/.gitkeep
```

- [ ] **Step 4: Implement `backend/app/agent/preset_store.py`**

```python
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import List

PRESETS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "presets"
)


def _sanitize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def _ensure_dir() -> str:
    path = os.path.abspath(PRESETS_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def save_preset(
    name: str,
    track_index: int,
    device_index: int,
    device_name: str,
    params: List[dict],
) -> str:
    safe_name = _sanitize_name(name)
    dirpath = _ensure_dir()
    filepath = os.path.join(dirpath, f"{safe_name}.json")
    data = {
        "name": name,
        "safe_name": safe_name,
        "device_name": device_name,
        "track_index": track_index,
        "device_index": device_index,
        "created_at": datetime.utcnow().isoformat(),
        "params": params,
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath


def load_preset(name: str) -> dict:
    safe_name = _sanitize_name(name)
    filepath = os.path.join(_ensure_dir(), f"{safe_name}.json")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Preset not found: {name!r}")
    with open(filepath) as f:
        return json.load(f)


def list_presets() -> List[dict]:
    dirpath = _ensure_dir()
    results = []
    for fname in sorted(os.listdir(dirpath)):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(dirpath, fname)) as f:
                data = json.load(f)
            results.append({
                "name": data.get("name", fname[:-5]),
                "device_name": data.get("device_name", ""),
                "created_at": data.get("created_at", ""),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def delete_preset(name: str) -> bool:
    safe_name = _sanitize_name(name)
    filepath = os.path.join(_ensure_dir(), f"{safe_name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False
```

- [ ] **Step 5: Run tests**

```bash
python3 -m pytest tests/test_preset_store.py -v
```

Expected: **11/11 PASS**

- [ ] **Step 6: Add `*.json` to `.gitignore` under presets**

Append to `/Users/charlotte/Desktop/Soniqwerk/.gitignore`:
```
# User presets (local only)
backend/data/presets/*.json
```

- [ ] **Step 7: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add backend/app/agent/preset_store.py backend/tests/test_preset_store.py \
    backend/data/presets/.gitkeep .gitignore
git commit -m "feat(agent): add preset store — save/restore device parameter snapshots"
```

---

### Task 2: Add `get_device_parameters` handler to `SONIQWERK_bridge.js`

**Files:**
- Modify: `ableton/SONIQWERK_bridge.js`

- [ ] **Step 1: Read the file, find the final `else` block of `handleCommand()`**

- [ ] **Step 2: Add before the final `else`**

```javascript
} else if (action === "get_device_parameters") {
    const { track_index, device_index } = params;
    const devicePath = `live_set tracks ${track_index} devices ${device_index}`;
    const paramCountRes = await queryLom(id + "_pc", devicePath + " parameters", "length");
    const count = parseInt(paramCountRes[0]) || 0;
    const paramList = [];
    for (let i = 0; i < count; i++) {
        const paramPath = `${devicePath} parameters ${i}`;
        const nameRes  = await queryLom(id + `_pn${i}`, paramPath, "name");
        const valRes   = await queryLom(id + `_pv${i}`, paramPath, "value");
        const minRes   = await queryLom(id + `_pm${i}`, paramPath, "min");
        const maxRes   = await queryLom(id + `_px${i}`, paramPath, "max");
        paramList.push({
            index: i,
            name:  nameRes[0],
            value: valRes[0],
            min:   minRes[0],
            max:   maxRes[0],
        });
    }
    result = { params: paramList };
```

- [ ] **Step 3: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add ableton/SONIQWERK_bridge.js
git commit -m "feat(bridge): add get_device_parameters LOM handler"
```

---

## Chunk 2: Agent tools

### Task 3: Add 4 preset tools to `tools.py`

**Files:**
- Modify: `backend/app/agent/tools.py`
- Modify: `backend/tests/test_extended_tools.py`

- [ ] **Step 1: Write failing tests — append to `backend/tests/test_extended_tools.py`**

```python
@pytest.mark.asyncio
async def test_get_device_parameters_tool():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"params": [{"index": 0, "name": "Osc", "value": 0.5, "min": 0.0, "max": 1.0}]}
        from app.agent.tools import get_device_parameters
        result = await get_device_parameters.ainvoke({"track_index": 0, "device_index": 0})
        mock_send.assert_called_once_with("get_device_parameters", {"track_index": 0, "device_index": 0})
        assert "params" in result


@pytest.mark.asyncio
async def test_save_device_preset_tool():
    params = [{"index": 0, "name": "Osc", "value": 0.5, "min": 0.0, "max": 1.0}]
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = [
            {"params": params},
            {"devices": [{"name": "Drift", "index": 0}]},
        ]
        with patch("app.agent.preset_store.save_preset", return_value="/tmp/test.json"):
            from app.agent.tools import save_device_preset
            result = await save_device_preset.ainvoke({
                "name": "Test", "track_index": 0, "device_index": 0
            })
            assert result["success"] is True


@pytest.mark.asyncio
async def test_load_device_preset_tool():
    preset_data = {
        "name": "Test",
        "params": [{"index": 0, "name": "Osc", "value": 0.5, "min": 0.0, "max": 1.0}]
    }
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        with patch("app.agent.preset_store.load_preset", return_value=preset_data):
            from app.agent.tools import load_device_preset
            result = await load_device_preset.ainvoke({
                "name": "Test", "track_index": 1, "device_index": 0
            })
            assert result["success"] is True
            assert result["params_restored"] == 1


@pytest.mark.asyncio
async def test_list_device_presets_tool():
    with patch("app.agent.preset_store.list_presets", return_value=[
        {"name": "Test", "device_name": "Drift", "created_at": "2026-03-12"}
    ]):
        from app.agent.tools import list_device_presets
        result = await list_device_presets.ainvoke({})
        assert result["count"] == 1
        assert result["presets"][0]["name"] == "Test"
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/test_extended_tools.py -k "preset or device_param" -v 2>&1 | head -15
```

- [ ] **Step 3: Add 4 tools to `backend/app/agent/tools.py`**

Append after `load_sample`, before `ALL_TOOLS`:

```python
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
```

Update `ALL_TOOLS` to include the 4 new tools (total = 23). Update `assert len(ALL_TOOLS) == 19` → `== 23` in the test.

- [ ] **Step 4: Run full suite**

```bash
python3 -m pytest tests/ -v 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 5: Commit and push**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add backend/app/agent/tools.py backend/tests/test_extended_tools.py
git commit -m "feat(agent): add get_device_parameters, save/load/list_device_presets tools"
git push public phase-3-ableton:main
```
