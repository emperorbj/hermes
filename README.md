# Hermes

A production-style, role-based Retrieval-Augmented Generation (RAG) agent. Hybrid search (dense + lexical), reranking, LLM generation with server-validated citations, and asynchronous document ingestion — orchestrated with LangGraph, served via FastAPI, running on entirely free-tier infrastructure.

Full architectural reasoning — every tool choice, every tradeoff, why each piece exists — lives in [`rag-project-architecture.md`](rag-project-architecture.md). This README covers what the system does and how to run it.

## What it does

- **Role-based access**: Admins can upload and delete documents; both Admins and Staff can query the assistant. Enforced deterministically in the backend, never left to the LLM.
- **Hybrid retrieval**: Pinecone (dense/semantic) and BM25 (lexical/keyword), run in parallel and merged, so both paraphrased questions and exact-term queries are covered.
- **Reranking**: Jina's reranker re-scores the merged candidate set for actual relevance before anything reaches the LLM.
- **Grounded generation with validated citations**: Groq-hosted LLM returns a structured answer plus citations; the backend verifies every cited chunk actually exists in the retrieved set before responding — the LLM is never trusted to invent sources.
- **Guardrails**: query validation (length, basic prompt-injection patterns) and PII redaction (email, credit card) on both the incoming query and the generated answer.
- **Asynchronous ingestion**: uploads return immediately; a Celery worker (on separate compute) parses, chunks, embeds, and indexes the document in the background, with the document's `status` tracked through `processing → ready`/`failed`.
- **Full observability**: every request traced end-to-end in LangSmith — each LangGraph node, the exact prompt sent to the LLM, latency, token usage.

## Architecture at a glance

```
Admin/Staff → FastAPI (Render) → LangGraph
  [query guardrail → hybrid retrieval (Pinecone + BM25) → Jina rerank → Groq generation → output guardrail]

Admin upload → FastAPI → NeonDB (metadata) + Cloudflare R2 (temp file)
  → Celery task (Oracle Cloud worker) → parse → chunk → embed (Jina, cached) → Pinecone + NeonDB chunks
```

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI, hosted on Render |
| Orchestration | LangGraph / LangChain |
| Background worker | Celery, hosted on Oracle Cloud Always Free |
| Broker + caching | Upstash Redis |
| Relational data | NeonDB (Postgres), schema managed with Alembic |
| Vector search | Pinecone (serverless) |
| Lexical search | `rank_bm25` (in-process, no external service) |
| Embeddings + reranking | Jina AI APIs |
| LLM generation | Groq (OpenAI-compatible, low-latency inference) |
| Temporary file hand-off | Cloudflare R2 (S3-compatible) |
| Observability | LangSmith |
| Package management | `uv` |

## Project structure

```
app/
├── main.py              # FastAPI app, router mounting, /health
├── database.py           # SQLAlchemy engine/session
├── models.py               # User, Document, Chunk, enums
├── security.py               # password hashing, JWT
├── dependencies.py             # auth dependencies (get_current_user, require_role)
├── celery_app.py                 # Celery app + broker config
├── tasks.py                        # background ingestion task
├── routers/                          # auth, documents, query endpoints
├── schemas/                            # Pydantic request/response models
└── services/                             # parsing, chunking, embeddings, retrieval,
                                             reranking, generation, guardrails, graph,
                                             vector_store, bm25, cache, storage
alembic/                  # DB migrations
create_tables.py          # (superseded by Alembic — kept for reference)
create_pinecone_index.py  # one-time Pinecone index provisioning script
seed_admin.py             # local script to create/promote an admin user
Dockerfile                # shared image for both API and worker
```

## Running locally

**Prerequisites**: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), accounts/API keys for NeonDB, Pinecone, Jina, Groq, Upstash, Cloudflare R2, and (optional) LangSmith.

1. Install dependencies:
   ```
   uv sync
   ```

2. Create a `.env` file in the project root:
   ```
   DATABASE_URL=
   JWT_SECRET_KEY=
   PINECONE_API_KEY=
   PINECONE_INDEX_NAME=
   JINA_API_KEY=
   GROQ_API_KEY=
   GROQ_MODEL=
   UPSTASH_REDIS_URL=
   R2_ENDPOINT_URL=
   R2_ACCESS_KEY_ID=
   R2_SECRET_ACCESS_KEY=
   R2_BUCKET_NAME=
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=
   LANGSMITH_PROJECT=hermes
   ```

3. Apply database migrations:
   ```
   uv run alembic upgrade head
   ```

4. Provision the Pinecone index (idempotent, safe to rerun):
   ```
   uv run python create_pinecone_index.py
   ```

5. Create an admin user:
   ```
   uv run python seed_admin.py you@example.com YourPassword123!
   ```

6. Run the API:
   ```
   uv run fastapi dev app/main.py
   ```
   Interactive docs at `http://127.0.0.1:8000/docs`.

7. Run the Celery worker (separate terminal):
   ```
   uv run celery -A app.celery_app worker --loglevel=info
   ```
   On Windows, add `--pool=solo` — Celery's default worker pool relies on `os.fork()`, unavailable on Windows.

## Running with Docker

One Dockerfile serves both roles — same image, different command:

```
docker build -t hermes .

# API
docker run --env-file .env -p 8000:8000 hermes

# Worker
docker run --env-file .env hermes uv run celery -A app.celery_app worker --loglevel=info
```

## API

See [`docs/frontend-integration.md`](docs/frontend-integration.md) for the full endpoint reference — request/response shapes, auth requirements, and error formats for frontend integration. The live interactive docs (`/docs`) are also always available on a running instance.

## Deployment

- **API** → Render, deployed from this repo, Dockerfile-based.
- **Worker** → Oracle Cloud Always Free (Ampere A1, ARM), Docker container with `--restart unless-stopped`.
- **Migrations** run manually against the production database (`uv run alembic upgrade head`) rather than automatically on deploy — deliberate, not automated, since Render's free tier doesn't support pre-deploy hooks and running migrations on every app boot is its own risk.
