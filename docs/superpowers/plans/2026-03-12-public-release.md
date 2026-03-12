# Public Release Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare Soniqwerk for public release on `github.com/mayeulrouberty/Soniqwerk` — security audit, proper README, .gitignore, docker-compose, and a clean push of the main branch.

**Architecture:** No code logic changes. Pure housekeeping: security scan, documentation, configuration polish, and git/GitHub operations. No tests required (nothing executable to test).

**Tech Stack:** git, GitHub CLI (`gh`), bash, Docker Compose v3.9

---

## Chunk 1: Security + gitignore

### Task 1: Security audit + root .gitignore

**Files:**
- Create: `.gitignore` (root)

**Critical:** No `.env` file with real credentials must ever be pushed. The current `backend/.env` contains `OPENAI_API_KEY=test` (not a real key) and `API_SECRET_KEY=test-secret` (test value). These are safe but we still must ensure they are never committed.

- [ ] **Step 1: Scan for hardcoded secrets**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
# Search for patterns that look like real API keys
git ls-files | xargs grep -l "sk-" 2>/dev/null
git ls-files | xargs grep -l "sk-ant-" 2>/dev/null
git ls-files | xargs grep -l "Bearer " 2>/dev/null
```

Expected: no files match (test values like `sk-...` in `.env.example` are placeholders, not real keys)

- [ ] **Step 2: Verify .env files are NOT tracked**

```bash
git ls-files | grep "\.env$"
```

Expected: empty output (only `.env.example` files should be tracked)

- [ ] **Step 3: Create root `.gitignore`**

Create `/Users/charlotte/Desktop/Soniqwerk/.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage

# Node
node_modules/
dist/
.next/
*.tsbuildinfo

# Environment — NEVER commit real credentials
.env
.env.local
.env.*.local
.env.production

# Databases & build artifacts
backend/data/chroma_db/
*.db
*.sqlite3

# System
.DS_Store
Thumbs.db
*.swp
*.swo

# IDE
.vscode/
.idea/
*.sublime-project

# Logs
*.log
npm-debug.log*

# Test artifacts
coverage/
```

- [ ] **Step 4: Verify .env files are now ignored**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git check-ignore -v backend/.env frontend/.env
```

Expected: both files shown as ignored by the new `.gitignore`

- [ ] **Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: add root .gitignore covering Python, Node, env, and system files"
```

---

## Chunk 2: Documentation

### Task 2: Root README.md

**Files:**
- Create: `README.md` (root — currently empty/missing)

- [ ] **Step 1: Create `README.md`**

Create `/Users/charlotte/Desktop/Soniqwerk/README.md`:

```markdown
# SONIQWERK

AI-powered music production assistant — RAG chat + Ableton Live agent.

Ask questions about music production from your own document library (manuals, books, sample packs documentation), and control Ableton Live 11/12 via a natural language agent.

## Features

- **RAG Chat** — Upload PDFs, ask questions, get answers with source citations. Supports Claude, GPT-4o, and local models via Ollama.
- **Document Library** — Drag-and-drop PDF upload with async ingestion (Celery + ChromaDB).
- **Ableton Live Agent** — LangChain ReAct agent with 6 Live Object Model tools. Control tracks, devices, parameters, and clips via text commands.
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
Browser (React)          Backend (FastAPI :8000)       Workers
     │                        │                            │
     │──POST /v1/chat──SSE──▶│──LangChain RAG             │
     │──POST /v1/documents───▶│──Celery task──────────────▶│──PDF→ChromaDB
     │──POST /v1/agent──SSE──▶│──ReAct agent               │
                               │                            │
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

## Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/mayeulrouberty/Soniqwerk.git
cd Soniqwerk

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env — add your OpenAI API key and set API_SECRET_KEY

cp frontend/.env.example frontend/.env
# Edit frontend/.env — set VITE_API_KEY to match API_SECRET_KEY above

# 3. Start infrastructure
docker-compose up -d

# 4. Run database migrations
cd backend && python -m alembic upgrade head

# 5. Start backend
uvicorn app.main:app --reload --port 8000

# 6. Start WebSocket bridge (Ableton only)
python -m ws_bridge

# 7. Start Celery worker
celery -A workers.celery_app worker --loglevel=info

# 8. Start frontend
cd frontend && npm install && npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## Ableton Live Setup

See [ableton/README.md](ableton/README.md) for Max for Live device setup instructions.

## Environment Variables

See `backend/.env.example` for the full list with descriptions.

Key variables:
| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (required) |
| `API_SECRET_KEY` | Shared API key for X-API-Key header |
| `DATABASE_URL` | PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) |

## Project Structure

```
Soniqwerk/
├── backend/          # FastAPI + RAG + Celery + WS bridge
│   ├── app/          # API routes, RAG engine, LLM router, agent
│   ├── workers/      # Celery tasks
│   ├── ws_bridge/    # WebSocket bridge server
│   └── tests/        # Unit + integration tests
├── frontend/         # React + TypeScript + Vite
│   └── src/
│       ├── components/  # UI components
│       ├── hooks/       # useSSE, useUpload, useVoice
│       └── stores/      # Zustand state
├── ableton/          # Max for Live bridge script
└── docs/             # Architecture diagrams and specs
```

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add README.md
git commit -m "docs: add comprehensive root README for public release"
```

---

### Task 3: Frontend README + placeholder polish

**Files:**
- Modify: `frontend/README.md`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Replace frontend README**

Replace `frontend/README.md` with:

```markdown
# SONIQWERK — Frontend

React 18 + TypeScript + Vite + Tailwind CSS

## Dev

```bash
cp .env.example .env   # set VITE_API_KEY
npm install
npm run dev            # http://localhost:5173
```

## Build

```bash
npm run build
```

## Stack

- React 18 + TypeScript (strict)
- Vite 5 + Tailwind CSS v4
- Zustand (state management)
- Axios + Zod (API client + validation)
- shadcn/ui (component library)
- lucide-react + react-icons (icons)
```

- [ ] **Step 2: Polish AbletonPlaceholder in App.tsx**

Replace the `AbletonPlaceholder` function in `frontend/src/App.tsx`:

```tsx
function AbletonPlaceholder() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center max-w-sm">
        <h2 className="font-display text-3xl text-accent mb-3">Ableton Live</h2>
        <p className="text-muted text-sm mb-4">
          Connect the Max for Live device to control your session via AI.
        </p>
        <p className="text-xs text-muted/60 font-mono">
          See <span className="text-accent/80">ableton/README.md</span> for setup instructions.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git add frontend/README.md frontend/src/App.tsx
git commit -m "docs: update frontend README and polish Ableton placeholder"
```

---

## Chunk 3: Docker Compose + GitHub push

### Task 4: Complete docker-compose.yml at root

**Files:**
- Create: `docker-compose.yml` (root)

Note: `backend/docker-compose.yml` exists but only has postgres + redis and is inside `backend/`. We create a complete root-level one.

- [ ] **Step 1: Create root `docker-compose.yml`**

Create `/Users/charlotte/Desktop/Soniqwerk/docker-compose.yml`:

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: soniqwerk
      POSTGRES_PASSWORD: soniqwerk
      POSTGRES_DB: soniqwerk
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U soniqwerk"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8002:8000"
    volumes:
      - chroma_data:/chroma/chroma
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
  chroma_data:
```

Note: The API and Celery worker are started manually (not in docker-compose) for development. The compose file manages only infrastructure services.

- [ ] **Step 2: Verify docker-compose syntax**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
docker-compose config --quiet && echo "✅ Valid"
```

Expected: `✅ Valid`

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: add root docker-compose for infrastructure services (postgres, redis, chromadb)"
```

---

### Task 5: Create public GitHub repo and push

**IMPORTANT:** This pushes code publicly. Verify the security checklist before running any push command.

- [ ] **Step 1: Final security check before push**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
# Verify no real API keys in tracked files
git ls-files | xargs grep -rn "sk-[a-zA-Z0-9]\{20,\}" 2>/dev/null | grep -v ".env.example" | grep -v "test"
```

Expected: **empty output** — if anything is shown, STOP and investigate before continuing.

```bash
# Verify .env files are not tracked
git ls-files | grep "\.env$"
```

Expected: **empty output**

- [ ] **Step 2: Create the GitHub repo**

```bash
gh repo create mayeulrouberty/Soniqwerk \
  --public \
  --description "AI music production assistant — RAG chat + Ableton Live agent" \
  --homepage "" \
  --confirm
```

Expected: repo created at `https://github.com/mayeulrouberty/Soniqwerk`

- [ ] **Step 3: Add remote and push**

```bash
cd /Users/charlotte/Desktop/Soniqwerk
git remote add public https://github.com/mayeulrouberty/Soniqwerk.git
git push public phase-3-ableton:main
```

Expected: push succeeds, branch `phase-3-ableton` becomes `main` on the public repo

- [ ] **Step 4: Verify on GitHub**

```bash
gh repo view mayeulrouberty/Soniqwerk --web
```

Check that:
- README is visible on the repo homepage
- No `.env` files appear in the file tree
- The commit history looks clean

- [ ] **Step 5: Set default branch (if needed)**

```bash
gh api repos/mayeulrouberty/Soniqwerk \
  --method PATCH \
  -f default_branch=main
```
