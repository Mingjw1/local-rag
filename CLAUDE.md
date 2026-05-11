# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local RAG Knowledge Base MVP — a fully local RAG (Retrieval-Augmented Generation) system. Documents are ingested through a parser → chunking → embedding pipeline, stored in Qdrant vector DB, and searched via Ollama-powered semantic search + LLM generation. Includes an LLM Wiki engine that auto-generates structured markdown knowledge bases from ingested documents.

**Stack**: Python 3.12+ / FastAPI / SQLAlchemy async / asyncpg | React 18 / TypeScript / Vite / Tailwind CSS | Qdrant / PostgreSQL 16 / Redis 7 / MinIO | Ollama (local LLM, GPU accelerated via ROCm)

## Architecture

```
app/
  core/          — Config (pydantic-settings from YAML + env vars), Pydantic models, Ollama async HTTP client
  db/            — SQLAlchemy async models (KnowledgeBase, Document, Chunk, AuditLog), Qdrant client, DB session
  pipeline/      — Document parsing (md/txt/pdf/docx/html/xlsx/csv), chunking (recursive/semantic/code-aware), embedding, query/search
  routers/       — FastAPI routes: documents (CRUD + upload), search/query (RAG + SSE streaming), admin (health/models/config), wiki (pages/lint)
  wiki/          — LLM Wiki engine: auto-generates/updates markdown pages per KB after ingest, lint checks (orphans, broken links, index consistency)
frontend/        — React SPA (Vite/TypeScript), 3 tabs: search/QA, documents, wiki. Flat source tree (~5 files).
config/          — YAML config: models registry, RAG controller, retrieval strategies
scripts/         — docker compose setup, seed data, model pulling, functional test
data/            — Runtime data: wiki markdown files, uploaded documents, Qdrant snapshots
docs/            — commands.md (CLI quick reference), ops-manual.md (operational guide)
tests/           — Unit tests for chunking, parsers, wiki engine
```

### Data Flow

1. **Upload**: User uploads document → saved to disk → `Document` row created in PostgreSQL (status: pending)
2. **Ingest**: `process_document()` → parse file → chunk text → embed via Ollama → upsert vectors to Qdrant → store chunks in PostgreSQL → update KB stats → trigger Wiki engine
3. **Search**: User query → embed query → vector search in Qdrant (with KB filter) → return ranked results
4. **QA**: Search + build context → Ollama chat completion → return answer with source citations (supports SSE streaming)

### Key Infrastructure

All services run in Docker Compose: `qdrant`, `postgres:16-alpine`, `redis:7-alpine`, `minio` (object storage), `ollama` (local LLM), `rag-controller` (FastAPI), `frontend` (nginx-served SPA).

GPU variant compose files: `docker-compose.amd.yml` (AMD ROCm), `docker-compose.nvidia.yml` (NVIDIA CUDA). Base `docker-compose.yml` is CPU-only.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/knowledge-bases` | Create knowledge base |
| GET | `/api/v1/knowledge-bases` | List knowledge bases |
| DELETE | `/api/v1/knowledge-bases/{id}` | Delete knowledge base |
| POST | `/api/v1/knowledge-bases/{id}/documents` | Upload document |
| GET | `/api/v1/knowledge-bases/{id}/documents` | List documents |
| DELETE | `/api/v1/knowledge-bases/{id}/documents/{doc_id}` | Delete document |
| POST | `/api/v1/knowledge-bases/{id}/search` | Semantic search |
| POST | `/api/v1/knowledge-bases/{id}/query` | QA (non-streaming) |
| POST | `/api/v1/knowledge-bases/{id}/query/stream` | QA (SSE streaming) |
| GET | `/api/v1/knowledge-bases/{id}/wiki/pages` | List wiki pages |
| GET | `/api/v1/knowledge-bases/{id}/wiki/pages/{page_id}` | Get wiki page content |
| POST | `/api/v1/knowledge-bases/{id}/wiki/lint` | Wiki lint check |
| GET | `/api/v1/admin/models` | List available models |
| POST | `/api/v1/admin/reload-config` | Hot-reload YAML config |
| GET | `/docs` | Swagger UI |

## Commands

### Run full stack (Docker)
```bash
bash up.sh                       # One-click start with GPU detection (or use docker compose directly)
docker compose up -d             # Start all services
docker compose down              # Stop all services
docker compose restart rag-controller  # Restart backend only
```

### Backend (local dev without Docker)
```bash
pip install -r app/requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (local dev)
```bash
cd frontend && npm install && npm run dev
```
Build for production: `cd frontend && npm run build`

### Tests
```bash
cd app && python -m pytest ../tests/ -v                  # All tests
cd app && python -m pytest ../tests/test_chunking.py -v  # Single test file
cd app && python ../tests/test_chunking.py -v            # Or run directly
```
Tests use `sys.path.insert(0, "..")` pattern — run from `app/` directory (not project root).

### Functional / Smoke Tests
```bash
./scripts/test.sh               # Requires running API (defaults to localhost:8005)
API_URL=http://localhost:8000 ./scripts/test.sh
```

### Seed Data
```bash
python scripts/seed.py          # Requires running API on localhost:8000
```

### Docker Compose management
```bash
docker compose ps               # Container status
docker compose logs -f rag-controller  # Watch backend logs
docker compose logs -f ollama   # Watch LLM logs
docker compose exec ollama ollama list  # List downloaded models
```

### Health checks
```bash
curl http://localhost:8000/health             # API health
curl http://localhost:11434/api/tags          # Ollama status
curl http://localhost:6333/collections         # Qdrant state
# Qdrant dashboard: http://localhost:6333/dashboard
```

### Model Management
```bash
ollama pull nomic-embed-text    # Embedding model (768 dim)
ollama pull qwen2.5:7b          # Default generation model
```

### Config Reload
```bash
curl -X POST http://localhost:8000/api/v1/admin/reload-config  # Hot-reload YAML
```

### Backup
```bash
docker compose exec postgres pg_dump -U ragkb ragkb > backup_$(date +%Y%m%d).sql
curl -X POST 'http://localhost:6333/collections/documents/snapshots'  # Qdrant snapshot
```

## Key Patterns

- **Settings come from YAML + env var overrides**: `config/rag-controller.yaml` is the main config file; `_resolve_env()` in `app/core/config.py` handles `${VAR:-default}` substitution. `.env` file is loaded via pydantic-settings. Configs: `rag-controller.yaml` (app), `models.yaml` (Ollama model registry), `retrieval.yaml` (RAG strategies).
- **Async everything**: Backend uses `asyncpg`, `httpx.AsyncClient`, `AsyncSession` throughout.
- **Qdrant is the vector store** (sync client wrapped with async facade). Collection is auto-created on first write with HNSW config. GRPC port: 6334.
- **Ollama is the only LLM provider**: embedding, generation, chat all go through `app/core/ollama_client.py`.
- **Wiki engine is filesystem-based**: per-KB markdown files in `data/wiki/<kb_id>/`, no additional DB. Index is a markdown table.
- **Chunking strategies**: three modes — `recursive` (size-based split with overlap), `semantic` (split by paragraph/topic boundaries), `code-aware` (preserves code block integrity).
- **No auth**: MVP, all endpoints are unauthenticated. CORS is open by default.
- **Embedding cache** is in-memory dict (simplified; Redis is available but not wired for caching yet).
- **All content is Chinese** by default (system prompts, lint messages, UI text).
