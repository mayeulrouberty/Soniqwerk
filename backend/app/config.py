from __future__ import annotations
from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Providers
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_embedding_model: str = Field("text-embedding-3-large")
    anthropic_api_key: str = Field("", description="Anthropic API key (optional)")

    # Auth
    api_secret_key: str = Field(default="", description="Shared API key for X-API-Key header")

    # Database
    database_url: str = Field(
        "postgresql+asyncpg://soniqwerk:soniqwerk@localhost:5432/soniqwerk"
    )

    # Redis
    redis_url: str = Field("redis://localhost:6379/0")

    # Celery
    celery_broker_url: str = Field("redis://localhost:6379/1")
    celery_result_backend: str = Field("redis://localhost:6379/2")

    # ChromaDB
    chroma_persist_dir: str = Field("./data/chroma_db")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )

    # LLM Routing
    llm_provider: str = Field("multi")
    ollama_model: str = Field("llama3.2:8b")

    # RAG
    rag_top_k: int = Field(8)
    rag_fetch_k: int = Field(30)
    use_reranker: bool = Field(True)

    # Ableton (Phase 2)
    ableton_ws_port: int = Field(8001)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
