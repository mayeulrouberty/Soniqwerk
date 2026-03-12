# C4 — Device Preset Store Design Spec

**Date:** 2026-03-12
**Sub-project:** C4 — Save/restore device parameter snapshots
**Status:** Approved

---

## Goal

Let the Soniqwerk agent save and restore the complete parameter state of any Ableton device as a named JSON preset. Works with any device — native Live instruments/effects or VSTs. Presets are stored locally in `backend/data/presets/`.

## Architecture

### `backend/app/agent/preset_store.py` *(new)*

Pure Python. Reads/writes JSON files. No LOM calls.

**Responsibilities:**
- `save_preset(name: str, track_index: int, device_index: int, params: List[dict]) -> str` — writes `backend/data/presets/{name}.json` with metadata + param snapshot. Returns file path.
- `load_preset(name: str) -> dict` — reads and returns preset JSON. Raises `FileNotFoundError` if missing.
- `list_presets() -> List[dict]` — scans `backend/data/presets/`, returns list of `{"name", "device_name", "created_at"}` sorted by name.
- `delete_preset(name: str) -> bool` — deletes preset file. Returns True if existed.
- Preset JSON format:
  ```json
  {
    "name": "My Drift Bass",
    "device_name": "Drift",
    "track_index": 1,
    "device_index": 0,
    "created_at": "2026-03-12T14:30:00",
    "params": [
      {"index": 0, "name": "Oscillator Type", "value": 0.5},
      ...
    ]
  }
  ```
- Storage directory: `backend/data/presets/` — created automatically if missing.
- Name sanitization: spaces → underscores, lowercase, alphanumeric + underscores only.

### `backend/app/agent/tools.py` *(modified)*

Add 3 new tools (total 22) + 1 extended bridge tool:

```python
@tool
async def get_device_parameters(track_index: int, device_index: int) -> dict:
    """Get all parameters of a device with their current values.
    Returns list of {index, name, value, min, max} dicts.
    Args:
        track_index: 0-based track index
        device_index: 0-based device index on that track
    """

@tool
async def save_device_preset(name: str, track_index: int, device_index: int) -> dict:
    """Save the current state of a device as a named preset.
    Reads all parameters, writes to backend/data/presets/{name}.json.
    Args:
        name: Preset name, e.g. "Reese Bass V1", "Dark Pad"
        track_index: 0-based track index
        device_index: 0-based device index on that track
    """

@tool
async def load_device_preset(name: str, track_index: int, device_index: int) -> dict:
    """Restore a previously saved preset to a device.
    Reads the preset JSON and applies each parameter value via set_parameter.
    Args:
        name: Preset name (from list_device_presets)
        track_index: 0-based track index to apply to
        device_index: 0-based device index to apply to
    """

@tool
async def list_device_presets() -> dict:
    """List all saved device presets.
    Returns list of {name, device_name, created_at} dicts.
    """
```

**`save_device_preset` flow:**
1. Call `_safe_send("get_device_parameters", {track_index, device_index})`
2. Pass result to `preset_store.save_preset(name, track_index, device_index, params)`
3. Return `{"success": True, "path": path}`

**`load_device_preset` flow:**
1. Call `preset_store.load_preset(name)` → get params list
2. For each param: call `_safe_send("set_parameter", {track_index, device_index, param_index, value})`
3. Return `{"success": True, "params_restored": count}`

### `ableton/SONIQWERK_bridge.js` *(modified)*

Add handler for `get_device_parameters`:
```javascript
} else if (action === "get_device_parameters") {
    const { track_index, device_index } = params;
    const device = `live_set tracks ${track_index} devices ${device_index}`;
    const paramCount = await queryLom(id + "_pc", device + " parameters", "length");
    const count = paramCount[0];
    const paramList = [];
    for (let i = 0; i < count; i++) {
        const paramPath = `${device} parameters ${i}`;
        const nameRes = await queryLom(id + "_pn" + i, paramPath, "name");
        const valRes = await queryLom(id + "_pv" + i, paramPath, "value");
        const minRes = await queryLom(id + "_pm" + i, paramPath, "min");
        const maxRes = await queryLom(id + "_px" + i, paramPath, "max");
        paramList.push({
            index: i,
            name: nameRes[0],
            value: valRes[0],
            min: minRes[0],
            max: maxRes[0],
        });
    }
    result = { params: paramList };
```

### `backend/data/presets/` *(new directory)*

Created automatically by `preset_store.py`. Add `.gitkeep` to track in git, add `*.json` to `.gitignore` (user presets are local, not committed).

### `backend/tests/test_preset_store.py` *(new)*

Unit tests using a `tmp_path` fixture (pytest). Tests:
- `save_preset` creates JSON file with correct structure
- `load_preset` returns correct data
- `load_preset` raises `FileNotFoundError` for unknown preset
- `list_presets` returns sorted list
- `delete_preset` removes file, returns True
- `delete_preset` returns False for missing preset
- Name sanitization (spaces, special chars)

---

## Data Flow

```
Agent: save_device_preset("Reese Bass V1", track_index=1, device_index=0)
  → get_device_parameters(1, 0) via bridge
  → bridge: queries all N parameters via LOM
  → returns [{index, name, value, min, max}, ...]
  → preset_store.save_preset("reese_bass_v1", 1, 0, params)
  → writes backend/data/presets/reese_bass_v1.json

Agent: load_device_preset("Reese Bass V1", track_index=2, device_index=0)
  → preset_store.load_preset("reese_bass_v1") → params list
  → for each param: set_parameter(2, 0, param.index, param.value)
  → all parameters restored
```

---

## Constraints

- Python 3.9 compatible
- `preset_store.py` is pure Python — no LOM, no LangChain dependencies
- `get_device_parameters` bridge handler loops per-parameter — may be slow for devices with many params (100+). Acceptable for now.
- Preset names are sanitized to safe filenames (no path traversal)
- `backend/data/presets/*.json` added to `.gitignore`

---

## Testing

- `tests/test_preset_store.py` — pure unit tests with `tmp_path`
- `tests/test_extended_tools.py` — add mock-based tests for 4 new tools
- Bridge handler: manual testing with Ableton Live

---

## Out of Scope

- Preset sharing / export
- Cloud sync
- Per-project preset namespacing
- Undo/redo for preset load
