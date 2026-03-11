from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from app.config import settings

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts using OpenAI text-embedding-3-large.

    Returns a list of embedding vectors (one per input text).
    Batches requests if necessary (OpenAI limit: 2048 texts per call).
    """
    if not texts:
        return []

    client = _get_client()
    # OpenAI allows up to 2048 inputs per embeddings call
    batch_size = 512
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
        )
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


async def embed_query(text: str) -> list[float]:
    """Embed a single query string. Returns one embedding vector."""
    results = await embed_texts([text])
    return results[0]
