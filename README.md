# Soniqwerk

Chat avec une base de connaissances locale sur la production musicale, ou parle directement à Ableton Live.

Tu peux uploader des PDFs (manuels de plugins, livres de sound design, n'importe quoi) et poser des questions dessus via RAG. Il y a aussi un agent LangChain connecté à Ableton via un bridge Max for Live — il peut créer des tracks, charger des instruments, écrire des clips MIDI, automatiser des paramètres, gérer des presets et chercher dans ta sample library, tout ça depuis un prompt texte.

## Ce qu'il y a dedans

- **Chat RAG** — les PDFs rentrent, les réponses sortent avec leurs sources. Fonctionne avec Claude, GPT-4o ou des modèles locaux via Ollama.
- **Agent Ableton** — agent ReAct avec ~23 outils LOM. Gestion des tracks, écriture MIDI, contrôle des devices, scènes, automation, search de samples, snapshots de presets.
- **Device Max for Live** — glisse `SONIQWERK.amxd` sur n'importe quelle track pour avoir un panel de chat intégré sans quitter Ableton.
- **Bridge WebSocket** — la colle entre le backend FastAPI et le node.script M4L.

## Stack

| Couche | Tech |
|--------|------|
| Frontend | React 18 + TypeScript + Vite + Tailwind |
| Backend | FastAPI + SSE streaming |
| RAG | LangChain + ChromaDB + text-embedding-3-large |
| LLM | Claude / GPT-4o / Ollama |
| Queue | Celery + Redis |
| BDD | PostgreSQL + SQLAlchemy async |
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

## Prérequis

- Python 3.9+
- Node.js 18+
- Docker (pour Postgres + Redis)
- Ableton Live 11 ou 12 avec Max for Live (seulement pour l'agent)

## Installation

```bash
git clone https://github.com/mayeulrouberty/Soniqwerk.git
cd Soniqwerk

cp backend/.env.example backend/.env
# remplir OPENAI_API_KEY et API_SECRET_KEY

cp frontend/.env.example frontend/.env
# VITE_API_KEY doit correspondre à API_SECRET_KEY

# démarrer postgres + redis
docker-compose up -d

# migrations
cd backend && python -m alembic upgrade head

# backend
uvicorn app.main:app --reload --port 8000

# worker celery (terminal séparé)
celery -A workers.celery_app worker --loglevel=info

# bridge WS pour ableton (terminal séparé, optionnel)
python -m ws_bridge

# frontend (terminal séparé)
cd ../frontend && npm install && npm run dev
```

Ouvrir http://localhost:5173.

## Setup Ableton

Voir [ableton/README.md](ableton/README.md).

## Variables d'environnement

Les principales — liste complète dans `backend/.env.example` :

| Variable | Rôle |
|----------|------|
| `OPENAI_API_KEY` | Requis |
| `API_SECRET_KEY` | Header d'auth — mettre quelque chose de solide |
| `DATABASE_URL` | Connexion Postgres |
| `ANTHROPIC_API_KEY` | Optionnel, active Claude |
| `SAMPLE_PATHS` | Dossiers séparés par `:` pour la recherche de samples |

## Structure

```
Soniqwerk/
├── backend/
│   ├── app/           # routes, RAG, agent, config
│   ├── workers/       # tâches celery
│   ├── ws_bridge/     # bridge websocket (port 8001)
│   └── tests/         # tests unitaires (141 passants)
├── frontend/
│   └── src/           # composants React, hooks, stores
├── ableton/           # device M4L + bridge + scripts ui
└── docs/              # specs et plans d'implémentation
```

## Licence

MIT
