# SONIQWERK — Design Document
**Date :** 2026-03-10
**Version :** 2.0
**Statut :** Approuvé

---

## Vue d'ensemble

SONIQWERK est un agent IA pour la production et le mixage de musique électronique. Il combine un pipeline RAG sur une base de connaissance audio (manuels DAW, plugins, livres) avec un agent autonome capable de contrôler Ableton Live via Max for Live.

**Priorité de développement :**
1. **Phase 1–2** : Backend RAG + Frontend React (MVP chat audio expert)
2. **Phase 3–5** : Agent Ableton + Scaling production

---

## Architecture — Approche B (FastAPI Modulaire)

Monorepo avec 3 processus distincts qui scalent indépendamment :

| Processus | Port | Rôle |
|-----------|------|------|
| `uvicorn app.main:app` | 8000 | API REST + SSE streaming |
| `celery -A workers.celery_app worker` | — | Ingestion PDF async |
| `uvicorn ws_bridge:app` | 8001 | WebSocket Ableton (Phase 2) |

### Structure du projet

```
Soniqwerk/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                # Pydantic v2 Settings
│   │   ├── api/v1/
│   │   │   ├── chat.py              # POST /v1/chat — SSE
│   │   │   ├── documents.py         # POST /v1/documents/ingest
│   │   │   └── analysis.py          # POST /v1/analysis/ableton
│   │   ├── rag/
│   │   │   ├── engine.py            # MMR + cross-encoder reranking
│   │   │   ├── embeddings.py        # text-embedding-3-large
│   │   │   └── collections.py       # ChromaDB multi-collections
│   │   ├── ingestion/
│   │   │   ├── pdf_loader.py        # Chunking + métadonnées
│   │   │   └── pipeline.py          # Celery task
│   │   ├── llm/
│   │   │   ├── router.py            # Classifier regex + embeddings
│   │   │   ├── providers.py         # GPT-4o / Claude / GPT-4o-mini / Ollama
│   │   │   └── prompts.py           # System prompts domaine audio
│   │   ├── agent/                   # Phase 2
│   │   └── integrations/            # Phase 2
│   ├── workers/celery_app.py
│   ├── data/documents/              # PDFs source
│   ├── scripts/seed_knowledge_base.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/              # Sidebar, Header
│   │   │   ├── chat/                # ChatWindow, MessageBubble, StreamingMessage, InputBar
│   │   │   ├── documents/           # DocumentLibrary, DropZone
│   │   │   └── plugins/             # PluginExplorer
│   │   ├── stores/                  # Zustand : chatStore, documentsStore, uiStore
│   │   ├── hooks/                   # useSSE, useUpload
│   │   ├── lib/api.ts               # Axios typé + Zod
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   ├── architecture.html
│   ├── design-prototype.html
│   └── superpowers/specs/
└── docker-compose.yml
```

---

## Pipeline RAG

### Ingestion (Celery async)
```
PDF → RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
    → Métadonnées (catégorie, source, pages)
    → text-embedding-3-large
    → ChromaDB (4 collections : manuals, plugins, books, articles)
```

### Query time
```
Question → Embedding requête
         → MMR Retrieval (fetch_k=30, λ=0.7)
         → Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2)
         → Top-4 chunks
         → Context Builder (+ ConversationBufferWindowMemory 10 turns)
         → LLM Router → SSE stream
```

**Différenciant clé :** le reranker cross-encoder re-score les 30 candidats MMR, éliminant les faux positifs sémantiques courants sur le vocabulaire audio (ex : "compression" peut être audio ou données).

---

## LLM Router

Classifier lightweight (regex + cosine similarity sur embeddings labelisés) — pas de LLM pour classifier afin d'éviter latence et coût.

| Pattern détecté | Modèle | Raison |
|----------------|--------|--------|
| Créatif : ambiance, texture, timbre, feel | `claude-sonnet-4-6` | Meilleur raisonnement nuancé |
| Technique : routing, paramètre, config, LUFS | `gpt-4o` | Meilleur instruction-following |
| FAQ courte (< 30 tokens), définitions | `gpt-4o-mini` | 10x moins cher, latence < 500ms |
| Mode offline / sans clé API | `ollama` (llama3.2) | Privacy-first |

**Fallback :** GPT-4o timeout → retry GPT-4o-mini. Claude indisponible → GPT-4o.

---

## Frontend — React + TypeScript + Tailwind + shadcn/ui

### Stack
- **Build** : Vite 5
- **UI** : React 18 + TypeScript + Tailwind CSS + shadcn/ui (thème dark custom)
- **État** : Zustand
- **Requêtes** : Axios + Zod (validation runtime)
- **SSE** : hook `useSSE` natif EventSource

### Design System
Basé sur le prototype `docs/design-prototype.html` :
- Couleurs : `#06050b` (bg), `#ff6b35` (accent orange), `#00f5a0` (green)
- Polices : Bebas Neue (display) + Outfit (UI) + JetBrains Mono (data)
- Transposés en variables Tailwind via `tailwind.config.ts`

### Stores Zustand

```typescript
// chatStore
{ messages, isStreaming, currentModel, sendMessage, appendChunk, setModel }

// documentsStore
{ documents, uploadQueue, ingest, pollStatus }

// uiStore
{ activeView, vuActive, sidebarOpen }
```

### SSE Pattern
```typescript
// Chunks appendés en temps réel, sources envoyées en event final
useSSE(url, { onChunk, onSources, onDone, onError })
```

---

## Error Handling

### Backend
```python
# Exceptions custom
class RAGError(Exception): ...        # ChromaDB indisponible
class LLMTimeoutError(Exception): ... # Provider > 30s
class IngestError(Exception): ...     # PDF corrompu

# Fallback LLM automatique sur timeout
```

### Frontend
- SSE `onError` → toast + bouton "Réessayer"
- Upload → retry x3 backoff exponentiel
- Connexion perdue → reconnexion SSE automatique

---

## Tests

### Backend (pytest + pytest-asyncio)
```
tests/
├── unit/
│   ├── test_rag_engine.py       # MMR retrieval, scores reranking
│   ├── test_llm_router.py       # Classifier → bon modèle
│   └── test_pdf_loader.py       # Chunking, métadonnées
├── integration/
│   ├── test_chat_endpoint.py    # SSE end-to-end
│   └── test_ingest_pipeline.py  # Upload → Celery → ChromaDB
└── fixtures/
    ├── sample.pdf
    └── mock_llm_responses.json
```

### Frontend (Vitest + Testing Library)
- `ChatWindow` : render, append chunks streaming
- `InputBar` : send, raccourcis clavier, attach fichier
- `DocumentLibrary` : upload progress, status polling

### E2E Phase 5
Playwright — scénario question → réponse streamée complète.

---

## Déploiement

### Dev
```bash
docker-compose up                                    # postgres + redis + chromadb
uvicorn app.main:app --reload --port 8000
celery -A workers.celery_app worker --loglevel=info
cd frontend && npm run dev
```

### Docker-compose prod (Phase 5)
```yaml
services:
  api:      { build: ./backend, scale: 2 }   # stateless → horizontal scaling
  worker:   { build: ./backend }
  postgres: { image: postgres:16-alpine }
  redis:    { image: redis:7-alpine }
  chroma:   { image: chromadb/chroma }
  frontend: { build: ./frontend }             # nginx static
```

---

## Authentification (Phase 1 → Phase 5)

**Phase 1 (immédiat) :** middleware `X-API-Key` — clé partagée via env var `API_SECRET_KEY`. Bloque toutes les routes si absente. Simple à implémenter, suffisant pour dev local / instances non publiques.

**Phase 5 :** JWT Bearer tokens + rate limiting Redis par user.

```python
# app/api/deps.py
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(status_code=401)
```

---

## Modèles de données (PostgreSQL)

```sql
-- Conversations
conversations (id UUID PK, created_at, model TEXT, metadata JSONB)

-- Messages
messages (id UUID PK, conversation_id FK, role TEXT, content TEXT,
          sources JSONB, model_used TEXT, tokens_used INT, created_at)

-- Documents ingérés
documents (id UUID PK, filename TEXT, category TEXT, status TEXT,
           chunks_count INT, file_hash TEXT, ingested_at)

-- Jobs Celery
ingestion_jobs (id UUID PK, document_id FK, celery_task_id TEXT,
                status TEXT, error TEXT, created_at, updated_at)
```

**Allocation Redis :**
| DB | Usage |
|----|-------|
| 0 | Cache sessions + API |
| 1 | Celery broker (tasks ingestion) |
| 2 | Celery results backend |
| 3 | ConversationBufferWindowMemory (10 turns / conversation) |

---

## Contrats API

### `POST /v1/chat` — SSE Stream

**Request :**
```json
{
  "message": "Comment faire un Reese bass dans Serum ?",
  "conversation_id": "uuid-optionnel",
  "model_override": "claude-sonnet-4-6"
}
```

**SSE Events (wire format) :**
```
event: chunk
data: {"text": "Un Reese bass est...", "conversation_id": "uuid"}

event: sources
data: {"sources": [{"title": "Serum Manual", "category": "plugin", "score": 0.94}]}

event: done
data: {"model_used": "claude-sonnet-4-6", "tokens": 412, "conversation_id": "uuid"}

event: error
data: {"code": "LLM_TIMEOUT", "message": "Provider unavailable, retrying..."}
```

### `POST /v1/documents/ingest`

**Request :** `multipart/form-data` — `file: File`, `category: str`

**Response :**
```json
{ "task_id": "celery-uuid", "document_id": "db-uuid", "status": "queued" }
```

### `GET /v1/documents/ingest/{task_id}/status`

**Response :**
```json
{ "status": "processing|ready|error", "chunks_count": 1830, "error": null }
```

---

## Design System (palette canonique)

Le **prototype UI** (`docs/design-prototype.html`) définit la palette produit. La documentation (`docs/architecture.html`) utilise une palette distincte pour les diagrammes. Ne pas mélanger.

**Tailwind config produit (`tailwind.config.ts`) :**
```typescript
colors: {
  bg:      '#06050b',
  surface: '#0d0c16',
  border:  '#1c1a2e',
  accent:  '#ff6b35',   // orange — accent principal
  green:   '#00f5a0',   // statut connecté
  text:    '#edeaf0',
  muted:   '#8e8aaa',
}
```

---

## Variables d'environnement

```bash
OPENAI_API_KEY=...
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
ANTHROPIC_API_KEY=...
API_SECRET_KEY=...                    # clé partagée Phase 1
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
CHROMA_PERSIST_DIR=./data/chroma_db
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LLM_PROVIDER=multi                    # openai | anthropic | multi | ollama
OLLAMA_MODEL=llama3.2:8b              # taille recommandée pour prod audio
RAG_TOP_K=8
RAG_FETCH_K=30
USE_RERANKER=true
ABLETON_WS_PORT=8001
```

---

## Phases de développement

| Phase | Contenu | Durée |
|-------|---------|-------|
| 1 | Backend RAG Core (FastAPI + ChromaDB + Celery + /v1/chat SSE) | Sem. 1–2 |
| 2 | Analyse DAW & Audio (ableton_parser, preset_parser, audio_analyzer) | Sem. 3 |
| 3 | Agent Ableton + Max for Live (WebSocket bridge, ReAct Agent, 6 tools) | Sem. 4–5 |
| 4 | Frontend React (ChatWindow SSE, DocumentLibrary, PluginExplorer) | Sem. 5–6 |
| 5 | Production & Scaling (Docker prod, CI/CD, Prometheus, Auth JWT, E2E) | Sem. 7–8 |

---

## Références
- `docs/architecture.html` — 7 diagrammes Mermaid (architecture, RAG, Ableton, Agent, LLM Router, Infra, User Flow)
- `docs/design-prototype.html` — Prototype UI interactif complet
- `Downloads/SONIQWERK_CLAUDE_CODE_PROMPT_V2.md` — Spécification technique source
