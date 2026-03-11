import pytest
from unittest.mock import patch, MagicMock


def test_get_collection_returns_collection_for_valid_category():
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    with patch("app.rag.collections._get_client", return_value=mock_client):
        from app.rag.collections import get_collection
        # Clear lru_cache to ensure fresh import
        from app.rag import collections as col_module
        col_module._get_client.cache_clear()

        result = get_collection("manuals")
        mock_client.get_or_create_collection.assert_called_once_with(
            name="soniqwerk_manuals",
            metadata={"hnsw:space": "cosine"},
        )


def test_get_collection_raises_for_invalid_category():
    from app.rag.collections import get_collection
    with pytest.raises(ValueError, match="Invalid category"):
        get_collection("invalid_cat")


def test_valid_collections_set():
    from app.rag.collections import VALID_COLLECTIONS
    assert "manuals" in VALID_COLLECTIONS
    assert "plugins" in VALID_COLLECTIONS
    assert "books" in VALID_COLLECTIONS
    assert "articles" in VALID_COLLECTIONS
    assert len(VALID_COLLECTIONS) == 4
