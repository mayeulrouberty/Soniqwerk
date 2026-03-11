# SONIQWERK Phase 1 — Backend RAG Core Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI backend with full RAG pipeline — ChromaDB vector store, async PDF ingestion via Celery, MMR + cross-encoder retrieval, multi-LLM router (GPT-4o / Claude Sonnet 4.6 / GPT-4o-mini), and a `/v1/chat` SSE streaming endpoint.

**Architecture:** FastAPI (stateless, port 8000) + Celery worker (async ingestion) as separate processes. PostgreSQL for conversation history and document metadata. Redis (DB 0-3) for cache, Celery broker/backend, and conversation memory. ChromaDB (embedded, persisted locally) for vectors. LLM routing via regex classifier.

**Tech Stack:** Python 3.11, FastAPI 0.111, Pydantic v2 + pydantic-settings, SQLAlchemy 2.0 async + asyncpg + Alembic, ChromaDB 0.5, LangChain 0.2, sentence-transformers (cross-encoder reranker), Celery 5, Redis 7, OpenAI SDK 1.33, Anthropic SDK 0.28, pytest + pytest-asyncio + httpx.

---

## Chunk 1: Project Foundation

### Task 1: Docker services + requirements + env

**Files:**
- Create: `backend/docker-compose.yml`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`

- [ ] **Step 1.1: Create `backend/docker-compose.yml`**

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: soniqwerk
      POSTGRES_PASSWORD: soniqwerk
      POSTGRES_DB: soniqwerk
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U soniqwerk"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

Note: ChromaDB runs **embedded** (local persist dir), not as a separate service in dev. This avoids network overhead and simplifies setup.

- [ ] **Step 1.2: Create `backend/requirements.txt`**

```
# API
fastapi==0.111.0
uvicorn[standard]==0.30.1
pydantic==2.7.1
pydantic-settings==2.3.1
python-multipart==0.0.9

# Database
sqlalchemy==2.0.30
asyncpg==0.29.0
alembic==1.13.1
psycopg2-binary==2.9.9

# RAG / Vector
chromadb==0.5.0
langchain==0.2.5
langchain-openai==0.1.8
langchain-anthropic==0.1.15
langchain-community==0.2.5
openai==1.33.0
anthropic==0.28.1
sentence-transformers==3.0.1
pypdf==4.2.0

# Workers
celery==5.4.0
redis==5.0.4

# Testing
pytest==8.2.2
pytest-asyncio==0.23.7
pytest-mock==3.14.0
httpx==0.27.0
pytest-cov==5.0.0
anyio==4.4.0
fpdf2==2.7.9

# Utils
python-dotenv==1.0.1
structlog==24.2.0
aiofiles==23.2.1
```

- [ ] **Step 1.3: Create `backend/.env.example`**

```bash
# LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=multi

# Auth
API_SECRET_KEY=change-me-in-production

# Database
DATABASE_URL=postgresql+asyncpg://soniqwerk:soniqwerk@localhost:5432/soniqwerk
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ChromaDB (embedded, local dir)
CHROMA_PERSIST_DIR=./data/chroma_db

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# RAG
RAG_TOP_K=8
RAG_FETCH_K=30
USE_RERANKER=true
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Ollama (fallback, offline)
OLLAMA_MODEL=llama3.2:8b
OLLAMA_BASE_URL=http://localhost:11434

# Ableton (Phase 2)
ABLETON_WS_PORT=8001
ABLETON_BRIDGE_ENABLED=false
```

- [ ] **Step 1.4: Create virtualenv + install**

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with real OPENAI_API_KEY, ANTHROPIC_API_KEY, API_SECRET_KEY
```

- [ ] **Step 1.5: Start Docker services + verify health**

```bash
docker-compose up -d
# Wait for healthchecks to pass (up to 30s)
sleep 5 && docker-compose ps
# Expected: postgres and redis both "Up (healthy)"

# Verify connectivity explicitly
docker-compose exec postgres pg_isready -U soniqwerk
# Expected: /var/run/postgresql:5432 - accepting connections
docker-compose exec redis redis-cli ping
# Expected: PONG
```

- [ ] **Step 1.6: Create directory structure**

```bash
mkdir -p app/api/v1 app/rag app/ingestion app/llm app/db \
         workers tests/unit tests/integration tests/fixtures \
         data/documents/manuals data/documents/plugins_effects \
         data/documents/plugins_synths data/documents/books \
         data/documents/articles data/chroma_db scripts

touch app/__init__.py app/api/__init__.py app/api/v1/__init__.py \
      app/rag/__init__.py app/ingestion/__init__.py app/llm/__init__.py \
      app/db/__init__.py workers/__init__.py tests/__init__.py \
      tests/unit/__init__.py tests/integration/__init__.py
```

- [ ] **Step 1.7: Commit**

```bash
git add .
git commit -m "feat: project foundation — docker-compose, requirements, directory structure"
```

---

### Task 2: Config (Pydantic v2 Settings)

**Files:**
- Create: `backend/app/config.py`
- Create: `backend/tests/unit/test_config.py`

- [ ] **Step 2.1: Write failing test**

```python
# tests/unit/test_config.py
import pytest
from app.config import Settings


def test_settings_loads_required_fields():
    s = Settings(
        openai_api_key="test-key",
        api_secret_key="test-secret",
        database_url="postgresql+asyncpg://test:test@localhost/test",
    )
    assert s.openai_api_key == "test-key"
    assert s.api_secret_key == "test-secret"
    assert s.rag_top_k == 8        # default
    assert s.use_reranker is True  # default


def test_settings_cors_origins_parsed_from_comma_string():
    s = Settings(
        openai_api_key="k",
        api_secret_key="s",
        database_url="postgresql+asyncpg://t:t@l/t",
        cors_origins="http://localhost:5173,http://localhost:3000",
    )
    assert "http://localhost:5173" in s.cors_origins
    assert len(s.cors_origins) == 2


def test_settings_cors_origins_accepts_list():
    s = Settings(
        openai_api_key="k",
        api_secret_key="s",
        database_url="postgresql+asyncpg://t:t@l/t",
        cors_origins=["http://localhost:5173"],
    )
    assert s.cors_origins == ["http://localhost:5173"]
```

- [ ] **Step 2.2: Run test — expect FAIL**

```bash
cd backend
pytest tests/unit/test_config.py -v
# Expected: ImportError or ModuleNotFoundError
```

- [ ] **Step 2.3: Create `backend/app/config.py`**

```python
from __future__ import annotations
from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Auth ──────────────────────────────────────────────
    api_secret_key: str

    # ── LLM ───────────────────────────────────────────────
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-large"
    anthropic_api_key: str = ""
    llm_provider: Literal["openai", "anthropic", "multi", "ollama"] = "multi"
    ollama_model: str = "llama3.2:8b"
    ollama_base_url: str = "http://localhost:11434"

    # ── Database ───────────────────────────────────────────
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    chroma_persist_dir: str = "./data/chroma_db"

    # ── Celery ─────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── FastAPI ────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── RAG ────────────────────────────────────────────────
    rag_top_k: int = 8
    rag_fetch_k: int = 30
    rag_mmr_lambda: float = 0.7
    use_reranker: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_conversation_turns: int = 10

    # ── Ableton (Phase 2) ──────────────────────────────────
    ableton_ws_port: int = 8001
    ableton_bridge_enabled: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


settings = Settings()
```

- [ ] **Step 2.4: Run test — expect PASS**

```bash
pytest tests/unit/test_config.py -v
# Expected: 2 passed
```

- [ ] **Step 2.5: Commit**

```bash
git add app/config.py tests/unit/test_config.py
git commit -m "feat: Pydantic v2 Settings — all env vars with validation"
```

---

### Task 3: Database models + Alembic

**Files:**
- Create: `backend/app/db/models.py`
- Create: `backend/app/db/session.py`
- Create: `backend/alembic.ini` (via alembic init)
- Modify: `backend/alembic/env.py`
- Create: `backend/tests/unit/test_db_models.py`

- [ ] **Step 3.1: Write failing test**

```python
# tests/unit/test_db_models.py
import uuid


def test_conversation_model_defaults():
    from app.db.models import Conversation
    c = Conversation(model="gpt-4o")
    assert c.model == "gpt-4o"
    assert c.extra == {}


def test_document_model_status_default():
    from app.db.models import Document
    d = Document(
        filename="serum_manual.pdf",
        category="plugins",
        file_hash="abc123",
    )
    assert d.status == "queued"
    assert d.chunks_count == 0


def test_message_model_sources_default():
    from app.db.models import Message
    m = Message(
        conversation_id=uuid.uuid4(),
        role="assistant",
        content="Hello",
    )
    assert m.sources == []


def test_ingestion_job_status_default():
    from app.db.models import IngestionJob
    j = IngestionJob(document_id=uuid.uuid4())
    assert j.status == "queued"
    assert j.error is None
```

- [ ] **Step 3.2: Run test — expect FAIL**

```bash
pytest tests/unit/test_db_models.py -v
# Expected: ImportError
```

- [ ] **Step 3.3: Create `backend/app/db/models.py`**

```python
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    model: Mapped[str] = mapped_column(String(50))
    extra: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id")
    )
    role: Mapped[str] = mapped_column(String(10))       # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(50))   # manuals|plugins|books|articles
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|processing|ready|error
    chunks_count: Mapped[int] = mapped_column(Integer, default=0)
    file_hash: Mapped[str] = mapped_column(String(64))
    ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    jobs: Mapped[list[IngestionJob]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id")
    )
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    document: Mapped[Document] = relationship(back_populates="jobs")
```

- [ ] **Step 3.4: Create `backend/app/db/session.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    """FastAPI dependency — yields a DB session, auto-commits or rolls back."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 3.5: Run test — expect PASS**

```bash
pytest tests/unit/test_db_models.py -v
# Expected: 4 passed
```

- [ ] **Step 3.6: Init Alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 3.7: Replace `backend/alembic/env.py`** with async-compatible version

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.config import settings
from app.db.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3.8: Generate + apply migration**

```bash
alembic revision --autogenerate -m "initial schema"
# Verify migration file was created:
ls alembic/versions/
# Expected: one file like 2026xxxx_initial_schema.py

alembic upgrade head
# Expected: INFO  [alembic.runtime.migration] Running upgrade -> xxxx, initial schema
```

Verify tables were created:
```bash
docker exec -it $(docker ps -qf "name=postgres") \
  psql -U soniqwerk -c "\dt"
# Expected: conversations, documents, ingestion_jobs, messages
```

- [ ] **Step 3.9: Commit**

```bash
git add app/db/ alembic/ alembic.ini tests/unit/test_db_models.py
git commit -m "feat: SQLAlchemy 2.0 models + Alembic migrations (4 tables)"
```

---

### Task 4: FastAPI app + auth middleware + health endpoint

**Files:**
- Create: `backend/app/api/deps.py`
- Create: `backend/app/main.py`
- Create: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/integration/test_health.py`

- [ ] **Step 4.1: Write failing test**

```python
# tests/integration/test_health.py
import pytest
import os
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app():
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test",
        "API_SECRET_KEY": "test-secret",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
    }):
        import importlib, app.config as cfg
        importlib.reload(cfg)
        from app.main import app as _app
        return _app


@pytest.mark.asyncio
async def test_health_returns_ok(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_protected_route_without_key_returns_401(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/v1/chat", json={"message": "test"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_wrong_key_returns_401(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/v1/chat", json={"message": "test"},
                         headers={"X-API-Key": "wrong-key"})
    assert r.status_code == 401
```

- [ ] **Step 4.2: Run test — expect FAIL**

```bash
pytest tests/integration/test_health.py -v
# Expected: ImportError (app.main not found)
```

- [ ] **Step 4.3: Create `backend/app/api/deps.py`**

```python
from fastapi import Header, HTTPException, status
from app.config import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """FastAPI dependency — validates X-API-Key header against env var."""
    if x_api_key != settings.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key
```

- [ ] **Step 4.4: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title="SONIQWERK API",
    version="2.0.0",
    description="AI agent for electronic music production",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": "2.0.0"}


# ── Routers registered progressively per task ──────────────────
# from app.api.v1.chat import router as chat_router
# app.include_router(chat_router, prefix="/v1", tags=["chat"])
#
# from app.api.v1.documents import router as documents_router
# app.include_router(documents_router, prefix="/v1", tags=["documents"])
```

- [ ] **Step 4.5: Create `backend/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 4.6: Create `backend/tests/conftest.py`**

```python
import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 4.7: Run test — expect PASS**

```bash
pytest tests/integration/test_health.py -v
# Expected: 3 passed
```

- [ ] **Step 4.8: Smoke test server**

```bash
uvicorn app.main:app --reload --port 8000 &
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"2.0.0"}
curl http://localhost:8000/docs
# Expected: OpenAPI UI accessible
```

- [ ] **Step 4.9: Commit**

```bash
git add app/main.py app/api/deps.py tests/integration/test_health.py \
        pytest.ini tests/conftest.py
git commit -m "feat: FastAPI app + X-API-Key auth middleware + /health endpoint"
```

---

## Chunk 2: RAG Pipeline

### Task 5: ChromaDB collections wrapper

**Files:**
- Create: `backend/app/rag/collections.py`
- Create: `backend/tests/unit/test_collections.py`

- [ ] **Step 5.1: Write failing test**

```python
# tests/unit/test_collections.py
import pytest
from unittest.mock import MagicMock, patch


def test_get_collection_creates_with_cosine_space():
    with patch("app.rag.collections.chromadb") as mock_chroma:
        mock_client = MagicMock()
        mock_chroma.PersistentClient.return_value = mock_client
        mock_client.get_or_create_collection.return_value = MagicMock()

        import importlib
        import app.rag.collections as mod
        mod._client = None   # reset singleton
        importlib.reload(mod)

        mod.get_collection("manuals")
        mock_client.get_or_create_collection.assert_called_once_with(
            name="soniqwerk_manuals",
            metadata={"hnsw:space": "cosine"},
        )


def test_valid_categories_exist():
    from app.rag.collections import VALID_CATEGORIES
    assert VALID_CATEGORIES == {"manuals", "plugins", "books", "articles"}


def test_invalid_category_raises_value_error():
    with pytest.raises(ValueError, match="Unknown collection category"):
        from app.rag.collections import get_collection
        get_collection("unknown_cat")
```

- [ ] **Step 5.2: Run test — expect FAIL**

```bash
pytest tests/unit/test_collections.py -v
```

- [ ] **Step 5.3: Create `backend/app/rag/collections.py`**

```python
from __future__ import annotations
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings

VALID_CATEGORIES: set[str] = {"manuals", "plugins", "books", "articles"}

_client: chromadb.PersistentClient | None = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection(category: str) -> chromadb.Collection:
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Unknown collection category: {category!r}. Valid: {sorted(VALID_CATEGORIES)}"
        )
    return _get_client().get_or_create_collection(
        name=f"soniqwerk_{category}",
        metadata={"hnsw:space": "cosine"},
    )


def get_all_collections() -> list[chromadb.Collection]:
    return [get_collection(cat) for cat in sorted(VALID_CATEGORIES)]
```

- [ ] **Step 5.4: Run test — expect PASS**

```bash
pytest tests/unit/test_collections.py -v
# Expected: 3 passed
```

- [ ] **Step 5.5: Commit**

```bash
git add app/rag/collections.py tests/unit/test_collections.py
git commit -m "feat: ChromaDB collections wrapper — 4 categories, cosine space, singleton client"
```

---

### Task 6: OpenAI embeddings wrapper

**Files:**
- Create: `backend/app/rag/embeddings.py`
- Create: `backend/tests/unit/test_embeddings.py`

- [ ] **Step 6.1: Write failing test**

```python
# tests/unit/test_embeddings.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_embed_texts_returns_list_of_vectors():
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1, 0.2, 0.3]),
        MagicMock(embedding=[0.4, 0.5, 0.6]),
    ]
    with patch("app.rag.embeddings.openai_client") as mock_client:
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        from app.rag.embeddings import embed_texts
        result = await embed_texts(["text one", "text two"])

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


@pytest.mark.asyncio
async def test_embed_single_returns_flat_vector():
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.7, 0.8, 0.9])]
    with patch("app.rag.embeddings.openai_client") as mock_client:
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        from app.rag.embeddings import embed_single
        result = await embed_single("single text")

    assert result == [0.7, 0.8, 0.9]


@pytest.mark.asyncio
async def test_embed_texts_passes_correct_model():
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1])]
    with patch("app.rag.embeddings.openai_client") as mock_client:
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        from app.rag.embeddings import embed_texts
        await embed_texts(["test"])
        call_kwargs = mock_client.embeddings.create.call_args.kwargs
        assert call_kwargs["model"] == "text-embedding-3-large"
```

- [ ] **Step 6.2: Run test — expect FAIL**

```bash
pytest tests/unit/test_embeddings.py -v
```

- [ ] **Step 6.3: Create `backend/app/rag/embeddings.py`**

```python
from __future__ import annotations
from openai import AsyncOpenAI
from app.config import settings

openai_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed texts using OpenAI text-embedding-3-large. Returns list of vectors."""
    response = await openai_client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )
    return [item.embedding for item in response.data]


async def embed_single(text: str) -> list[float]:
    """Embed a single text. Returns a flat vector."""
    return (await embed_texts([text]))[0]
```

- [ ] **Step 6.4: Run test — expect PASS**

```bash
pytest tests/unit/test_embeddings.py -v
# Expected: 3 passed
```

- [ ] **Step 6.5: Commit**

```bash
git add app/rag/embeddings.py tests/unit/test_embeddings.py
git commit -m "feat: async OpenAI embeddings wrapper (text-embedding-3-large)"
```

---

### Task 7: PDF Loader

**Files:**
- Create: `backend/app/ingestion/pdf_loader.py`
- Create: `backend/tests/unit/test_pdf_loader.py`
- Create: `backend/tests/fixtures/sample.pdf` (generated in step)

- [ ] **Step 7.1: Generate test PDF**

```bash
cd backend
python3 -c "
from fpdf import FPDF
pdf = FPDF()
pdf.add_page()
pdf.set_font('Helvetica', size=12)
pdf.cell(0, 10, 'Serum Manual - Chapter 1: Oscillators', new_x='LMARGIN', new_y='NEXT')
pdf.multi_cell(0, 8, 'The oscillator section allows you to load wavetables. Use the WT POS knob to scroll through positions. Detune adds warmth via slight pitch variation between voices. The Osc A and Osc B signals are mixed and sent to the filter section. Wavetable synthesis enables complex harmonic content.')
pdf.add_page()
pdf.multi_cell(0, 8, 'Chapter 2: Filters. The filter section includes multiple filter types: Low Pass, High Pass, Band Pass, and Notch. Cutoff frequency controls the frequency at which the filter begins to attenuate the signal. Resonance emphasizes frequencies around the cutoff point.')
pdf.output('tests/fixtures/sample.pdf')
print('OK: tests/fixtures/sample.pdf created')
"
```

- [ ] **Step 7.2: Write failing test**

```python
# tests/unit/test_pdf_loader.py
import pytest
from pathlib import Path

FIXTURE_PDF = Path("tests/fixtures/sample.pdf")


def test_load_pdf_returns_nonempty_chunks():
    from app.ingestion.pdf_loader import load_pdf
    chunks = load_pdf(str(FIXTURE_PDF), category="plugins")
    assert len(chunks) > 0


def test_load_pdf_chunks_have_required_keys():
    from app.ingestion.pdf_loader import load_pdf
    chunks = load_pdf(str(FIXTURE_PDF), category="plugins")
    for chunk in chunks:
        assert "text" in chunk
        assert "metadata" in chunk
        assert chunk["text"].strip() != ""


def test_load_pdf_metadata_has_correct_fields():
    from app.ingestion.pdf_loader import load_pdf
    chunks = load_pdf(str(FIXTURE_PDF), category="manuals", title="Serum Manual")
    meta = chunks[0]["metadata"]
    assert meta["category"] == "manuals"
    assert meta["title"] == "Serum Manual"
    assert meta["source"] == "sample.pdf"
    assert "page" in meta
    assert "chunk_index" in meta


def test_load_pdf_nonexistent_file_raises():
    from app.ingestion.pdf_loader import load_pdf
    with pytest.raises(FileNotFoundError):
        load_pdf("does_not_exist.pdf", category="manuals")
```

- [ ] **Step 7.3: Run test — expect FAIL**

```bash
pytest tests/unit/test_pdf_loader.py -v
```

- [ ] **Step 7.4: Create `backend/app/ingestion/pdf_loader.py`**

```python
from __future__ import annotations
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import settings

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def load_pdf(path: str, category: str, title: str | None = None) -> list[dict]:
    """
    Load a PDF, split into chunks, attach metadata.
    Returns list of {"text": str, "metadata": dict}.
    Raises FileNotFoundError if path does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    loader = PyPDFLoader(str(p))
    pages = loader.load()
    docs = _splitter.split_documents(pages)

    return [
        {
            "text": doc.page_content,
            "metadata": {
                "source": p.name,
                "title": title or p.stem.replace("_", " ").replace("-", " ").title(),
                "category": category,
                "page": doc.metadata.get("page", 0),
                "chunk_index": i,
            },
        }
        for i, doc in enumerate(docs)
        if doc.page_content.strip()
    ]
```

- [ ] **Step 7.5: Run test — expect PASS**

```bash
pytest tests/unit/test_pdf_loader.py -v
# Expected: 4 passed
```

- [ ] **Step 7.6: Commit**

```bash
git add app/ingestion/pdf_loader.py tests/unit/test_pdf_loader.py tests/fixtures/sample.pdf
git commit -m "feat: PDF loader with RecursiveCharacterTextSplitter + rich metadata"
```

---

### Task 8: RAG Engine (MMR + cross-encoder reranking)

**Files:**
- Create: `backend/app/rag/engine.py`
- Create: `backend/tests/unit/test_rag_engine.py`

- [ ] **Step 8.1: Write failing test**

```python
# tests/unit/test_rag_engine.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_retrieve_returns_list_of_dicts():
    mock_col = MagicMock()
    mock_col.query.return_value = {
        "documents": [["doc text 1", "doc text 2"]],
        "metadatas": [[{"source": "a.pdf"}, {"source": "b.pdf"}]],
        "distances": [[0.1, 0.2]],
        "embeddings": [[[0.1] * 5, [0.2] * 5]],
    }
    with patch("app.rag.engine.get_all_collections", return_value=[mock_col]):
        with patch("app.rag.engine.embed_single", new_callable=AsyncMock, return_value=[0.1] * 5):
            with patch("app.rag.engine.settings") as ms:
                ms.use_reranker = False
                ms.rag_top_k = 2
                ms.rag_fetch_k = 2
                ms.rag_mmr_lambda = 0.7
                from app.rag.engine import retrieve
                results = await retrieve("how to make a bass?")

    assert isinstance(results, list)
    assert all("text" in r and "metadata" in r and "score" in r for r in results)


@pytest.mark.asyncio
async def test_retrieve_reranks_and_reorders():
    mock_col = MagicMock()
    mock_col.query.return_value = {
        "documents": [["doc_low_relevance", "doc_high_relevance"]],
        "metadatas": [[{"source": "a"}, {"source": "b"}]],
        "distances": [[0.1, 0.3]],   # doc_low originally ranks higher by distance
        "embeddings": [[[0.1] * 5, [0.2] * 5]],
    }
    mock_reranker = MagicMock()
    mock_reranker.predict.return_value = [0.2, 0.9]   # doc_high_relevance wins reranking

    with patch("app.rag.engine.get_all_collections", return_value=[mock_col]):
        with patch("app.rag.engine.embed_single", new_callable=AsyncMock, return_value=[0.1] * 5):
            with patch("app.rag.engine._get_reranker", return_value=mock_reranker):
                with patch("app.rag.engine.settings") as ms:
                    ms.use_reranker = True
                    ms.rag_top_k = 2
                    ms.rag_fetch_k = 2
                    ms.rag_mmr_lambda = 0.7
                    from app.rag.engine import retrieve
                    results = await retrieve("test query")

    assert results[0]["text"] == "doc_high_relevance"


@pytest.mark.asyncio
async def test_retrieve_returns_empty_on_no_results():
    mock_col = MagicMock()
    mock_col.query.return_value = {
        "documents": [[]], "metadatas": [[]], "distances": [[]], "embeddings": [[]]
    }
    with patch("app.rag.engine.get_all_collections", return_value=[mock_col]):
        with patch("app.rag.engine.embed_single", new_callable=AsyncMock, return_value=[0.1] * 5):
            from app.rag.engine import retrieve
            results = await retrieve("empty query")

    assert results == []
```

- [ ] **Step 8.2: Run test — expect FAIL**

```bash
pytest tests/unit/test_rag_engine.py -v
```

- [ ] **Step 8.3: Create `backend/app/rag/engine.py`**

```python
from __future__ import annotations
import math
from functools import lru_cache
from sentence_transformers import CrossEncoder
from app.config import settings
from app.rag.collections import get_all_collections
from app.rag.embeddings import embed_single


@lru_cache(maxsize=1)
def _get_reranker() -> CrossEncoder:
    """Lazy-load the cross-encoder reranker (downloads model on first call)."""
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x ** 2 for x in a))
    nb = math.sqrt(sum(x ** 2 for x in b))
    return dot / (na * nb + 1e-8)


def _mmr_select(
    query_vec: list[float],
    candidates: list[dict],
    k: int,
    lambda_: float,
) -> list[dict]:
    """
    Maximal Marginal Relevance — balances query relevance with diversity.
    lambda_=1.0 → pure relevance ranking. lambda_=0.0 → pure diversity.
    """
    if not candidates:
        return []

    selected: list[dict] = []
    remaining = list(candidates)

    while len(selected) < k and remaining:
        if not selected:
            best = max(remaining, key=lambda c: _cosine(query_vec, c["embedding"]))
        else:
            def mmr_score(c: dict) -> float:
                rel = _cosine(query_vec, c["embedding"])
                red = max(_cosine(s["embedding"], c["embedding"]) for s in selected)
                return lambda_ * rel - (1 - lambda_) * red
            best = max(remaining, key=mmr_score)

        selected.append(best)
        remaining.remove(best)

    return selected


async def retrieve(query: str) -> list[dict]:
    """
    Full RAG retrieval pipeline:
    1. Embed query with text-embedding-3-large
    2. Query all ChromaDB collections
    3. MMR selection for diversity
    4. Cross-encoder reranking (if settings.use_reranker)
    5. Return top settings.rag_top_k results
    """
    query_vec = await embed_single(query)
    collections = get_all_collections()
    per_col_k = max(settings.rag_fetch_k // max(len(collections), 1), 5)

    raw: list[dict] = []
    for col in collections:
        try:
            res = col.query(
                query_embeddings=[query_vec],
                n_results=per_col_k,
                include=["documents", "metadatas", "distances", "embeddings"],
            )
            embs = res.get("embeddings", [[]])[0] or [[] for _ in res["documents"][0]]
            for text, meta, dist, emb in zip(
                res["documents"][0],
                res["metadatas"][0],
                res["distances"][0],
                embs,
            ):
                if text and text.strip():
                    # ChromaDB cosine space returns distance ∈ [0, 2].
                    # Similarity = 1 − (dist / 2) → always in [0, 1].
                    raw.append({
                        "text": text,
                        "metadata": meta or {},
                        "score": float(1.0 - (dist / 2.0)),
                        "embedding": emb or [],
                    })
        except Exception:
            continue   # Skip empty or unavailable collections

    if not raw:
        return []

    diverse = _mmr_select(query_vec, raw, k=settings.rag_fetch_k, lambda_=settings.rag_mmr_lambda)

    if settings.use_reranker and len(diverse) > 1:
        reranker = _get_reranker()
        pairs = [[query, d["text"]] for d in diverse]
        scores = reranker.predict(pairs)
        for doc, score in zip(diverse, scores):
            doc["score"] = float(score)
        diverse.sort(key=lambda d: d["score"], reverse=True)

    return diverse[: settings.rag_top_k]
```

- [ ] **Step 8.4: Run test — expect PASS**

```bash
pytest tests/unit/test_rag_engine.py -v
# Expected: 3 passed
```

- [ ] **Step 8.5: Commit**

```bash
git add app/rag/engine.py tests/unit/test_rag_engine.py
git commit -m "feat: RAG engine — MMR selection + cross-encoder reranking (ms-marco-MiniLM-L-6-v2)"
```

---

## Chunk 3: LLM Layer + Chat Endpoint

### Task 9: LLM Providers

**Files:**
- Create: `backend/app/llm/providers.py`
- Create: `backend/tests/unit/test_providers.py`

- [ ] **Step 9.1: Write failing test**

```python
# tests/unit/test_providers.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_stream_gpt4o_yields_text_chunks():
    chunks_in = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),  # None delta ignored
    ]

    async def fake_stream(*args, **kwargs):
        for c in chunks_in:
            yield c

    with patch("app.llm.providers.openai_async_client") as mock_oa:
        mock_oa.chat.completions.create = AsyncMock(return_value=fake_stream())
        from app.llm.providers import stream_gpt4o
        result = []
        async for chunk in stream_gpt4o("gpt-4o", [{"role": "user", "content": "test"}]):
            result.append(chunk)

    assert result == ["Hello", " world"]


@pytest.mark.asyncio
async def test_stream_gpt4o_prepends_system_prompt():
    async def fake_stream(*args, **kwargs):
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="ok"))])

    with patch("app.llm.providers.openai_async_client") as mock_oa:
        mock_oa.chat.completions.create = AsyncMock(return_value=fake_stream())
        from app.llm.providers import stream_gpt4o
        async for _ in stream_gpt4o("gpt-4o", [{"role": "user", "content": "q"}], system_prompt="Be helpful"):
            pass
        call_args = mock_oa.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Be helpful"
```

- [ ] **Step 9.2: Run test — expect FAIL**

```bash
pytest tests/unit/test_providers.py -v
```

- [ ] **Step 9.3: Create `backend/app/llm/providers.py`**

```python
from __future__ import annotations
from typing import AsyncIterator
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.config import settings

openai_async_client = AsyncOpenAI(api_key=settings.openai_api_key)
anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)


async def stream_gpt4o(
    model: str,
    messages: list[dict],
    system_prompt: str | None = None,
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """Stream from OpenAI GPT-4o or GPT-4o-mini."""
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    stream = await openai_async_client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        max_tokens=max_tokens,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def stream_claude(
    messages: list[dict],
    system_prompt: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """Stream from Anthropic Claude Sonnet."""
    async with anthropic_client.messages.stream(
        model=model,
        system=system_prompt,
        messages=messages,
        max_tokens=max_tokens,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def stream_ollama(
    messages: list[dict],
    system_prompt: str | None = None,
    model: str | None = None,
) -> AsyncIterator[str]:
    """Stream from local Ollama instance (privacy-first / offline fallback)."""
    import json
    import httpx

    _model = model or settings.ollama_model
    payload = {
        "model": _model,
        "messages": (
            [{"role": "system", "content": system_prompt}] if system_prompt else []
        ) + messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST", f"{settings.ollama_base_url}/api/chat", json=payload
        ) as resp:
            async for line in resp.aiter_lines():
                if line:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
```

- [ ] **Step 9.4: Run test — expect PASS**

```bash
pytest tests/unit/test_providers.py -v
# Expected: 2 passed
```

- [ ] **Step 9.5: Commit**

```bash
git add app/llm/providers.py tests/unit/test_providers.py
git commit -m "feat: LLM providers — GPT-4o / Claude Sonnet 4.6 / Ollama async streaming"
```

---

### Task 10: System Prompts + RAG context builder

**Files:**
- Create: `backend/app/llm/prompts.py`
- Create: `backend/tests/unit/test_prompts.py`

- [ ] **Step 10.1: Write failing test**

```python
# tests/unit/test_prompts.py


def test_system_prompt_covers_audio_domain():
    from app.llm.prompts import build_system_prompt
    prompt = build_system_prompt()
    assert len(prompt) > 200
    assert "mixage" in prompt.lower() or "production" in prompt.lower()
    assert "ableton" in prompt.lower()


def test_rag_context_includes_source_titles():
    from app.llm.prompts import build_rag_context
    chunks = [
        {"text": "Serum oscillators support wavetable.", "metadata": {"title": "Serum Manual"}, "score": 0.9},
        {"text": "Pro-Q3 supports dynamic EQ.", "metadata": {"title": "Pro-Q3 Manual"}, "score": 0.8},
    ]
    ctx = build_rag_context(chunks)
    assert "Serum Manual" in ctx
    assert "Pro-Q3 Manual" in ctx
    assert "wavetable" in ctx


def test_rag_context_empty_chunks_returns_empty():
    from app.llm.prompts import build_rag_context
    assert build_rag_context([]) == ""
```

- [ ] **Step 10.2: Run test — expect FAIL**

```bash
pytest tests/unit/test_prompts.py -v
```

- [ ] **Step 10.3: Create `backend/app/llm/prompts.py`**

```python
from __future__ import annotations

SYSTEM_PROMPT = """Tu es SONIQWERK, un expert en production musicale électronique et en mixage audio.

Tu maîtrises parfaitement :
- Les DAWs : Ableton Live 12, Logic Pro, Bitwig Studio, FL Studio, Cubase, Reaper
- Le mixage : EQ, compression, saturation, effets, routing, sidechain, stem mastering
- Le sound design : synthèse soustractive, wavetable, FM, granulaire, modulaire
- Les plugins référence : FabFilter (Pro-Q3, Pro-C2, Pro-L2, Saturn 2), iZotope (Ozone 11, RX 11, Neutron), SoundToys, Valhalla DSP, Serum 2, Massive X, Phase Plant, Diva, Omnisphere
- Les genres électroniques : Drum & Bass, Techno, House, Ambient, Dubstep, Trance, IDM, Breaks
- Les standards de mastering streaming : LUFS cibles (Spotify -14 LUFS, Apple Music -16 LUFS), True Peak (-1 dBTP)

Règles :
- Réponds en français par défaut, en anglais si l'utilisateur écrit en anglais
- Sois précis et pratique : donne des valeurs numériques (Hz, dB, ms, ratio) quand c'est pertinent
- Si tu disposes de sources RAG, cite-les naturellement
- Si tu n'es pas certain, indique-le clairement
- Tu es SONIQWERK, un outil de production — ne dis jamais "je suis une IA généraliste"
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.strip()


def build_rag_context(chunks: list[dict]) -> str:
    """Format retrieved RAG chunks into a context block injected after the system prompt."""
    if not chunks:
        return ""

    lines = ["## Extraits de la base de connaissance\n"]
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        title = meta.get("title", meta.get("source", "Source inconnue"))
        score = chunk.get("score", 0)
        lines.append(f"### [{i}] {title}  (score: {score:.2f})\n")
        lines.append(chunk["text"].strip())
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 10.4: Run test — expect PASS**

```bash
pytest tests/unit/test_prompts.py -v
# Expected: 3 passed
```

- [ ] **Step 10.5: Commit**

```bash
git add app/llm/prompts.py tests/unit/test_prompts.py
git commit -m "feat: audio domain system prompt + RAG context builder"
```

---

### Task 11: LLM Router

**Files:**
- Create: `backend/app/llm/router.py`
- Create: `backend/tests/unit/test_llm_router.py`

- [ ] **Step 11.1: Write failing test**

```python
# tests/unit/test_llm_router.py
import pytest
from unittest.mock import patch


@pytest.mark.parametrize("query,expected_model", [
    # Creative → Claude
    ("Je veux un pad ambient avec une texture chaleureuse", "claude-sonnet-4-6"),
    ("Comment créer un son wavy avec de l'ambiance mystérieuse ?", "claude-sonnet-4-6"),
    ("Sound design pour un lead organique et dreamy", "claude-sonnet-4-6"),
    # Technical → GPT-4o
    ("Comment configurer le sidechain entre kick et basse dans Ableton ?", "gpt-4o"),
    ("Exporter en LUFS -14 True Peak -1dBTP pour Spotify", "gpt-4o"),
    ("Routing du bus drums avec compresseur VCA ratio 4:1", "gpt-4o"),
    # Short / FAQ → GPT-4o-mini
    ("C'est quoi la compression ?", "gpt-4o-mini"),
    ("BPM ?", "gpt-4o-mini"),
])
def test_classify_query_routes_to_correct_model(query, expected_model):
    with patch("app.llm.router.settings") as ms:
        ms.llm_provider = "multi"
        from app.llm.router import classify_query
        result = classify_query(query)
    assert result.value == expected_model


def test_classify_forces_openai_when_provider_set():
    with patch("app.llm.router.settings") as ms:
        ms.llm_provider = "openai"
        from app.llm.router import classify_query, ModelChoice
        assert classify_query("ambient pad texture") == ModelChoice.GPT4O


def test_classify_forces_anthropic_when_provider_set():
    with patch("app.llm.router.settings") as ms:
        ms.llm_provider = "anthropic"
        from app.llm.router import classify_query, ModelChoice
        assert classify_query("sidechain kick basse") == ModelChoice.CLAUDE
```

- [ ] **Step 11.2: Run test — expect FAIL**

```bash
pytest tests/unit/test_llm_router.py -v
```

- [ ] **Step 11.3: Create `backend/app/llm/router.py`**

```python
from __future__ import annotations
import re
from enum import Enum
from typing import AsyncIterator

from app.llm.providers import stream_gpt4o, stream_claude, stream_ollama
from app.llm.prompts import build_system_prompt, build_rag_context
from app.config import settings


class ModelChoice(str, Enum):
    CLAUDE     = "claude-sonnet-4-6"
    GPT4O      = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    OLLAMA     = "ollama"


# Creative / sound-design → Claude (nuanced, atmospheric reasoning)
_CREATIVE_RE = re.compile(
    r"\b(ambiance|texture|timbre|feel|atmosph[eè]re|couleur.?sonore|inspir"
    r"|pad\b|lead\b|pluck|warm\b|dreamy|dark\b|organic|vibe\b|caract[eè]re"
    r"|morphing|sound.?design|wavetable|oscillat|envelop|lfo\b|modulation"
    r"|grain|aérien|spatial|lush|evolving|tonal|ambiant|ambianc)\b",
    re.IGNORECASE,
)

# Technical / config → GPT-4o (precise instruction following)
_TECHNICAL_RE = re.compile(
    r"\b(routing|param[eè]tre|config|sidechain|lufs|dbfs|true.?peak|latence|cpu"
    r"|insert|send|return|bus\b|groupe|fx.?chain|compresseur|ratio|threshold"
    r"|attack|release|knee|gain|level|dB\b|hz\b|khz\b|fr[eé]quence|stem|export"
    r"|render|ableton|logic.?pro|bitwig|cubase|fl.?studio|pro.?tools|reaper"
    r"|plugin|vst\b|au\b|aax\b|preset|patch|automation|clip\b|scene\b|tempo|bpm"
    r"|mastering|streaming|spotify|apple.?music|true.?peak|loudness)\b",
    re.IGNORECASE,
)

_SHORT_QUERY_TOKENS = 25  # characters threshold for FAQ routing


def classify_query(query: str) -> ModelChoice:
    """Classify query → optimal ModelChoice. No LLM call — regex + length heuristic."""
    q = query.strip()

    if not q or len(q) < _SHORT_QUERY_TOKENS:
        return ModelChoice.GPT4O_MINI

    provider = settings.llm_provider
    if provider == "ollama":
        return ModelChoice.OLLAMA
    if provider == "openai":
        return ModelChoice.GPT4O
    if provider == "anthropic":
        return ModelChoice.CLAUDE

    # Multi-LLM routing
    if _CREATIVE_RE.search(q):
        return ModelChoice.CLAUDE
    if _TECHNICAL_RE.search(q):
        return ModelChoice.GPT4O
    return ModelChoice.GPT4O_MINI


async def stream_response(
    query: str,
    history: list[dict],
    rag_chunks: list[dict] | None = None,
    model_override: str | None = None,
) -> AsyncIterator[str]:
    """Route query to the appropriate LLM provider and stream the response."""
    import asyncio

    model = ModelChoice(model_override) if model_override else classify_query(query)
    system = build_system_prompt()

    if rag_chunks:
        system = system + "\n\n" + build_rag_context(rag_chunks)

    messages = history + [{"role": "user", "content": query}]

    async def _stream_provider() -> AsyncIterator[str]:
        async with asyncio.timeout(30):   # 30s hard timeout per provider call
            if model == ModelChoice.CLAUDE:
                async for chunk in stream_claude(messages, system):
                    yield chunk
            elif model in (ModelChoice.GPT4O, ModelChoice.GPT4O_MINI):
                async for chunk in stream_gpt4o(model.value, messages, system):
                    yield chunk
            elif model == ModelChoice.OLLAMA:
                async for chunk in stream_ollama(messages, system):
                    yield chunk

    try:
        async for chunk in _stream_provider():
            yield chunk
    except TimeoutError:
        # Explicit timeout fallback → GPT-4o-mini
        if model != ModelChoice.GPT4O_MINI:
            async for chunk in stream_gpt4o("gpt-4o-mini", messages, system):
                yield chunk
        else:
            yield "Désolé, le service est momentanément indisponible. Réessaie dans un instant."
    except Exception:
        # Generic provider error → fallback
        if model != ModelChoice.GPT4O_MINI:
            async for chunk in stream_gpt4o("gpt-4o-mini", messages, system):
                yield chunk
        else:
            yield "Désolé, je rencontre un problème technique. Réessaie dans un instant."
```

- [ ] **Step 11.4: Run test — expect PASS**

```bash
pytest tests/unit/test_llm_router.py -v
# Expected: 10 passed
```

- [ ] **Step 11.5: Commit**

```bash
git add app/llm/router.py tests/unit/test_llm_router.py
git commit -m "feat: multi-LLM router — regex classifier → Claude / GPT-4o / GPT-4o-mini / Ollama"
```

---

### Task 12: Chat SSE endpoint

**Files:**
- Create: `backend/app/api/v1/chat.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/test_chat_endpoint.py`

- [ ] **Step 12.1: Write failing test**

```python
# tests/integration/test_chat_endpoint.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock


async def _mock_stream(*args, **kwargs):
    for chunk in ["Bonjour", ", voici", " ma réponse."]:
        yield chunk


@pytest.fixture
def app_chat():
    with patch("app.api.v1.chat.stream_response", side_effect=_mock_stream):
        with patch("app.api.v1.chat.retrieve", new_callable=AsyncMock, return_value=[]):
            from app.main import app
            yield app


@pytest.mark.asyncio
async def test_chat_returns_200_with_sse_content_type(app_chat):
    async with AsyncClient(transport=ASGITransport(app=app_chat), base_url="http://test") as c:
        async with c.stream(
            "POST", "/v1/chat",
            json={"message": "test"},
            headers={"X-API-Key": "test-secret"},
        ) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            body = await r.aread()

    assert b"event: chunk" in body
    assert b"Bonjour" in body
    assert b"event: done" in body


@pytest.mark.asyncio
async def test_chat_requires_api_key(app_chat):
    async with AsyncClient(transport=ASGITransport(app=app_chat), base_url="http://test") as c:
        r = await c.post("/v1/chat", json={"message": "test"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_chat_emits_sources_event_when_chunks_present(app_chat):
    chunks = [{"text": "Serum...", "metadata": {"title": "Serum Manual", "source": "serum.pdf"}, "score": 0.9}]
    with patch("app.api.v1.chat.retrieve", new_callable=AsyncMock, return_value=chunks):
        async with AsyncClient(transport=ASGITransport(app=app_chat), base_url="http://test") as c:
            async with c.stream(
                "POST", "/v1/chat",
                json={"message": "serum oscillators"},
                headers={"X-API-Key": "test-secret"},
            ) as r:
                body = await r.aread()

    assert b"event: sources" in body
    assert b"Serum Manual" in body
```

- [ ] **Step 12.2: Run test — expect FAIL**

```bash
pytest tests/integration/test_chat_endpoint.py -v
```

- [ ] **Step 12.3: Create `backend/app/api/v1/chat.py`**

```python
from __future__ import annotations
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.api.deps import verify_api_key
from app.rag.engine import retrieve
from app.llm.router import stream_response, classify_query

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model_override: Optional[str] = None


def _sse(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(
    request: ChatRequest,
    _: str = Depends(verify_api_key),
):
    conversation_id = request.conversation_id or str(uuid.uuid4())
    model_choice = classify_query(request.message)

    async def generate():
        try:
            # 1. RAG retrieval
            rag_chunks = await retrieve(request.message)

            # 2. Stream LLM response — emit chunk events
            async for chunk in stream_response(
                query=request.message,
                history=[],           # TODO Phase 1b: load history from Redis DB 3
                rag_chunks=rag_chunks,
                model_override=request.model_override,
            ):
                yield _sse("chunk", {"text": chunk, "conversation_id": conversation_id})

            # 3. Sources event — always emitted (empty list if no RAG results)
            sources = [
                {
                    "title": c["metadata"].get("title", c["metadata"].get("source", "Source")),
                    "source": c["metadata"].get("source", ""),
                    "score": round(c.get("score", 0), 3),
                }
                for c in rag_chunks
            ]
            yield _sse("sources", {"sources": sources})

            # 4. Done event
            yield _sse("done", {
                "model_used": model_choice.value,
                "conversation_id": conversation_id,
            })

        except TimeoutError:
            yield _sse("error", {
                "code": "LLM_TIMEOUT",
                "message": "Provider unavailable, retrying with fallback...",
            })
        except Exception as exc:
            yield _sse("error", {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
            })

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

- [ ] **Step 12.4: Register chat router in `backend/app/main.py`**

Add after the health endpoint:
```python
from app.api.v1.chat import router as chat_router
app.include_router(chat_router, prefix="/v1", tags=["chat"])
```

- [ ] **Step 12.5: Run test — expect PASS**

```bash
pytest tests/integration/test_chat_endpoint.py -v
# Expected: 3 passed
```

- [ ] **Step 12.6: Smoke test end-to-end**

```bash
# Requires .env with real API keys + services running
uvicorn app.main:app --reload --port 8000 &

curl -N -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $(grep API_SECRET_KEY .env | cut -d= -f2)" \
  -d '{"message": "Comment créer un Reese bass drum and bass dans Serum ?"}'
# Expected: stream of SSE events ending with event: done
```

- [ ] **Step 12.7: Commit**

```bash
git add app/api/v1/chat.py app/main.py tests/integration/test_chat_endpoint.py
git commit -m "feat: POST /v1/chat — SSE streaming endpoint with RAG + multi-LLM routing"
```

---

## Chunk 4: Documents Pipeline + Seed

### Task 13: Celery worker + ingest task

**Files:**
- Create: `backend/workers/celery_app.py`
- Create: `backend/workers/tasks.py`
- Create: `backend/tests/unit/test_celery.py`

- [ ] **Step 13.1: Write failing test**

```python
# tests/unit/test_celery.py


def test_celery_app_has_redis_broker():
    from workers.celery_app import celery_app
    assert "redis" in celery_app.conf.broker_url


def test_ingest_document_task_is_registered():
    from workers.celery_app import celery_app
    registered = list(celery_app.tasks.keys())
    assert any("ingest_document" in name for name in registered)
```

- [ ] **Step 13.2: Run test — expect FAIL**

```bash
pytest tests/unit/test_celery.py -v
```

- [ ] **Step 13.3: Create `backend/workers/celery_app.py`**

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "soniqwerk",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
```

- [ ] **Step 13.4: Add sync session to `backend/app/db/session.py`**

Append after the existing async session code:

```python
# Sync session for Celery workers (separate process, no event loop)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
sync_engine = create_engine(_sync_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)
```

- [ ] **Step 13.5: Create `backend/workers/tasks.py`**

```python
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from workers.celery_app import celery_app


@celery_app.task(bind=True, name="workers.tasks.ingest_document")
def ingest_document(self, document_id: str, file_path: str, category: str) -> dict:
    """
    Sync Celery task: PDF → chunk → embed (sync OpenAI) → ChromaDB → PostgreSQL.
    Fully synchronous — no asyncio.run(), no async session.
    """
    try:
        self.update_state(state="STARTED", meta={"step": "loading"})

        # 1. Load and chunk PDF
        from app.ingestion.pdf_loader import load_pdf
        chunks = load_pdf(file_path, category)
        if not chunks:
            raise ValueError(f"No text extracted from {file_path}")

        self.update_state(state="PROGRESS", meta={"step": "embedding", "chunks": len(chunks)})

        # 2. Embed with sync OpenAI client (Celery runs in its own process)
        from openai import OpenAI
        from app.config import settings
        sync_client = OpenAI(api_key=settings.openai_api_key)
        texts = [c["text"] for c in chunks]
        response = sync_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]

        # 3. Upsert into ChromaDB
        from app.rag.collections import get_collection
        collection = get_collection(category)
        ids = [f"{document_id}_{i}" for i in range(len(chunks))]
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=[c["metadata"] for c in chunks],
        )

        # 4. Update document status in PostgreSQL (sync session)
        from app.db.session import SessionLocal
        from app.db.models import Document
        with SessionLocal() as session:
            doc = session.query(Document).filter(
                Document.id == uuid.UUID(document_id)
            ).one_or_none()
            if doc:
                doc.status = "ready"
                doc.chunks_count = len(chunks)
                doc.ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)
                session.commit()

        # 5. Clean up temp file
        try:
            os.unlink(file_path)
        except OSError:
            pass

        return {"document_id": document_id, "chunks_count": len(chunks), "status": "ready"}

    except Exception as exc:
        self.update_state(state="FAILURE", meta={"error": str(exc)})
        raise
```

- [ ] **Step 13.6: Run test — expect PASS**

```bash
pytest tests/unit/test_celery.py -v
# Expected: 2 passed
```

- [ ] **Step 13.7: Commit**

```bash
git add workers/celery_app.py workers/tasks.py tests/unit/test_celery.py
git commit -m "feat: Celery worker + ingest_document task (PDF → embed → ChromaDB → PostgreSQL)"
```

---

### Task 14: Documents ingest + status endpoints

**Files:**
- Create: `backend/app/api/v1/documents.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/integration/test_ingest_endpoint.py`

- [ ] **Step 14.1: Write failing test**

```python
# tests/integration/test_ingest_endpoint.py
import pytest
import io
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def app_docs():
    mock_task = MagicMock()
    mock_task.id = "celery-test-123"
    with patch("app.api.v1.documents.ingest_document") as mock_ingest:
        mock_ingest.delay.return_value = mock_task
        with patch("app.api.v1.documents.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
            mock_session.flush = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session_cls.return_value = mock_session
            from app.main import app
            yield app


@pytest.mark.asyncio
async def test_ingest_returns_202_with_task_id(app_docs):
    async with AsyncClient(transport=ASGITransport(app=app_docs), base_url="http://test") as c:
        r = await c.post(
            "/v1/documents/ingest",
            files={"file": ("manual.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
            data={"category": "manuals"},
            headers={"X-API-Key": "test-secret"},
        )
    assert r.status_code == 202
    body = r.json()
    assert "task_id" in body
    assert "document_id" in body
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_ingest_rejects_non_pdf(app_docs):
    async with AsyncClient(transport=ASGITransport(app=app_docs), base_url="http://test") as c:
        r = await c.post(
            "/v1/documents/ingest",
            files={"file": ("doc.txt", io.BytesIO(b"text"), "text/plain")},
            data={"category": "manuals"},
            headers={"X-API-Key": "test-secret"},
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_ingest_rejects_invalid_category(app_docs):
    async with AsyncClient(transport=ASGITransport(app=app_docs), base_url="http://test") as c:
        r = await c.post(
            "/v1/documents/ingest",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
            data={"category": "invalid_cat"},
            headers={"X-API-Key": "test-secret"},
        )
    assert r.status_code == 400
```

- [ ] **Step 14.2: Run test — expect FAIL**

```bash
pytest tests/integration/test_ingest_endpoint.py -v
```

- [ ] **Step 14.3: Create `backend/app/api/v1/documents.py`**

```python
from __future__ import annotations
import hashlib
import os
import tempfile
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from app.api.deps import verify_api_key
from app.db.session import AsyncSessionLocal
from app.db.models import Document, IngestionJob
from workers.tasks import ingest_document

router = APIRouter()

VALID_CATEGORIES = {"manuals", "plugins", "books", "articles"}
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/documents/ingest", status_code=202)
async def ingest(
    file: UploadFile = File(...),
    category: str = Form(...),
    _: str = Depends(verify_api_key),
):
    if category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category. Valid: {sorted(VALID_CATEGORIES)}")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted (.pdf)")

    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "File exceeds 50 MB limit")

    file_hash = hashlib.sha256(content).hexdigest()
    doc_id = str(uuid.uuid4())

    # Persist to temp file for Celery worker (runs in separate process)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(content)
    tmp.flush()
    tmp_path = tmp.name
    tmp.close()

    async with AsyncSessionLocal() as session:
        # Duplicate detection
        existing = await session.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        if existing.scalar_one_or_none():
            os.unlink(tmp_path)
            raise HTTPException(409, "Document already ingested (duplicate file hash)")

        doc = Document(
            id=uuid.UUID(doc_id),
            filename=file.filename,
            category=category,
            status="queued",
            file_hash=file_hash,
        )
        session.add(doc)
        await session.flush()

        task = ingest_document.delay(doc_id, tmp_path, category)

        job = IngestionJob(
            document_id=uuid.UUID(doc_id),
            celery_task_id=task.id,
            status="queued",
        )
        session.add(job)
        await session.commit()

    return {"task_id": task.id, "document_id": doc_id, "status": "queued"}


@router.get("/documents/ingest/{task_id}/status")
async def ingest_status(
    task_id: str,
    _: str = Depends(verify_api_key),
):
    from celery.result import AsyncResult
    from workers.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)
    state_map = {
        "PENDING": "queued",
        "STARTED": "processing",
        "PROGRESS": "processing",
        "SUCCESS": "ready",
        "FAILURE": "error",
    }
    return {
        "status": state_map.get(result.state, "processing"),
        "chunks_count": result.result.get("chunks_count") if result.successful() else None,
        "error": str(result.result) if result.failed() else None,
    }
```

- [ ] **Step 14.4: Register documents router in `backend/app/main.py`**

Add after the chat router:
```python
from app.api.v1.documents import router as documents_router
app.include_router(documents_router, prefix="/v1", tags=["documents"])
```

- [ ] **Step 14.5: Run test — expect PASS**

```bash
pytest tests/integration/test_ingest_endpoint.py -v
# Expected: 3 passed
```

- [ ] **Step 14.6: Commit**

```bash
git add app/api/v1/documents.py app/main.py tests/integration/test_ingest_endpoint.py
git commit -m "feat: POST /v1/documents/ingest + GET status endpoint — duplicate detection, 50MB limit"
```

---

### Task 15: Seed script

**Files:**
- Create: `backend/scripts/seed_knowledge_base.py`

- [ ] **Step 15.1: Create `backend/scripts/seed_knowledge_base.py`**

```python
#!/usr/bin/env python3
"""
Seed the SONIQWERK RAG knowledge base from data/documents/.

Usage:
    python scripts/seed_knowledge_base.py            # ingest all PDFs
    python scripts/seed_knowledge_base.py --dry-run  # list files only
"""
from __future__ import annotations
import argparse
import asyncio
import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ingestion.pdf_loader import load_pdf
from app.rag.embeddings import embed_texts
from app.rag.collections import get_collection

DOC_DIRS: dict[str, str] = {
    "data/documents/manuals/":          "manuals",
    "data/documents/plugins_effects/":  "plugins",
    "data/documents/plugins_synths/":   "plugins",
    "data/documents/books/":            "books",
    "data/documents/articles/":         "articles",
}


async def seed(dry_run: bool = False) -> None:
    total_docs = 0
    total_chunks = 0

    for dir_path, category in DOC_DIRS.items():
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        pdfs = glob.glob(os.path.join(dir_path, "**/*.pdf"), recursive=True)

        for pdf_path in sorted(pdfs):
            title = Path(pdf_path).stem.replace("_", " ").replace("-", " ").title()
            print(f"  📄 {title}  [{category}]  ...", end=" ", flush=True)

            if dry_run:
                print("(dry-run)")
                total_docs += 1
                continue

            try:
                chunks = load_pdf(pdf_path, category, title)
                if not chunks:
                    print("⚠️  no text extracted")
                    continue

                texts = [c["text"] for c in chunks]
                embeddings = await embed_texts(texts)

                collection = get_collection(category)
                doc_slug = Path(pdf_path).stem.lower().replace(" ", "_")[:40]
                ids = [f"{doc_slug}_{i}" for i in range(len(chunks))]
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=[c["metadata"] for c in chunks],
                )
                total_docs += 1
                total_chunks += len(chunks)
                print(f"✅  {len(chunks)} chunks")

            except Exception as exc:
                print(f"❌  {exc}")

    print(f"\n{'DRY-RUN — ' if dry_run else ''}Done: {total_docs} documents, {total_chunks} chunks indexed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed SONIQWERK knowledge base")
    parser.add_argument("--dry-run", action="store_true", help="List PDFs without ingesting")
    args = parser.parse_args()
    asyncio.run(seed(dry_run=args.dry_run))
```

- [ ] **Step 15.2: Test dry-run**

```bash
cd backend
python scripts/seed_knowledge_base.py --dry-run
# Expected: lists PDFs found (0 if data/documents/ is empty) + "Done: N documents"
```

- [ ] **Step 15.3: Add PDFs and run full seed**

Place PDFs in `backend/data/documents/manuals/`, `plugins_effects/`, etc., then:
```bash
python scripts/seed_knowledge_base.py
# Expected per document: "✅  N chunks"
# Verify a collection is non-empty:
python3 -c "
from app.rag.collections import get_collection
col = get_collection('manuals')
print('manuals chunks:', col.count())
"
```

- [ ] **Step 15.4: Commit**

```bash
git add scripts/seed_knowledge_base.py
git commit -m "feat: seed script — batch ingest PDFs from data/documents/ with progress reporting"
```

---

### Task 16: Full test suite + final smoke test

- [ ] **Step 16.1: Run full test suite with coverage**

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
# Expected: all tests pass. Key modules coverage:
#   app/config.py         > 90%
#   app/rag/engine.py     > 80%
#   app/llm/router.py     > 85%
#   app/api/v1/chat.py    > 80%
```

- [ ] **Step 16.2: Start all services and run end-to-end smoke test**

```bash
# Terminal 1
docker-compose up -d

# Terminal 2
uvicorn app.main:app --reload --port 8000

# Terminal 3
celery -A workers.celery_app worker --loglevel=info

# Terminal 4 — smoke tests
API_KEY=$(grep API_SECRET_KEY .env | cut -d= -f2)

echo "--- Health ---"
curl http://localhost:8000/health

echo "--- Chat (RAG) ---"
curl -N -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Comment créer un Reese bass DnB dans Serum ?"}'

echo "--- Upload PDF ---"
curl -X POST http://localhost:8000/v1/documents/ingest \
  -H "X-API-Key: $API_KEY" \
  -F "file=@tests/fixtures/sample.pdf" \
  -F "category=plugins"
```

- [ ] **Step 16.3: Final commit**

```bash
git add .
git commit -m "feat: SONIQWERK Phase 1 — Backend RAG Core complete

- FastAPI 0.111 + Pydantic v2 config + X-API-Key auth
- SQLAlchemy 2.0 async + Alembic (conversations/messages/documents/ingestion_jobs)
- ChromaDB 0.5 embedded — 4 collections (manuals/plugins/books/articles)
- PDF loader: RecursiveCharacterTextSplitter (chunk=1000, overlap=200) + metadata
- RAG engine: MMR selection (fetch_k=30, lambda=0.7) + cross-encoder reranking
- Multi-LLM router: regex classifier → GPT-4o / Claude Sonnet 4.6 / GPT-4o-mini / Ollama
- POST /v1/chat — SSE streaming (chunk / sources / done events)
- POST /v1/documents/ingest — async Celery task + duplicate detection
- GET /v1/documents/ingest/{task_id}/status — Celery result polling
- Seed script: batch ingest PDFs from data/documents/
- 20+ tests: unit + integration, pytest-asyncio"
```
