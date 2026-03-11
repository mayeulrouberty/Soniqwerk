import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_embed_texts_returns_list_of_vectors():
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1, 0.2, 0.3]),
        MagicMock(embedding=[0.4, 0.5, 0.6]),
    ]

    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    with patch("app.rag.embeddings._get_client", return_value=mock_client):
        from app.rag.embeddings import embed_texts
        result = await embed_texts(["text one", "text two"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.4, 0.5, 0.6]


@pytest.mark.asyncio
async def test_embed_texts_empty_returns_empty():
    from app.rag.embeddings import embed_texts
    result = await embed_texts([])
    assert result == []


@pytest.mark.asyncio
async def test_embed_query_returns_single_vector():
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]

    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    with patch("app.rag.embeddings._get_client", return_value=mock_client):
        from app.rag.embeddings import embed_query
        result = await embed_query("single query")

    assert result == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_embed_texts_uses_correct_model():
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1])]
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    with patch("app.rag.embeddings._get_client", return_value=mock_client):
        from app.rag.embeddings import embed_texts
        await embed_texts(["test"])

    call_kwargs = mock_client.embeddings.create.call_args
    assert call_kwargs.kwargs["model"] == "text-embedding-3-large"
