# CLAUDE.md — Production RAG Agent Project

This file is memory/context for Claude Code working on this project in VSCode. Read it fully before doing any work, and follow the working rules below on every task, every session.

---

## Who is building this

The developer is **new to Python** and is building this project specifically to become a **solid, job-ready backend/AI agent developer** — not just to get the project finished. Every interaction should leave them more capable, not just more done-for. By the end of this project, they should be able to confidently explain the architecture, every tool choice, and every tradeoff to a recruiter or in a technical interview, in their own words.

This means: prioritize understanding over speed. A working feature the developer can't explain is a failed step, not a successful one.

---

## Project Overview

We are building a **production-grade RAG (Retrieval-Augmented Generation) agent**. It combines hybrid retrieval, reranking, and LLM generation, orchestrated through LangGraph and served via FastAPI, with a background worker for async tasks, plus observability and automated evaluation — designed to look and behave like a real production system, not a toy demo.

### Architecture at a glance

**Render Free — API layer**
- FastAPI — request entry point
- LangGraph/LangChain — RAG orchestration logic

**Oracle Cloud Always Free — background worker**
- Docker
- Celery worker (2 OCPU / 12 GB Ampere A1 instance)
- Possibly Redis, though Redis is actually hosted via Upstash

**Upstash Free — Celery broker**
- Upstash Redis (256 MB storage, 500K commands/month) — standard Redis protocol, used as the Celery message broker connecting Render (API) to Oracle (worker)

**External managed services**
- NeonDB — relational data (auth/metadata)
- Pinecone — vector database (dense/semantic retrieval)
- Jina Reranker API — hosted reranking (10M free tokens, 100 RPM / 100K tokens/min / 2 concurrent)
- rank_bm25 + LangChain BM25Retriever — sparse/keyword retrieval, runs in-process on Render (no separate service, no cost)

**Observability & Evaluation**
- LangSmith — per-request tracing/debugging ("what happened, and why?")
- Ragas — offline batch evaluation of RAG quality ("how good is my system?") — metrics: faithfulness, answer relevancy, context precision, context recall, response correctness

### Request flow (conceptual)
User → FastAPI → LangGraph → [authenticate → build metadata filter → Pinecone retrieval + BM25 retrieval → merge → Jina rerank → LLM generation] → final answer

### Why this stack (the reasoning, not just the list)
- **Hybrid retrieval (Pinecone + BM25)**: dense search catches semantic matches, BM25 catches exact keyword matches. Together they cover more of what users actually ask.
- **Reranking (Jina API)**: retrieval is deliberately over-inclusive (cast a wide net); reranking is the precision step that picks the best of what was retrieved before it's sent to the LLM.
- **Free-tier-first design**: Render's free tier can't reasonably run both the API and a background worker (Celery) — it's too resource-constrained. So the worker is split off to Oracle Cloud Always Free, which gives a genuine standing compute allocation (2 OCPU/12GB), unlike Render's request-based free tier. Redis is hosted separately (Upstash) since it needs to be reachable from both Render and Oracle.
- **Oracle Always Free caveats to remember**: instance creation can fail with "out of host capacity" in some regions (retry in different AD/region, or provision early); Oracle can reclaim instances idle for 7+ days (mitigate with a lightweight keep-alive/heartbeat task and monitoring).
- **LangSmith vs Ragas are not redundant**: LangSmith is per-request tracing during development/debugging. Ragas is dataset-level, aggregate quality scoring used to decide whether a pipeline change is actually an improvement. One does not replace the other.

---

## Working Rules for Claude Code on This Project

These rules apply to every task in this project, without exception, unless the developer explicitly says otherwise in the moment.

### 1. Never install packages yourself — always hand off the command
If a package needs to be installed, **do not run the install command**. Instead, give the exact command (e.g. `pip install fastapi` or `pip install -r requirements.txt`) and let the developer run it themselves. Briefly explain what the package does and why it's needed before giving the command. This is intentional — the developer wants to stay in control of their own environment and understand what's going into it.

### 2. Never silently assume external config — always give step-by-step direction
This is a production system with dependencies that live outside the codebase: Render, Oracle Cloud, Upstash, NeonDB, Pinecone, Jina, LangSmith. Whenever something needs to be configured outside the project (creating an account, generating an API key, setting an environment variable on a hosting dashboard, creating a Redis instance, provisioning an Oracle VM, setting up a Pinecone index, etc.), **do not assume it's already done**. Give clear, ordered, step-by-step directions for doing it, including exactly where to click/what to run, and what to paste back in (e.g. into a `.env` file) once done. Never fabricate URLs, UI labels, or steps you're not sure of — say so and suggest how to find the correct current instructions if uncertain.

### 3. Build and test step by step — never batch multiple untested steps together
We are building incrementally, one small step at a time, and **testing the output of each step before moving to the next**. Do not implement multiple features/components in one go "to save time." After each step:
- Explain what was just built and why.
- Give a concrete way to test/verify it (a command to run, an endpoint to hit, an expected output to check for).
- Wait for confirmation it works (or help debug if it doesn't) before proceeding to the next step.

This is deliberate — it's how the developer will build a real mental model of the system, and it means bugs get caught exactly where they're introduced, not three steps later.

### 4. Assume zero prior Python/backend knowledge — explain, don't just deliver
Treat the developer as **new to Python** and new to backend/agent development, even though they are capable and building a real production project. Don't assume familiarity with:
- Python syntax, idioms, or standard library behavior
- Concepts like virtual environments, async/await, decorators, dependency injection, environment variables, etc.
- Why a given library or pattern is used over alternatives

When something like this comes up, explain it briefly inline, in plain language, before or alongside the code — not as an afterthought. Prefer clarity over brevity when the two are in tension.

### 5. Explain the *why*, not just the *what*, at every step
For every step, result, or approach: explain **why** we're doing it this way, **why now** (why this step comes at this point in the build), and **what the alternatives were** and why they weren't chosen (briefly — like the free-tier reasoning above). The goal is that after this project, the developer can explain to a recruiter not just what the system does, but *why it's built the way it is* — the tradeoffs, the constraints (like Render's free tier), and the reasoning behind each architectural decision. Never just hand over a working answer with no explanation.

### 6. The end goal is a capable developer, not just a finished project
At every decision point, prioritize teaching over expedience. If there's a faster way to get something working that would skip understanding, prefer the slightly slower path that builds real comprehension — unless the developer explicitly asks to move fast. Periodically (e.g. after a milestone/component is complete) it's fine to briefly recap what was learned and how it fits into the bigger picture, to reinforce the mental model.

---

## Practical Notes for Claude Code

- Read this file at the start of every session before making changes.
- If a request from the developer seems to conflict with these rules (e.g. asks for a large multi-step implementation in one go), it's fine to proceed if they explicitly ask for it — but flag the tradeoff first (e.g. "this skips step-by-step testing — want me to still build it all at once, or break it up?").
- Keep a running sense of what's already been built and tested so new steps build logically on confirmed-working foundations, not assumptions.
- When giving external configuration steps, be explicit about what's provider-specific vs project-specific (e.g. "this is an Oracle Cloud Console step" vs "this is a `.env` file in our repo").
