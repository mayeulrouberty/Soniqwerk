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
