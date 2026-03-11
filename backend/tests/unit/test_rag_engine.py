import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_collection_mock(count=10):
    """Build a mock ChromaDB collection with realistic query results."""
    mock_col = MagicMock()
    mock_col.count.return_value = count
    mock_col.query.return_value = {
        "documents": [["chunk text A", "chunk text B", "chunk text C"]],
        "metadatas": [[
            {"source": "serum.pdf", "category": "plugins", "title": "Serum Manual", "chunk_index": 0},
            {"source": "serum.pdf", "category": "plugins", "title": "Serum Manual", "chunk_index": 1},
            {"source": "serum.pdf", "category": "plugins", "title": "Serum Manual", "chunk_index": 2},
        ]],
        "distances": [[0.1, 0.3, 0.5]],   # cosine distances ∈ [0, 2]
        "embeddings": [[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]],
    }
    return mock_col


@pytest.mark.asyncio
async def test_retrieve_returns_chunks():
    mock_embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

    with patch("app.rag.engine.embed_query", mock_embed), \
         patch("app.rag.engine.get_collection", return_value=_make_collection_mock()), \
         patch("app.rag.engine.settings") as mock_settings:
        mock_settings.rag_top_k = 3
        mock_settings.rag_fetch_k = 10
        mock_settings.use_reranker = False

        from app.rag.engine import retrieve
        result = await retrieve("How to make a Reese bass?")

    assert len(result) > 0
    assert all("text" in r for r in result)
    assert all("metadata" in r for r in result)
    assert all("score" in r for r in result)


@pytest.mark.asyncio
async def test_retrieve_score_is_normalized():
    """ChromaDB cosine dist=0.1 → score=1-(0.1/2)=0.95, NOT 1-0.1=0.9."""
    mock_embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

    with patch("app.rag.engine.embed_query", mock_embed), \
         patch("app.rag.engine.get_collection", return_value=_make_collection_mock()), \
         patch("app.rag.engine.settings") as mock_settings:
        mock_settings.rag_top_k = 3
        mock_settings.rag_fetch_k = 10
        mock_settings.use_reranker = False

        from app.rag.engine import retrieve
        result = await retrieve("test query")

    # All scores must be in [0, 1]
    for chunk in result:
        assert 0.0 <= chunk["score"] <= 1.0, f"Score out of range: {chunk['score']}"

    # Top result from distance=0.1 → score=0.95 (NOT 0.9)
    scores = [r["score"] for r in result]
    assert max(scores) > 0.9  # would fail if using 1-dist formula (gives 0.9 max)


@pytest.mark.asyncio
async def test_retrieve_empty_collection_returns_empty():
    mock_embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
    mock_col = MagicMock()
    mock_col.count.return_value = 0  # empty collection

    with patch("app.rag.engine.embed_query", mock_embed), \
         patch("app.rag.engine.get_collection", return_value=mock_col), \
         patch("app.rag.engine.settings") as mock_settings:
        mock_settings.rag_top_k = 8
        mock_settings.rag_fetch_k = 30
        mock_settings.use_reranker = False

        from app.rag.engine import retrieve
        result = await retrieve("empty test")

    assert result == []


@pytest.mark.asyncio
async def test_retrieve_no_embedding_in_output():
    """The 'embedding' field should be stripped from final output."""
    mock_embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

    with patch("app.rag.engine.embed_query", mock_embed), \
         patch("app.rag.engine.get_collection", return_value=_make_collection_mock()), \
         patch("app.rag.engine.settings") as mock_settings:
        mock_settings.rag_top_k = 3
        mock_settings.rag_fetch_k = 10
        mock_settings.use_reranker = False

        from app.rag.engine import retrieve
        result = await retrieve("test")

    for chunk in result:
        assert "embedding" not in chunk


def test_cosine_similarity_unit_vectors():
    from app.rag.engine import _cosine_similarity
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert abs(_cosine_similarity(a, b) - 1.0) < 1e-6

    c = [0.0, 1.0, 0.0]
    assert abs(_cosine_similarity(a, c) - 0.0) < 1e-6
