from __future__ import annotations

import os
from typing import List, Optional, Tuple

AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".mp3", ".flac"}


class SampleLibrary:
    def __init__(self, paths: List[str]) -> None:
        self._entries: List[Tuple[str, str]] = []
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
    global _library
    _library = None
