from app.config import Settings


def test_settings_loads_required_fields():
    s = Settings(
        openai_api_key="test-key",
        api_secret_key="test-secret",
        database_url="postgresql+asyncpg://test:test@localhost/test",
    )
    assert s.openai_api_key == "test-key"
    assert s.api_secret_key == "test-secret"
    assert s.rag_top_k == 8
    assert s.rag_fetch_k == 30
    assert s.use_reranker is True
    assert s.openai_embedding_model == "text-embedding-3-large"


def test_settings_defaults():
    s = Settings(
        openai_api_key="k",
        api_secret_key="s",
        database_url="postgresql+asyncpg://test:test@localhost/test",
    )
    assert s.rag_top_k == 8
    assert s.llm_provider == "multi"
    assert s.ollama_model == "llama3.2:8b"
    assert s.chroma_persist_dir == "./data/chroma_db"
    assert "http://localhost:5173" in s.cors_origins


def test_cors_origins_is_list():
    s = Settings(
        openai_api_key="k",
        api_secret_key="s",
        database_url="postgresql+asyncpg://test:test@localhost/test",
    )
    assert isinstance(s.cors_origins, list)
    assert len(s.cors_origins) >= 1
