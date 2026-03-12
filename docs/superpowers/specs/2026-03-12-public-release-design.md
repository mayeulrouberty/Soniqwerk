# Public Release Cleanup — Design Spec

**Date:** 2026-03-12
**Sub-project:** A — Code cleanup + public repo
**Status:** Approved

---

## Goal

Prepare the Soniqwerk codebase for public release on `github.com/mayeulrouberty/Soniqwerk`. Ensure no sensitive data is exposed, the project is documented, and the docker-compose stack is production-ready.

## Scope

### 1. Security Audit

- Scan all git-tracked files for hardcoded secrets (API keys, tokens, passwords)
- Ensure `backend/.env` and `frontend/.env*` are in `.gitignore` (never committed)
- Create `backend/.env.example` with placeholder values
- Create `frontend/.env.example` with placeholder values
- Verify `conftest.py` uses only `test-secret` (non-sensitive test value — acceptable)

### 2. Root `.gitignore`

Single unified `.gitignore` at repo root covering:
- Python: `__pycache__/`, `*.pyc`, `.venv/`, `*.egg-info/`
- Node: `node_modules/`, `dist/`, `.tsbuildinfo`
- Environment: `.env`, `.env.local`, `.env.*.local`
- System: `.DS_Store`, `Thumbs.db`
- IDE: `.vscode/`, `.idea/`
- Build artifacts: `backend/data/chroma_db/`, `*.db`

### 3. Root `README.md`

Replace the current minimal README with a comprehensive one covering:
- Project description and demo screenshot placeholder
- Tech stack (FastAPI, React, LangChain, ChromaDB, Celery, Max for Live)
- Architecture overview (3 processes: API :8000, WS bridge :8001, Celery worker)
- Prerequisites (Python 3.9+, Node 18+, Docker, Ableton Live 11/12 + Max for Live)
- Quick start with Docker (`docker-compose up`)
- Manual setup instructions (backend, frontend, Ableton device)
- Environment variables reference (points to `.env.example`)
- Project structure overview

### 4. Frontend Polish

- `frontend/README.md`: replace Vite template with Soniqwerk-specific content
- Plugins tab (`App.tsx`): render a clean "Coming soon" card instead of empty div
- Ableton tab (`App.tsx`): render a clean "Connect the Max for Live device to get started" card

### 5. CORS Configuration

In `backend/app/config.py`:
- Replace hardcoded `localhost` CORS origins with env var `CORS_ORIGINS` (comma-separated string)
- Default value: `"http://localhost:5173,http://localhost:3000"` (safe for development)
- Parse into list on app startup

### 6. Docker Compose

In `docker-compose.yml`:
- Verify all 5 services defined: `postgres`, `redis`, `chromadb`, `api`, `celery`
- Add `healthcheck` to postgres and redis
- Add `depends_on` with `condition: service_healthy` for api and celery
- Ensure all env vars reference `.env` file via `env_file: .env`
- Expose only necessary ports externally

### 7. New Public Repo

```bash
# Create new public repo (no init — we push our own history)
gh repo create mayeulrouberty/Soniqwerk --public --description "AI music production assistant with RAG chat and Ableton Live agent"

# Push phase-3-ableton as main
git remote add public https://github.com/mayeulrouberty/Soniqwerk.git
git push public phase-3-ableton:main
```

Only `main` is pushed publicly. Internal branches (`phase-1-backend-rag`, `phase-4-frontend`, `HackathonToulonV1`) stay local only.

## Files Created/Modified

| File | Action |
|------|--------|
| `README.md` | Replace with comprehensive project README |
| `.gitignore` | Unified root gitignore |
| `backend/.env.example` | New — placeholder env vars |
| `frontend/.env.example` | New — placeholder env vars |
| `frontend/README.md` | Replace Vite template |
| `frontend/src/App.tsx` | Polish placeholder tabs |
| `backend/app/config.py` | CORS from env var |
| `docker-compose.yml` | Health checks + env_file |

## Security Checklist (must pass before push)

- [ ] No `.env` files in git history
- [ ] No API keys in any tracked file
- [ ] `backend/.env.example` contains only placeholder values
- [ ] `frontend/.env.example` contains only placeholder values
- [ ] `.gitignore` covers all env file patterns

## Non-Goals

- CI/CD pipeline (Phase 5)
- Production deployment (Heroku/AWS)
- Rate limiting / JWT auth (Phase 5)
- E2E tests (Phase 5)
