# Local RAG Knowledge Base (本地 RAG 知识库)

A fully local RAG (Retrieval-Augmented Generation) system with a modern AI-native UI, powered by Ollama and Qdrant.

![UI Preview](docs/ui-preview.png)

## Architecture

```
app/
  core/          — Config (pydantic-settings), Pydantic models, Ollama async HTTP client
  db/            — SQLAlchemy async models, Qdrant vector store client
  pipeline/      — Document parsing, chunking, embedding, search/query
  routers/       — FastAPI routes: documents, search/query (SSE streaming), admin, wiki
  wiki/          — LLM Wiki engine: auto-generates structured markdown pages per KB
frontend/        — React SPA (Vite/TypeScript + Tailwind CSS), 3-panel layout
config/          — YAML configuration: models registry, RAG controller, retrieval strategies
```

### Data Flow

1. **Upload** → Document parsed → chunked → embedded via Ollama → stored in Qdrant vector DB
2. **Search** → Query embedded → vector search → ranked results returned
3. **QA** → Search + build context → LLM generation → answer with source citations (SSE streaming)

### Infrastructure

| Service        | Role                          |
|----------------|--------------------------------|
| Qdrant         | Vector database                |
| PostgreSQL     | Metadata database              |
| Redis          | Cache                          |
| MinIO          | Object storage (documents)     |
| Ollama         | Local LLM (embedding + generation, GPU accelerated) |
| RAG Controller | FastAPI backend                |
| Frontend       | Nginx-served React SPA         |

## Quick Start

### Prerequisites

- Docker & Docker Compose v2
- Python 3.12+ (for local dev)
- Ollama with models: `nomic-embed-text` (768 dim), `qwen2.5:7b` or similar

### Run full stack

```bash
# Start all services
docker compose up -d

# Open frontend
open http://localhost:3000
```

### Local development

```bash
# Backend
pip install -r app/requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend && npm install && npm run dev
```

### Seed data

```bash
pip install httpx
python scripts/seed.py
```

### Pull models

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
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

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, ReactMarkdown
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy (async), SSE Starlette
- **Vector Store**: Qdrant (HNSW indexing)
- **Database**: PostgreSQL 16 (async via asyncpg)
- **LLM**: Ollama (local, GPU accelerated via ROCm)
- **Storage**: MinIO (S3-compatible object storage)
- **Infrastructure**: Docker Compose

## License

MIT
