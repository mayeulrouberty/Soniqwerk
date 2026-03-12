# Soniqwerk

Chat with a local knowledge base about music production, or talk directly to Ableton Live.

Upload PDFs (plugin manuals, sound design books, whatever you want to query) and run RAG queries against them. There's also a LangChain agent connected to Ableton through a Max for Live bridge — it can create tracks, load instruments, write MIDI clips, automate parameters, manage device presets and search your sample library, all from a text prompt.

## What's in here

- **RAG chat** — PDFs in, answers out, with source citations. Works with Claude, GPT-4o, or local models via Ollama.
- **Ableton agent** — ReAct agent with ~23 LOM tools. Track management, MIDI writing, device control, scenes, automation, sample search/load, device preset snapshots.
- **Max for Live device** — drop `SONIQWERK.amxd` on any track to get a built-in chat panel without leaving Ableton.
- **WebSocket bridge** — the glue between the FastAPI backend and the M4L node.script.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + TypeScript + Vite + Tailwind |
| Backend | FastAPI + SSE streaming |
| RAG | LangChain + ChromaDB + text-embedding-3-large |
| LLM | Claude / GPT-4o / Ollama |
| Queue | Celery + Redis |
| DB | PostgreSQL + SQLAlchemy async |
| M4L | node.script + WebSocket + jsui |

## Architecture

```
Browser (:5173)          FastAPI (:8000)           Celery
      │                        │                       │
      ├─ POST /v1/chat ─SSE───▶│─ LangChain RAG        │
      ├─ POST /v1/documents ──▶│─ Celery task ─────────▶│── PDF→ChromaDB
      └─ POST /v1/agent ─SSE──▶│─ ReAct agent          │

                       WS bridge (:8001)
                               │
                        SONIQWERK.amxd
                               │
                      Ableton Live 11/12
```

## Requirements

- Python 3.9+
- Node.js 18+
- Docker (for Postgres + Redis)
- Ableton Live 11 or 12 with Max for Live (only needed for the agent)

## Setup

```bash
git clone https://github.com/mayeulrouberty/Soniqwerk.git
cd Soniqwerk

cp backend/.env.example backend/.env
# fill in OPENAI_API_KEY and API_SECRET_KEY

cp frontend/.env.example frontend/.env
# set VITE_API_KEY to match API_SECRET_KEY

# start postgres + redis
docker-compose up -d

# migrations
cd backend && python -m alembic upgrade head

# backend
uvicorn app.main:app --reload --port 8000

# celery worker (separate terminal)
celery -A workers.celery_app worker --loglevel=info

# ws bridge for ableton (separate terminal, optional)
python -m ws_bridge

# frontend (separate terminal)
cd ../frontend && npm install && npm run dev
```

Open http://localhost:5173.

## Ableton setup

See [ableton/README.md](ableton/README.md).

## Environment variables

Key ones — full list in `backend/.env.example`:

| Variable | What it does |
|----------|-------------|
| `OPENAI_API_KEY` | Required |
| `API_SECRET_KEY` | Auth header — set something strong |
| `DATABASE_URL` | Postgres connection string |
| `ANTHROPIC_API_KEY` | Optional, enables Claude |
| `SAMPLE_PATHS` | Colon-separated folders to index for sample search |

## Structure

```
Soniqwerk/
├── backend/
│   ├── app/           # routes, RAG engine, agent, config
│   ├── workers/       # celery tasks
│   ├── ws_bridge/     # websocket bridge (port 8001)
│   └── tests/         # unit tests (141 passing)
├── frontend/
│   └── src/           # React components, hooks, stores
├── ableton/           # M4L device + bridge + ui scripts
└── docs/              # specs and implementation plans
```

## License

MIT
