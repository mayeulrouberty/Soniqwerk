# SONIQWERK

AI-powered music production assistant — RAG chat + Ableton Live agent.

Ask questions about music production from your own document library (manuals, plugin documentation, books), and control Ableton Live 11/12 via a natural language agent.

## Features

- **RAG Chat** — Upload PDFs, ask questions, get answers with source citations. Supports Claude, GPT-4o, and local models via Ollama.
- **Document Library** — Drag-and-drop PDF upload with async ingestion (Celery + ChromaDB).
- **Ableton Live Agent** — LangChain ReAct agent with Live Object Model tools. Control tracks, devices, parameters, and clips via text commands.
- **WebSocket Bridge** — Max for Live device bridges the backend to Ableton Live's LOM.
- **Voice Input** — Dictate chat messages via Web Speech API (Chrome/Edge, fr/en).

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS + Zustand |
| Backend API | FastAPI (Python 3.9) + SSE streaming |
| RAG | LangChain + ChromaDB + text-embedding-3-large + cross-encoder reranking |
| LLM | Claude (Anthropic) / GPT-4o / GPT-4o-mini / Ollama |
| Queue | Celery + Redis |
| Database | PostgreSQL 16 + SQLAlchemy async |
| Ableton | Max for Live node.script + WebSocket bridge |

## Architecture

Three independent processes:

```
Browser (React :5173)      Backend (FastAPI :8000)      Workers
        │                          │                        │
        │──POST /v1/chat──SSE────▶│──LangChain RAG          │
        │──POST /v1/documents────▶│──Celery task───────────▶│──PDF→ChromaDB
        │──POST /v1/agent──SSE───▶│──ReAct agent            │
                                   │
                          WS Bridge (:8001)
                                   │
                          Max for Live (.amxd)
                                   │
                          Ableton Live 11/12
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Ableton Live 11 or 12 + Max for Live (for Ableton agent only)

## Quick Start

```bash
# 1. Clone
git clone https://github.com/mayeulrouberty/Soniqwerk.git
cd Soniqwerk

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env — add your OpenAI API key and set a strong API_SECRET_KEY

cp frontend/.env.example frontend/.env
# Edit frontend/.env — set VITE_API_KEY to match API_SECRET_KEY above

# 3. Start infrastructure services
docker-compose up -d

# 4. Run database migrations
cd backend && python -m alembic upgrade head

# 5. Start backend API
uvicorn app.main:app --reload --port 8000

# 6. Start Celery worker (new terminal)
celery -A workers.celery_app worker --loglevel=info

# 7. Start WebSocket bridge for Ableton (new terminal, optional)
python -m ws_bridge

# 8. Start frontend (new terminal)
cd ../frontend && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## Ableton Live Setup

See [ableton/README.md](ableton/README.md) for Max for Live device setup instructions.

## Environment Variables

See `backend/.env.example` for the full list. Key variables:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (required) |
| `API_SECRET_KEY` | Shared API key for X-API-Key header — change in production |
| `DATABASE_URL` | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional, enables Claude) |

## Project Structure

```
Soniqwerk/
├── backend/           # FastAPI + RAG + Celery + WS bridge
│   ├── app/           # API routes, RAG engine, LLM router, agent
│   ├── workers/       # Celery tasks
│   ├── ws_bridge/     # WebSocket bridge server (port 8001)
│   └── tests/         # Unit + integration tests (82 passing)
├── frontend/          # React + TypeScript + Vite
│   └── src/
│       ├── components/   # UI components
│       ├── hooks/        # useSSE, useUpload, useVoice
│       └── stores/       # Zustand state
├── ableton/           # Max for Live bridge script
└── docs/              # Architecture diagrams and specs
```

## License

MIT
