# C3 — Sample Library Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local sample library search + auto-load system so the Soniqwerk agent can find and load audio samples into Ableton.

**Architecture:** Pure Python `SampleLibrary` class indexes configured folders at lazy-init; two new LangChain tools (`search_samples`, `load_sample`); one new bridge action (`load_sample`).

**Tech Stack:** Python 3.9, LangChain `@tool`, Max for Live LOM

---

## Chunk 1: SampleLibrary + config

### Task 1: `sample_library.py` + tests

**Files:**
- Create: `backend/app/agent/sample_library.py`
- Create: `backend/tests/test_sample_library.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sample_library.py`:

```python
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
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
source venv/bin/activate
python3 -m pytest tests/test_sample_library.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'app.agent.sample_library'`

- [ ] **Step 3: Implement `backend/app/agent/sample_library.py`**

```python
from __future__ import annotations

import os
from typing import List, Optional, Tuple

AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".mp3", ".flac"}


class SampleLibrary:
    def __init__(self, paths: List[str]) -> None:
        self._entries: List[Tuple[str, str]] = []  # (full_path, filename)
        self._build_index(paths)

    def _build_index(self, paths: List[str]) -> None:
        for root_path in paths:
            if not os.path.isdir(root_path):
                continue
            for dirpath, _, filenames in os.walk(root_path):
                for fname in filenames:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in AUDIO_EXTENSIONS:
                        self._entries.append((os.path.join(dirpath, fname), fname))

    def search(self, query: str, limit: int = 10) -> List[dict]:
        q = query.lower()
        results: List[Tuple[int, dict]] = []
        for full_path, fname in self._entries:
            name_lower = fname.lower()
            if not q or q in name_lower:
                score = 0 if name_lower.startswith(q) else 1
                results.append((score, {"name": fname, "path": full_path}))
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results[:limit]]


_library: Optional[SampleLibrary] = None


def get_library() -> SampleLibrary:
    global _library
    if _library is None:
        from app.config import settings
        _library = SampleLibrary(settings.sample_path_list)
    return _library


def reset_library() -> None:
    """Reset singleton — used in tests."""
    global _library
    _library = None
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_sample_library.py -v
```

Expected: **8/8 PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add backend/app/agent/sample_library.py backend/tests/test_sample_library.py
git commit -m "feat(agent): add SampleLibrary — local audio file indexer with keyword search"
```

---

### Task 2: Update `config.py` + `.env.example`

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Read `backend/app/config.py` first, then add `sample_paths` setting**

In the `Settings` class, add:

```python
sample_paths: str = ""

@property
def sample_path_list(self) -> List[str]:
    return [p.strip() for p in self.sample_paths.split(":") if p.strip()]
```

Make sure `List` is imported from `typing` at the top. If it's not, add it.

- [ ] **Step 2: Add to `backend/.env.example`**

Append:
```
# Sample library — colon-separated absolute folder paths to scan for audio files
# Example: SAMPLE_PATHS=/Users/you/Samples:/Users/you/Music/Ableton/User Library/Samples
SAMPLE_PATHS=
```

- [ ] **Step 3: Verify the setting loads**

```bash
cd /Users/charlotte/Desktop/Soniqwerk/backend
source venv/bin/activate
python3 -c "from app.config import settings; print(settings.sample_path_list)"
```

Expected: `[]`

- [ ] **Step 4: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add backend/app/config.py backend/.env.example
git commit -m "feat(config): add SAMPLE_PATHS setting for local sample library"
```

---

## Chunk 2: Tools + bridge

### Task 3: Add `search_samples` + `load_sample` tools

**Files:**
- Modify: `backend/app/agent/tools.py`
- Modify: `backend/tests/test_extended_tools.py`

- [ ] **Step 1: Write failing tests — append to `backend/tests/test_extended_tools.py`**

```python
@pytest.mark.asyncio
async def test_search_samples_tool():
    with patch("app.agent.sample_library.get_library") as mock_lib:
        mock_lib.return_value.search.return_value = [
            {"name": "kick.wav", "path": "/samples/kick.wav"}
        ]
        from app.agent.tools import search_samples
        result = await search_samples.ainvoke({"query": "kick", "limit": 10})
        assert result["count"] == 1
        assert result["samples"][0]["name"] == "kick.wav"


@pytest.mark.asyncio
async def test_load_sample_tool():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import load_sample
        await load_sample.ainvoke({"track_index": 0, "sample_path": "/samples/kick.wav"})
        mock_send.assert_called_once_with("load_sample", {
            "track_index": 0, "sample_path": "/samples/kick.wav"
        })
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/test_extended_tools.py::test_search_samples_tool tests/test_extended_tools.py::test_load_sample_tool -v 2>&1 | head -15
```

Expected: `ImportError` or `AttributeError`

- [ ] **Step 3: Add tools to `backend/app/agent/tools.py`**

Append after `write_automation` tool, before `ALL_TOOLS`:

```python
# ── Sample library ────────────────────────────────────────────────────────────

@tool
async def search_samples(query: str, limit: int = 10) -> dict:
    """Search the local sample library by filename keyword.

    Returns a list of matching samples with their full file paths.
    Use load_sample() to load a result into a track's Simpler or Sampler device.

    Args:
        query: Search keyword, e.g. "kick", "snare 909", "amen break", "bass 808"
        limit: Maximum results to return (default 10)
    """
    from app.agent.sample_library import get_library
    results = get_library().search(query, limit)
    return {"samples": results, "count": len(results)}


@tool
async def load_sample(track_index: int, sample_path: str) -> dict:
    """Load a sample file into the instrument on a track (Simpler or Sampler).

    The track must already have a Simpler or Sampler device loaded.
    Get sample_path from search_samples() results.

    Args:
        track_index: 0-based track index
        sample_path: Absolute path to the audio file (from search_samples results)
    """
    return await _safe_send("load_sample", {
        "track_index": track_index,
        "sample_path": sample_path,
    })
```

Update `ALL_TOOLS` to add `search_samples, load_sample` at the end (total = 19).

- [ ] **Step 4: Update the length assertion in `test_extended_tools.py`**

Change `assert len(ALL_TOOLS) == 17` to `assert len(ALL_TOOLS) == 19`.

- [ ] **Step 5: Run all tests**

```bash
python3 -m pytest tests/ -v 2>&1 | tail -10
```

Expected: all pass (119+ tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add backend/app/agent/tools.py backend/tests/test_extended_tools.py
git commit -m "feat(agent): add search_samples and load_sample tools"
```

---

### Task 4: Add `load_sample` handler to `SONIQWERK_bridge.js`

**Files:**
- Modify: `ableton/SONIQWERK_bridge.js`

- [ ] **Step 1: Read the file, find the final `else` block of `handleCommand()`**

- [ ] **Step 2: Add before the final `else`**

```javascript
} else if (action === "load_sample") {
    const { track_index, sample_path } = params;
    await callLom(id, `live_set tracks ${track_index} devices 0`,
        `load_sample "${sample_path}"`);
    result = { success: true };
```

- [ ] **Step 3: Commit and push**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add ableton/SONIQWERK_bridge.js
git commit -m "feat(bridge): add load_sample LOM handler for Simpler/Sampler"
git push public phase-3-ableton:main
```
