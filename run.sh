#!/bin/bash
# SONIQWERK — One-command launcher
# Usage: ./run.sh
# Stop:  Ctrl+C

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[SONIQWERK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
die()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Track background PIDs for cleanup
PIDS=()
cleanup() {
    echo ""
    log "Shutting down all services..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    log "All services stopped. Bye!"
}
trap cleanup EXIT INT TERM

# ── 1. Check prerequisites ──────────────────────────────────────────────────
log "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Python 3.9+ from https://python.org"
command -v node    >/dev/null 2>&1 || die "node not found. Install Node.js 18+ from https://nodejs.org"
command -v docker  >/dev/null 2>&1 || warn "docker not found — skipping infrastructure (postgres/redis/chromadb)"

PYTHON=python3

# ── 2. Backend virtual environment ─────────────────────────────────────────
log "Setting up Python environment..."
if [ ! -d "backend/venv" ]; then
    log "Creating virtual environment..."
    $PYTHON -m venv backend/venv
fi
source backend/venv/bin/activate

log "Installing backend dependencies..."
pip install -q -r backend/requirements.txt

# ── 3. Check .env files ─────────────────────────────────────────────────────
if [ ! -f "backend/.env" ]; then
    warn "backend/.env not found — copying from .env.example"
    cp backend/.env.example backend/.env
    warn "Edit backend/.env and add your OPENAI_API_KEY, then re-run this script."
    exit 1
fi
if [ ! -f "frontend/.env" ]; then
    warn "frontend/.env not found — copying from .env.example"
    cp frontend/.env.example frontend/.env
fi

# ── 4. Start infrastructure (Docker) ───────────────────────────────────────
if command -v docker >/dev/null 2>&1; then
    log "Starting infrastructure (PostgreSQL, Redis, ChromaDB)..."
    docker compose up -d 2>/dev/null || docker-compose up -d 2>/dev/null || warn "docker compose failed — make sure Docker Desktop is running"
    log "Waiting for services to be ready..."
    sleep 4
else
    warn "Docker not available — skipping infrastructure services."
    warn "Make sure PostgreSQL and Redis are running manually."
fi

# ── 5. Database migrations ──────────────────────────────────────────────────
log "Running database migrations..."
cd backend
python -m alembic upgrade head 2>/dev/null || warn "Migrations failed — database may not be ready yet"
cd "$SCRIPT_DIR"

# ── 6. Start backend API ────────────────────────────────────────────────────
log "Starting backend API on http://localhost:8000 ..."
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/soniqwerk_api.log 2>&1 &
PIDS+=($!)
cd "$SCRIPT_DIR"

# ── 7. Start WebSocket bridge ───────────────────────────────────────────────
log "Starting Ableton WebSocket bridge on port 8001..."
cd backend
python -m ws_bridge > /tmp/soniqwerk_bridge.log 2>&1 &
PIDS+=($!)
cd "$SCRIPT_DIR"

# ── 8. Start Celery worker ──────────────────────────────────────────────────
log "Starting Celery worker..."
cd backend
celery -A workers.celery_app worker --loglevel=warning > /tmp/soniqwerk_celery.log 2>&1 &
PIDS+=($!)
cd "$SCRIPT_DIR"

# ── 9. Frontend dependencies ────────────────────────────────────────────────
log "Installing frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install --silent
fi

# ── 10. Start frontend ──────────────────────────────────────────────────────
log "Starting frontend on http://localhost:5173 ..."
npm run dev > /tmp/soniqwerk_frontend.log 2>&1 &
PIDS+=($!)
cd "$SCRIPT_DIR"

# ── 11. Ready ───────────────────────────────────────────────────────────────
sleep 3
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  SONIQWERK is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  App:     ${GREEN}http://localhost:5173${NC}"
echo -e "  API:     http://localhost:8000/docs"
echo -e "  Logs:    /tmp/soniqwerk_*.log"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services."
echo ""

# Wait for all background processes
wait
