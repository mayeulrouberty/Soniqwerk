from __future__ import annotations
import chromadb
from functools import lru_cache
from app.config import settings

VALID_COLLECTIONS = {"manuals", "plugins", "books", "articles"}


@lru_cache(maxsize=1)
def _get_client() -> chromadb.ClientAPI:
    """Embedded PersistentClient — persisted locally, no network overhead."""
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


def get_collection(category: str) -> chromadb.Collection:
    """Get or create a ChromaDB collection for the given category.

    Uses cosine distance metric. ChromaDB cosine distance ∈ [0, 2].
    Similarity score = 1 − (distance / 2) → always in [0, 1].
    """
    if category not in VALID_COLLECTIONS:
        raise ValueError(f"Invalid category '{category}'. Valid: {sorted(VALID_COLLECTIONS)}")

    client = _get_client()
    return client.get_or_create_collection(
        name=f"soniqwerk_{category}",
        metadata={"hnsw:space": "cosine"},
    )
