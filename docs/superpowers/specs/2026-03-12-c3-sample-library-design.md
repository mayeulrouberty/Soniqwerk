# C3 — Sample Library Design Spec

**Date:** 2026-03-12
**Sub-project:** C3 — Local sample indexing + agent search + auto-load
**Status:** Approved

---

## Goal

Let the Soniqwerk agent find and load local audio samples into Ableton Live. The user configures sample folder paths via `SAMPLE_PATHS` in `backend/.env`. The agent can search by filename/keyword and load the result into a Simpler or Drum Rack slot on a given track.

## Architecture

### `backend/app/agent/sample_library.py` *(new)*

Pure Python. No LOM calls. Scans configured folders at startup, builds an in-memory index.

**Responsibilities:**
- `_build_index(paths: List[str]) -> Dict[str, str]` — scans recursively for audio files (`.wav`, `.aif`, `.aiff`, `.mp3`, `.flac`), returns `{filename_lower_no_ext: full_path}`
- `search(query: str, limit: int = 10) -> List[dict]` — case-insensitive substring match on filename. Returns list of `{"name": filename, "path": full_path}` sorted by relevance (exact match first, then partial).
- `SampleLibrary` class: initialized with `paths: List[str]`, exposes `search()`, `get_by_path(path)`.
- Module-level singleton: `_library: Optional[SampleLibrary] = None` + `get_library() -> SampleLibrary` (lazy-init from settings).

**Supported audio extensions:** `.wav`, `.aif`, `.aiff`, `.mp3`, `.flac`

**Index size:** No limit enforced. Typical user library: <50k files, fits in memory.

### `backend/app/config.py` *(modified)*

Add setting:
```python
sample_paths: str = ""  # Colon-separated list of absolute folder paths
```

Add property:
```python
@property
def sample_path_list(self) -> List[str]:
    return [p.strip() for p in self.sample_paths.split(":") if p.strip()]
```

### `backend/.env.example` *(modified)*

Add:
```
# Sample library — colon-separated folder paths to scan for audio files
SAMPLE_PATHS=
```

### `backend/app/agent/tools.py` *(modified)*

Add 2 new tools (total 19):

```python
@tool
async def search_samples(query: str, limit: int = 10) -> dict:
    """Search the local sample library by filename keyword.
    Returns a list of matching samples with their full paths.
    Use load_sample to load a result into a track.
    Args:
        query: Search keyword, e.g. "kick", "snare", "amen", "bass 808"
        limit: Max results to return (default 10)
    """

@tool
async def load_sample(track_index: int, sample_path: str) -> dict:
    """Load a sample file into the instrument on a track (Simpler or Sampler).
    The track must already have a Simpler or Sampler device loaded.
    Args:
        track_index: 0-based track index
        sample_path: Absolute path to the audio file (from search_samples results)
    """
```

`search_samples` calls `get_library().search(query, limit)` directly (no LOM call needed).
`load_sample` calls `_safe_send("load_sample", {"track_index": track_index, "sample_path": sample_path})`.

### `ableton/SONIQWERK_bridge.js` *(modified)*

Add handler:
```javascript
} else if (action === "load_sample") {
    const { track_index, sample_path } = params;
    await callLom(id, `live_set tracks ${track_index} devices 0`,
        `load_sample "${sample_path}"`);
    result = { success: true };
```

**LOM note:** `Device.load_sample(path)` works on Simpler and Sampler in Live 11+. The path must be an absolute filesystem path.

### `backend/tests/test_sample_library.py` *(new)*

Unit tests using a temporary directory with dummy audio files (`.wav` touch files). Tests:
- Index builds correctly from paths
- Search returns exact match first
- Search is case-insensitive
- Search returns empty list when no match
- Search respects limit
- Non-audio files are excluded
- Missing directories are skipped gracefully

---

## Data Flow

```
Agent: search_samples("amen break")
  → SampleLibrary.search("amen break", 10)
  → returns [{"name": "amen_break_170.wav", "path": "/Users/.../amen_break_170.wav"}, ...]

Agent: load_sample(track_index=0, sample_path="/Users/.../amen_break_170.wav")
  → _safe_send("load_sample", {...})
  → bridge: live_set tracks 0 devices 0 load_sample "/path/to/file.wav"
  → Simpler loads the sample
```

---

## Constraints

- Python 3.9 compatible
- `search_samples` does NOT call LOM — pure Python index search
- `load_sample` requires the target track to already have Simpler or Sampler loaded
- Paths must be absolute (no `~/` expansion needed — user provides absolute paths in `.env`)
- Index is built once at first `search_samples` call (lazy init), not at startup

---

## Testing

- `tests/test_sample_library.py` — pure unit tests, no LOM, no mocking of `_safe_send` for search
- `test_extended_tools.py` — add 2 mock-based tests for the new tools

---

## Out of Scope

- Drum Rack pad targeting (C3.1 — future)
- Audio preview playback
- AI-powered semantic search (filename match only for now)
- Sample metadata (BPM detection, key detection)
