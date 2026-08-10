# Context Store — Claude Code Instructions

## Project Overview
Aivaura Context Store MVP. AI-powered company intelligence platform with hybrid RAG.

## Tech Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy async, Celery, Redis
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind, Zustand
- **Storage**: PostgreSQL (Supabase), Redis (Upstash), Qdrant Cloud
- **AI**: Ollama (nomic-embed-text), Groq (llama-3.1-70b), LlamaIndex

## Commands

### Backend
```bash
cd backend
poetry install
cp .env.example .env  # fill in your values
poetry run uvicorn app.main:app --reload --port 8000

# Workers (separate terminals)
poetry run celery -A app.workers.celery_app worker --loglevel=info
poetry run celery -A app.workers.celery_app beat --loglevel=info

# MCP server (separate terminal)
poetry run python -m app.mcp.server

# DB migrations (if not using auto-create)
poetry run alembic upgrade head
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

### Ollama (required for embeddings)
```bash
# Install from ollama.com, then:
ollama pull nomic-embed-text
ollama pull llama3.2:3b  # optional, only if LLM_PROVIDER=ollama
```

## Default Login
- Email: admin@aivaura.com
- Password: changeme123

## File Structure
```
backend/app/
  main.py          — FastAPI app + lifespan
  config.py        — Pydantic settings
  database.py      — Async SQLAlchemy
  models/          — SQLAlchemy ORM models
  api/             — Route handlers
  connectors/      — Data source connectors (5)
  processing/      — Clean → chunk → embed → store
  retrieval/       — Hybrid search + reranker + query engine
  llm/             — Pluggable LLM (Groq/Anthropic/OpenAI/Ollama)
  mcp/             — MCP server (port 3001)
  workers/         — Celery tasks
frontend/src/
  app/             — Next.js pages (login, dashboard, ask, connectors, admin)
  components/      — UI components
  lib/             — API client, Zustand store
  types/           — TypeScript types
```

## Key Rules
1. Never commit .env files
2. All LLM calls must include the anti-hallucination system prompt
3. All API responses must follow {data, error} format
4. OAuth tokens must be Fernet-encrypted before DB storage
5. Rate limit: 60 queries/hour per user on /api/v1/query
