# Recommended technical stack — target, not deployed runtime

> **Implementation reality (verified in source on 2026-10-21):** the running code uses multiple SQLite databases (including `product_state.db`, `career_fit.db` and `career_state.db`), SQLite FTS5/BM25 and optional local TF-IDF/LSI hybrid retrieval. PostgreSQL, pgvector, SQLAlchemy/Alembic and the Next.js/React target below are a **proposed stack, not a verified deployed implementation**. Do not claim operational maturity from this architecture proposal. See [SQL integrity plan](SQL_DATA_INTEGRITY_PLAN_2026-10-21.md) and [48-case database acceptance matrix](SQL_DATA_INTEGRITY_TEST_MATRIX_2026-10-21.md). Before migrating: prove current SQLite transaction correctness, concurrency handling, staging isolation, recoverability and safe schema upgrades.


## Product application

### Frontend
- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- shadcn/ui primitives
- TanStack Query
- Zustand for small client state
- Playwright for browser E2E

Why:
mature hiring-product stack, strong SSR/app-router ergonomics, fast interface iteration.

### API
- FastAPI / Python 3.12+
- Pydantic contracts
- httpx adapters
- OpenAPI-generated TS client

Why:
document parsing, retrieval, ML/LLM ecosystem and typed APIs fit Python well.

### Primary database
Production:
- PostgreSQL
- pgvector
- SQLAlchemy / Alembic

Local / demo:
- SQLite + FTS5

Objects:
- users
- jobs
- job_sources
- requirements
- evidence_objects
- evidence_sources
- matches
- review_decisions
- application_packages
- applications
- outcomes
- search_subscriptions

### Search / retrieval

Stage 1:
- lexical BM25 / Postgres full-text
- metadata filters
- exact skill aliases

Stage 2:
- pgvector embeddings
- hybrid retrieval: lexical + vector + provenance metadata

Stage 3:
- reranker for top-N evidence candidates

Never use vector similarity as proof by itself.

### LLM layer
- LiteLLM abstraction
- provider-selectable: OpenAI / Anthropic / Gemini / local Ollama

LLM jobs:
- structured requirement extraction
- evidence atomization assistance
- semantic match explanation
- package drafting
- interview-defense questions

Deterministic code owns:
- hard constraints
- allowed/blocked evidence states
- application send permissions
- provenance rules

### Background jobs
- Redis
- Celery / Dramatiq
- scheduled search subscriptions
- document processing
- enrichment
- eval batches

### Job discovery adapters
Broad:
- Adzuna
- Jooble
- optional commercial Google Jobs search provider

Direct ATS:
- Greenhouse
- Lever
- Ashby

Universal fallback:
- browser extension capture

### Occupation taxonomy
EU:
- ESCO API / local dataset

Optional:
- O*NET for US-oriented enrichment

### File/evidence ingestion
- PDF: pypdf
- DOCX: python-docx
- HTML: BeautifulSoup
- spreadsheets: openpyxl / csv
- images: user-confirmed metadata first; optional multimodal extraction
- GitHub: README/issues/releases/repo metadata via API

### Auth / storage
- Auth.js or Clerk
- S3-compatible object storage
- envelope encryption for private evidence
- source-level consent and deletion controls

### Observability
- OpenTelemetry
- Sentry
- structured agent/tool traces
- prompt/version IDs
- eval regression dashboard

## Safety / trust architecture

A generated application claim needs:
- source evidence ID
- verification status
- ownership boundary
- metric type: measured / modeled / target
- visibility permission

No provenance → no automatic outward-facing claim.

## Deployment

Small public beta:
- Vercel frontend
- Render/Fly.io API worker
- Neon/Supabase Postgres
- Upstash Redis
- S3/R2 files

Self-hosted option:
- Docker Compose
- Postgres + pgvector
- Redis
- Ollama
