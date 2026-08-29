# Building Hermes: Engineering Decisions, Reasoning, and What Broke Along the Way

This is a decision-by-decision account of building a production-style RAG (Retrieval-Augmented Generation) agent — hybrid search, reranking, role-based access, async ingestion, observability — on entirely free-tier infrastructure. Not a feature list: the reasoning behind each call, the alternatives considered, and the real problems hit while building it.

---

## 1. Hybrid retrieval: Pinecone (dense) + BM25 (lexical), not just vector search

**The decision**: run two retrieval systems in parallel — Pinecone for dense/semantic similarity, and BM25 (`rank_bm25`, in-process) for exact keyword matching — merge the results, then rerank.

**Why**: a pure vector-search RAG system is good at "find text that means something similar," and quietly bad at exact terms — a section number, an acronym, a product code, a name. Embedding models compress a chunk of text into one vector representing its overall gist; a rare, specific term can get diluted in that average rather than standing out. BM25 doesn't understand meaning at all — it's a statistical measure of exact word overlap, weighted by how rare a term is across the corpus. The two systems have opposite failure modes, so running both and merging catches more of what users actually ask than either alone.

**Why BM25 specifically, not a second hosted service**: `rank_bm25` runs in-process, in memory, no external API, no rate limit, no hosting cost. Zero infrastructure tradeoff for meaningfully better recall.

---

## 2. Reranking as a separate precision step (Jina Reranker)

**The decision**: retrieval is deliberately over-inclusive — cast a wide net across both retrievers — then a cross-encoder reranker re-scores the merged candidates before anything reaches the LLM.

**Why**: retrieval and relevance-ranking are different problems. A retriever's job is *coverage* — don't miss the answer. A reranker's job is *precision* — of everything retrieved, what's actually most relevant to this specific question. Trying to make retrieval alone both broad and precise usually makes it worse at both. Splitting the concerns means the merge step doesn't need a sophisticated fused-ranking algorithm (like Reciprocal Rank Fusion) — it just needs to deduplicate the union of both retrievers' candidates and hand everything to the reranker, which does the real judgment call.

**Why hosted (Jina) instead of self-hosted**: a cross-encoder reranker is a real model, not a lightweight algorithm like BM25 — running it locally would consume meaningful CPU/RAM on an already-constrained free-tier host. A hosted API with a free token allowance keeps the deployment footprint light.

---

## 3. LangGraph as an explicit orchestration graph, not a function-call chain

**The decision**: the query pipeline — `query_guardrail → retrieval → reranking → generation → output_guardrail` — is built as an actual LangGraph `StateGraph`, not a straight sequence of function calls.

**Why**: it was *built* first as a plain function chain (prove the logic works), then deliberately refactored into a graph once the logic was solid — restructuring first, adding new behavior second, never both at once. The graph buys three concrete things: every stage becomes independently traceable in LangSmith (see §9) instead of one opaque call; guardrail stages become first-class nodes rather than inline `if` statements scattered through a function; and the shape matches what a more complex agent (conditional routing, retries, tool calls) would need later, without having to re-architect for it.

**A deliberate boundary**: authentication stays *outside* the graph, enforced by a FastAPI dependency before the graph ever runs. Putting auth inside a graph node would mean passing credentials through graph state for no real benefit — FastAPI's dependency injection already does this well, and it keeps the graph focused purely on the retrieval/generation logic.

---

## 4. Role-based access enforced in the backend — never the LLM

**The decision**: whether a user can upload/delete documents (admin) versus only query (staff) is a deterministic check in FastAPI dependency code, checked against the database on every request. It is never expressed as a prompt instruction, and never delegated to the model's judgment.

**Why this is a hard rule, not a preference**: an LLM is not an access-control boundary. Prompt-based restrictions can be argued with, confused, or bypassed via injection; a `require_role(Role.ADMIN)` dependency cannot be talked out of its job. This matters more than it might seem for a demo project — a real internal knowledge base handling department-specific or access-controlled documents genuinely depends on this boundary holding, and "the LLM usually respects the rule" is not a security property.

**A related design choice**: role checks re-fetch the user's current role from the database on every request rather than trusting the role embedded in a JWT at login time. A stateless token would let a demoted admin retain access for the rest of the token's lifetime; re-checking the live database row closes that window immediately, at the cost of one extra (already-necessary) query.

---

## 5. The LLM is never trusted to report its own sources

**The decision**: the model returns a structured response — an answer plus a list of citations (`document_id`, `chunk_index`) — and the backend verifies every citation against the chunks that were actually retrieved for that query before returning anything to the client. Citations that don't match a real retrieved chunk are silently dropped.

**Why**: this is the difference between a demo and something people can actually rely on. An LLM asked to cite its sources will, under normal operation, cite real ones most of the time — and occasionally invent a plausible-looking one, especially under time pressure or ambiguous context. A user acting on a RAG answer treats the citations as ground truth. Unvalidated citations aren't a cosmetic bug; they're a trust and liability problem the moment this is used for anything real. Server-side validation makes fabricated citations structurally impossible to surface, not just unlikely.

---

## 6. Guardrails: query validation, and PII redaction on both sides of the conversation

**The decision**: incoming queries are checked for basic validity (non-empty, under a length cap, no obvious prompt-injection phrasing) before retrieval runs at all. PII (email addresses, credit card numbers) is redacted from both the incoming query *and* the generated answer.

**Why query-side validation**: an oversized or malicious query is a cost and abuse vector — a very long query burns more embedding and generation tokens for no benefit, and a simple pattern check (`"ignore previous instructions"`, `"reveal your system prompt"`) is a first, honest layer of prompt-injection defense. It's explicitly *not* framed as a complete guarantee — pattern matching can be evaded by rephrasing, and that limitation is documented rather than hidden. Defense in depth, not a silver bullet.

**Why PII redaction on the query, specifically**: without it, if a user pastes their own email or card number into a question, that raw text flows straight through to third-party APIs (the embedding provider, the LLM) with zero redaction. Redacting it *before* anything is sent outward means that data genuinely never leaves the server boundary, rather than "probably" being handled responsibly downstream.

**Why PII redaction on the answer too**: protects against the model surfacing sensitive information that happens to live inside a retrieved document — a different threat, same mitigation.

**A deliberate build choice worth naming**: LangChain ships a `PIIMiddleware` that does this, but it's designed to hook into their `create_agent()` framework — adopting it would have meant restructuring the generation step around an abstraction with real integration risk to the already-working, already-tested citation-validation logic. Instead, the underlying detector functions (`detect_email`, `detect_credit_card`, `apply_strategy`) — the actual tested logic *inside* that middleware — are called directly from custom graph nodes. Real, tested detection logic, without the framework coupling or the risk to working code.

---

## 7. Async ingestion: Celery, not inline processing

**The decision**: uploading a document returns almost instantly (`202 Accepted`) with status `processing`. The actual work — parse, chunk, embed, index — happens in a background worker, and the client polls (or later, could subscribe) for the status to flip to `ready` or `failed`.

**Why**: parsing, chunking, generating embeddings, and upserting vectors for a real document takes anywhere from a few seconds to tens of seconds — blocking an HTTP request on that is a bad user experience on a good day, and doesn't scale at all under concurrent uploads (one slow synchronous request blocks the entire request-handling thread it's running on). This was, notably, *not* the first version built — ingestion was deliberately built and proven synchronous first, then moved to async once the underlying logic was solid, same "prove correctness, then restructure for production" pattern as the LangGraph refactor.

**A consequence this decision forces**: once processing is async, "the row exists" no longer means "it's ready" — which is exactly the point at which a `status` field (`processing`/`ready`/`failed`) on the document became a genuine requirement rather than speculative complexity. It didn't exist before this, deliberately — it wasn't needed yet.

---

## 8. Why the worker runs on Oracle Cloud, not Render

**The decision**: the API lives on Render; the Celery worker runs on a completely separate machine — an Oracle Cloud Always Free Ampere A1 instance (2 OCPU / 12 GB, ARM).

**Why**: Render's free tier is request-based compute — it can serve an API, but it can't run a persistent background worker process alongside it without paying for a second service. Oracle Cloud's Always Free tier, by contrast, gives a genuine standing compute allocation, not tied to request volume. This is a real free-tier-navigation constraint, not an arbitrary architectural flourish — and it forces a useful discipline: the API and the worker have to communicate *only* through shared external state (a message broker, a database, object storage), because they share no memory, no filesystem, and often no host at all. That constraint is exactly what a real distributed system looks like, at zero cost.

**The actual friction, honestly**: this was the single most operationally painful part of the whole build. In order: SSH host-key verification failing because the confirmation prompt requires typing the literal word `yes`, not `y`; a private key rejected due to Windows file permissions being too open (fixed with `icacls`); an instance-creation error from an accidental shape/image architecture mismatch (x86 shape, ARM image); and finally a private key that simply didn't match what the console had provisioned, solved only by terminating and recreating the instance from scratch, watching the key-generation step carefully. None of this was a code problem. All of it was the unglamorous reality of provisioning cloud infrastructure that never shows up in an architecture diagram.

---

## 9. Docker for both — one image, two commands, two entirely different machines

**The decision**: a single Dockerfile builds one image; the API and the worker run the exact same image with a different startup command.

**Why this specifically mattered here, not just as "best practice"**: the API (Render) and the worker (Oracle's Ampere A1) run on genuinely different CPU architectures — x86_64 versus ARM64. Without containerization, "works on my machine" would have meant separately managing two different sets of installed dependencies, two different sets of platform-specific quirks (the Windows-only Celery `--pool=solo` workaround for local dev, for instance, which simply doesn't exist once the same code runs inside a Linux container — even on the Windows host, via Docker Desktop). One image, built once, run identically regardless of the host underneath, is what actually made deploying to two completely different providers with two completely different chip architectures tractable instead of a maintenance headache.

**A signal-handling detail worth naming**: the initial `CMD` used shell form for environment-variable substitution (`--port ${PORT:-8000}`, since Render assigns its port dynamically) — which silently makes `/bin/sh` the container's PID 1, with the real app as its child, meaning Docker's shutdown signal doesn't reliably reach the app for a graceful shutdown. The fix (`CMD ["sh", "-c", "exec ..."]`, using `exec` to replace the shell process rather than spawn a child) keeps the needed variable substitution while making the app itself PID 1. A one-line difference between graceful shutdowns and the platform having to hard-kill the process on every restart.

---

## 10. Cloudflare R2 as the file hand-off between two machines with no shared filesystem

**The decision**: when a document is uploaded, the API writes the raw file to an R2 bucket and passes only the object's *key* through the Celery task message. The worker fetches the file from R2, processes it, then deletes it — R2 holds nothing durably, it's a hand-off buffer between two machines that otherwise share nothing.

**The alternative seriously considered and rejected**: passing the raw file bytes directly through the Celery/Redis message itself (base64-encoded). It would have worked for this project's typical document sizes, at the cost of loading Redis with large binary payloads. R2 was chosen specifically to keep the message broker doing what it's good at — small, fast coordination messages — rather than repurposing it as a file transport. Object storage, used narrowly, for exactly the problem it's built for.

---

## 11. Alembic migrations, not `create_all()` or manual SQL

**The decision**: schema changes (like adding the `status` field) are written as versioned, reviewable Alembic migration files with both `upgrade()` and `downgrade()`, rather than either hand-run SQL or SQLAlchemy's `create_all()` (which only creates missing tables and can never alter an existing one).

**Why it matters, concretely, not just in theory**: autogenerated migrations are a starting point, not a finished artifact — two real bugs surfaced in review before anything touched the production database. First, SQLAlchemy's `Enum` type persists a Python enum member's *name* (`PROCESSING`) rather than its *value* (`processing`) by default, silently, unless told otherwise — invisible until someone looks directly at the raw data. Second, Alembic's `add_column` doesn't automatically create a new Postgres enum type the way a full `create_table` does — a limitation with no obvious symptom until the migration is actually run and fails. Both were caught by treating an autogenerated migration as a draft to review, not a command to trust.

**On automated migrations at deploy time**: Render's free tier doesn't support pre-deploy hooks, so migrations are run deliberately, by hand, against the production database when a schema change is ready — not automatically on every app boot. Running a migration on every process start is its own risk (races if multiple instances ever start concurrently, migrations firing far more often than schema actually changes); a manual, deliberate step is the more honest choice at this project's current scale.

---

## 12. Observability: LangSmith, and dropping Ragas rather than forcing it

**The decision**: every request is traced end-to-end in LangSmith — each LangGraph node, the exact prompt sent to the LLM, latency, token usage. Ragas (for offline, dataset-driven quality scoring — a genuinely different concern from per-request tracing) was scoped, attempted, and ultimately dropped.

**Why the two were never meant to be redundant**: LangSmith answers "what happened on this specific request, and why" — essential for debugging a multi-stage pipeline where "it's not working" is not actionable without visibility into which stage actually failed. Ragas was meant to answer a different question: "is the pipeline actually good, and did this change make it better or worse" — measured against a fixed set of test questions, not one request at a time.

**Why Ragas was dropped, specifically**: two different Ragas releases both failed at import time on the identical root cause — an unconditional import of a LangChain integration module that the project's `langchain-community` version no longer ships, as part of that package's own ongoing sunset. The tempting fix — downgrade `langchain-community` to restore the missing module — was rejected, because it risked breaking three integrations that were already live, working, and load-bearing (`JinaEmbeddings`, `JinaRerank`, `BM25Retriever`), to unblock a tool that wasn't yet providing any value. Trading a known-working dependency for a chance of fixing an unrelated one is the wrong trade. The gap this leaves — no automated offline quality scoring — is documented as a real, known limitation, not quietly dropped.

---

## 13. Groq for generation, NeonDB for relational data — free tier without being cheap about it

**Groq**: OpenAI-compatible API, open-weight models, purpose-built low-latency inference hardware, genuine free tier. Chosen for the same reason reranking and embeddings are hosted rather than self-run — avoids consuming compute on an already-constrained deployment host — and for not locking the project into a single frontier-model vendor by default.

**NeonDB**: serverless Postgres, holding everything that is *not* vector search — users, roles, document metadata, conversation state. A deliberate separation of concerns from Pinecone: things that are fundamentally relational don't get crammed into vector metadata just because a vector store happens to support arbitrary key-value fields. Each store does the job it's actually good at.

---

## What this project actually demonstrates

The architecture diagram is the easy part to explain. What's harder to show — and what this document is trying to make visible — is the hundred smaller decisions underneath it: when to trust a framework's default behavior and when to check it directly against the source; when a build warning is cosmetic noise and when it's a real security posture issue worth fixing properly; when hand-rolling a small piece of logic is more honest than adopting a framework abstraction with real integration risk; and when "good enough for this project's actual scale" is the right call, made deliberately, rather than an oversight.
