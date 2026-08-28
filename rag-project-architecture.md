# Production RAG Agent — Project Architecture

## 1. Overview

This document describes the architecture of a role-based, production-style Retrieval-Augmented Generation (RAG) agent. The system supports hybrid search (dense + lexical retrieval), reranking, conversational memory, and strict role-based access control, and is designed to run entirely on free-tier infrastructure.

Two user roles exist:

- **Admin** — can upload documents into the RAG pipeline, remove/delete a document or an entire knowledge base from it, and can query the assistant.
- **Staff** — can only query the assistant; cannot upload or delete documents.

Role authorization is enforced deterministically in the backend (FastAPI + database), never left to the LLM to decide.

---

## 2. Core Tools, Libraries, and Services — Responsibilities

### FastAPI
The application's API layer. Handles authentication, authorization checks, request validation, and exposes endpoints for document ingestion (admin-only) and querying (admin + staff). All access-control decisions happen here before any retrieval or LLM call occurs.

### LangChain
Provides the building blocks for the retrieval pipeline: the `BM25Retriever` (lexical search wrapper around `rank_bm25`), and middleware hooks for guardrails (before/after agent, before/after model, around tool calls). Used for PII detection, model/tool call limits, model fallback/retry, and custom validation logic.

### LangGraph
Orchestrates the end-to-end agent workflow as an explicit graph: authentication/role check → query guardrail → hybrid retrieval → reranking → answer generation → output guardrail. Also provides persistence/checkpointing, which is used as the conversational memory layer.

### rank_bm25 (+ LangChain's BM25Retriever)
Implements the lexical/keyword side of hybrid search (Okapi BM25). Runs in-process inside the FastAPI/Celery application — no separate service or hosting cost required.

### Pinecone (Free tier)
Vector database for the dense/semantic side of hybrid search. Stores document embeddings along with metadata (document ID, document name, chunk ID, page number, source, access level, department, uploader) used for both citation and access-control filtering.

### Reranker (Jina Reranker API — free tier)
Re-scores the merged candidate set from Pinecone (dense) and BM25 (lexical) to produce the final, most relevant context passed to the LLM. Chosen over a self-hosted reranker (e.g., BAAI/bge-reranker-v2-m3) because running a cross-encoder model locally would consume too much CPU/RAM on the free-tier deployment host. The Jina free tier offers a fixed pool of free tokens, rate limits, and a dedicated rerank endpoint, and requires no separate deployment.

### Embeddings (Jina Embeddings API — free tier)
Turns document chunks (at ingestion) and user queries (at retrieval) into the dense vectors stored in and queried against Pinecone. Uses the same Jina account/API key as the reranker, so no separate external service is introduced for this. Chosen over a self-hosted embedding model for the same reason as the reranker — avoids consuming CPU/RAM on the free-tier deployment host — and chosen over a paid provider like OpenAI to keep the project's free-tier-first design consistent.

### LLM Generation (Groq API — free tier)
Produces the final answer from the reranked context. Groq serves open-weight models (e.g. the Llama family) over an OpenAI-compatible API, running on their own inference hardware built for very low latency, with a free tier. Chosen over a paid provider (OpenAI, Anthropic) to keep the project's free-tier-first design consistent, and over self-hosting a model for the same reason reranking and embeddings are hosted rather than local — avoids consuming CPU/RAM/GPU on the free-tier deployment host.

### NeonDB (Postgres)
Relational data store for everything that is not vector search: users, roles/permissions, document metadata, conversation records, and LangGraph checkpoint state (conversational memory). Chosen so that persistent state does not live on the replaceable compute host running Celery.

### Celery
Handles asynchronous background processing — primarily the document ingestion pipeline (parse → chunk → embed → upsert to Pinecone → write metadata to NeonDB) triggered when an admin uploads a document, and the corresponding teardown (remove vectors from Pinecone, remove entries from the BM25 index, delete metadata from NeonDB) triggered when an admin deletes a document or knowledge base. Kept off the main request path so neither ingestion nor deletion blocks API responses.

### Object Storage (Cloudflare R2 — free tier)
Temporary holding area for an uploaded file's raw bytes between the moment FastAPI (on Render) receives it and the moment the Celery worker (on Oracle Cloud — a separate machine, no shared filesystem) actually processes it. The API uploads the file to R2 and passes only its object key to the Celery task (via Redis); the worker fetches the file by that key, processes it, then deletes it from R2 — nothing durable lives here, it's a hand-off buffer, not long-term storage. Chosen over passing raw file bytes directly through the Celery/Redis task queue to keep the message broker free of large binary payloads, and over AWS S3 for R2's free egress and generous free tier. S3-compatible, accessed via `boto3` pointed at R2's endpoint rather than a Cloudflare-specific SDK.

### Redis (Upstash — free tier)
Message broker for Celery. Chosen for its free-tier allocation and standard Redis protocol compatibility, allowing it to be used as a drop-in Celery broker without hosting Redis separately. Also backs the application's three caching layers (embedding cache, retrieval cache, LLM response cache) — one Upstash instance serves both roles, separated by key prefix, rather than provisioning a second Redis instance.

### Docker
Containerizes the FastAPI application and the Celery worker so both can be deployed consistently across different free-tier hosts (Render for the API, Oracle Cloud for the worker).

### Render (Free tier)
Hosts the Dockerized FastAPI application (the API + LangGraph orchestration layer). Render's free tier supports Docker-based web services but does not offer free background worker services, and free instances spin down after 15 minutes of inactivity.

### Oracle Cloud Always Free (Ampere A1)
Hosts the Celery worker in Docker, since Render's free tier cannot run background workers. Provides 2 OCPUs and 12 GB RAM (as of 2026) — enough for a single worker process. Treated as *replaceable compute*: no important data is stored on the VM's local disk; everything durable lives in NeonDB and Pinecone. This avoids designing around Oracle's idle-instance reclamation policy — the worker is simply restarted/recreated from the Docker image if reclaimed, rather than kept alive artificially.

### Ragas
Offline evaluation framework for measuring RAG quality against a test dataset: faithfulness (is the answer supported by retrieved context), answer relevancy, context precision, context recall, and response correctness. Used in the development/testing workflow to compare pipeline changes, not in the live request path.

### LangSmith
Tracing and observability tool. Used during development and operation to inspect what happened during a given request — query generation, metadata filters applied, Pinecone/BM25 results, reranker output, the exact prompt/context sent to the LLM, final answer, latency, token usage, and errors.

---

## 3. Approaches Being Adopted

### Hybrid Retrieval
Dense search (Pinecone) and lexical search (BM25) are run in parallel and their candidate results are merged, then passed through a reranker before reaching the LLM. This combines semantic matching with exact keyword matching.

### Reranking Strategy
Rather than self-hosting a reranker model (which would strain the free-tier deployment's CPU/RAM), a hosted reranker API is used so the deployment footprint stays lightweight.

### Caching Strategy (Upstash Redis)
Three independent caches sit in front of the most expensive or rate-limited steps in the pipeline, all backed by the same Upstash Redis instance used as the Celery broker:

- **Embedding cache** — keyed on a hash of the input text (chunk text at ingestion, query text at retrieval), caches the vector returned by the Jina Embeddings API. Avoids re-embedding identical text, which matters directly because Jina's free tier caps total tokens/month.
- **Retrieval cache** — keyed on a hash of the query plus the active metadata filters (so one user's cached results can never leak to a user with different access permissions), caches the merged/reranked candidate set. Avoids repeating the Pinecone query, BM25 search, and Jina rerank call for a repeated or near-identical question.
- **LLM response cache** — keyed on a hash of the query plus the retrieved context actually used, caches the final generated answer. Avoids a full LLM generation call when the same question has already been answered from the same context.

Each cache is added at the exact point its underlying expensive operation is built (embedding cache alongside the embeddings client, retrieval cache alongside hybrid retrieval/reranking, LLM cache alongside generation) rather than all three being built together up front. Sharing one Upstash instance across Celery and all three caches is the simplest fit for the free tier's fixed budget (256 MB storage, 500K commands/month) — but that budget is now split across more traffic than just Celery, worth monitoring as usage grows.

### Guardrails via LangChain/LangGraph Middleware (not Guardrails AI)
Since the project already commits to LangChain and LangGraph, their built-in middleware (before/after agent, before/after model, around tool/model calls) is used to implement query guardrails, PII detection, model/tool call limits, and output validation — rather than introducing a separate framework like Guardrails AI. Guardrails AI is left as an option only if a specific validation capability is later found missing.

### Role Authorization Kept Out of the LLM Layer
Admin vs. staff permissions (e.g., who can upload documents) are enforced deterministically in FastAPI/database logic, never treated as an LLM guardrail or left to prompt instructions. This is treated as a hard architectural rule, not a preference.

### Metadata Filtering as a Security Layer, Not Just an Optimization
Every retrieved chunk (in both Pinecone and the local BM25 index) carries metadata such as department and access level. Retrieval queries are filtered by the requesting user's role/permissions *before* results are merged and reranked — so unauthorized documents are never retrieved in the first place, rather than being filtered out after the fact. Because BM25 is a local index without Pinecone's native filtering, the same authorization constraints must be applied manually on the BM25 side to keep both retrieval paths consistent.

### Source Attribution
The LLM is never trusted to invent citations. Source metadata (document ID, name, chunk ID, page number, source, hash) is carried through the entire pipeline alongside each chunk. The LLM is prompted to return structured output containing an answer plus a list of citations, and the backend validates that every cited document/chunk ID actually exists in the retrieved set before the response is returned to the user.

### Defense Against Prompt Injection via Retrieved Documents
Retrieved documents are always treated as untrusted data, never as instructions — even when uploaded by an admin. The LLM prompt structure explicitly separates system rules, the user's question, and retrieved document content (wrapped in clear delimiters/tags), with an explicit reminder that document content must never be followed as instructions. This is understood as risk reduction, not a complete guarantee — defense in depth is applied on top of it (backend authorization, ingestion-time scanning, structured output, and server-side citation validation).

### Memory Model — Three Separate Kinds of "Memory"
The system deliberately separates three concerns instead of conflating them into a single vector memory:

1. **Conversation memory** ("what were we talking about") — handled by LangGraph checkpointing, persisted in NeonDB rather than on the Celery worker's local disk.
2. **Knowledge** ("what do the documents say") — handled by Pinecone + BM25.
3. **User/application data** ("who is this user, what's their role, what conversations do they own") — handled by NeonDB.

Conversation memory is scoped per authenticated user and conversation ID so that one user's conversation history can never leak into another user's session. No separate long-term "AI memory agent" or automatic saving of conversations into the vector store is used for the initial version.

### Compute Treated as Replaceable, Data Treated as Durable
The Celery worker host (Oracle Cloud) is intentionally treated as disposable compute. No essential state is stored on it. All durable data lives in NeonDB (relational/metadata/conversations) and Pinecone (vectors). If the worker VM is ever reclaimed or lost, it is simply recreated from the Docker image with no data loss. Artificially keeping the VM "busy" purely to defeat idle-reclamation policies is explicitly avoided in favor of letting genuine ingestion workload keep it active.

### Single Worker to Start
The project starts with one Celery worker (one Oracle VM), since the ingestion workload (admin document uploads) does not require horizontal scaling at this stage. Concurrency or additional workers are treated as a later optimization if ingestion volume grows.

### Evaluation and Observability as Separate Concerns
Ragas answers "how good is the RAG system" through offline, dataset-driven evaluation. LangSmith answers "what happened during this specific request" through tracing. Both are used together but serve distinct purposes — evaluation for measuring/improving quality over time, tracing for debugging and operational visibility.

---

## 4. Component Responsibility Summary

| Component | Responsibility |
|---|---|
| FastAPI | API layer, authentication, role-based authorization |
| LangChain | Retrieval utilities (BM25Retriever), middleware/guardrail hooks |
| LangGraph | Workflow orchestration, conversational memory (checkpointing) |
| rank_bm25 | Lexical/keyword search (in-process, no external service) |
| Pinecone | Dense/semantic vector search, chunk metadata storage |
| Jina Reranker API | Reranking merged hybrid search candidates |
| Groq API | LLM answer generation from reranked context |
| NeonDB (Postgres) | Users, roles, document metadata, conversations, LangGraph checkpoints |
| Celery | Asynchronous document ingestion (parse, chunk, embed, store) |
| Cloudflare R2 | Temporary file hand-off between API and Celery worker |
| Redis (Upstash) | Celery message broker; embedding/retrieval/LLM response caches |
| Docker | Containerization of API and worker |
| Render | Hosts the FastAPI + LangGraph API service |
| Oracle Cloud Always Free | Hosts the Celery worker (disposable compute) |
| Ragas | Offline RAG quality evaluation |
| LangSmith | Tracing and observability of live requests |

---

## 5. Key Architectural Rules

- Authorization is always enforced in the backend, never by the LLM.
- Metadata-based access filtering happens *before* retrieval results are merged or reranked, on both the Pinecone and BM25 sides.
- Retrieved document content is always treated as untrusted data, separated from system instructions.
- Citations are validated server-side against the actual retrieved set before being returned.
- Durable state (documents, vectors, conversations) lives in NeonDB/Pinecone — never solely on the Celery worker's compute instance.
- No artificial workloads are created solely to keep free-tier compute from being reclaimed.
