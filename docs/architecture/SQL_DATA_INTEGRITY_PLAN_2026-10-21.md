# RoleHint — SQL data integrity, persistence and migration plan
**Status:** verified source-code architecture review; implementations and performance claims below are **NOT** marked accepted.  
**Date:** 2026-10-21 · **Scope:** applied SQL evidence, concurrent user operations, free/paid entitlements, history, staging durability, recovery, controlled migration, engineering portfolio.

**Non-negotiable:** keep the operating FastAPI/Telegram/ATS/AutoMatch/webapp and founder-approved visual design. **Do not rewrite the product or switch databases before correctness is demonstrated on the existing store.** No production database migration, live billing or staging promotion is approved here.

## 1. What the repository actually proves

| Capability | Code evidence | Assessment |
|---|---|---|
| Running application SQL engine | `backend/app/services/product_state/store.py`, `evidence_store.py`, `scheduler/subscriptions.py`, `state/career_store.py` import `sqlite3` and execute SQL | **SQLite implementation confirmed**; does not prove full production acceptance |
| Product entities | `ProductStore.SCHEMA` defines users, user_jobs, preferences, evidence, packs, applications, queues, entitlements, etc. | Actual relational design |
| Relational integrity | `FOREIGN KEY` / `ON DELETE CASCADE`, composite PRIMARY KEY, UNIQUE; `PRAGMA foreign_keys=ON` in product schema | Present for at least product-state connection; confirm *per connection* and cross-file behavior |
| Updates / idempotency | `ON CONFLICT DO UPDATE`; UNIQUE(user_id,application_key), UNIQUE(user_id,message_id) | Some safe repeats; check every transaction boundary and user-scoping; no proof of race safety |
| Search | `evidence_store.py` and `ProductStore` implement SQLite FTS5 virtual tables and `bm25()` ranked joins | Genuine query/retrieval capability; does not establish PostgreSQL FTS or pgvector |
| Hybrid retrieval | `vector_retrieval.py` uses TF–IDF → SVD LSI with lexical signals | Working local vector/lexical algorithm **not pgvector-backed** |
| Database topology | `main.py` opens `career_fit.db`, `career_state.db`, `product_state.db`; `worker.py` separately opens product-state DB | Multiple independent SQLite files/connections; no transactional atomicity *across* DB files inferred |
| Transaction boundaries | `web_identity.py` uses `BEGIN IMMEDIATE` for OTP/email consume; `web_release.py` and `ProductStore` frequently commit separately | Auth has protected transactions; **search→validation→delivery credit** not one atomic transaction |
| Parallel use | `ProductStore` opens `sqlite3.connect(...,check_same_thread=False)`; API and worker independently use same product-state path | Shared process connection and cross-process writers demand concurrency testing; `check_same_thread=False` itself does not make multi-statement operations atomic |
| Storage | Railway production service has a volume at `/app/data`; separately named staging service has no `volumeMounts` in current config | Production persistence configured, **backup/restore not proven**; staging durability cannot be assumed |
| Planned replacement | `docs/architecture/TECH_STACK.md` prescribes PostgreSQL, pgvector, SQLAlchemy/Alembic | **Aspirational specification, not observed runtime**. No verified Postgres driver/runtime shown in inspected paths |

No `journal_mode=WAL`, `busy_timeout`, Alembic/versioned schema ledger or restore drill was found in the inspected implementation/search results. This is an **audit evidence gap**, not a claim that none exists anywhere. Inspect exact connection settings and test before choosing defaults.

**Claim discipline:** RoleHint can truthfully be described as an applied SQL-backed product with relational persistence, evidence search and user/application state. Do **not** call it a completed production PostgreSQL architecture, pgvector database implementation, or load-tested database. The user's “L2 Applied SQL” is a provisional skills assessment; reaching “L4” requires reproducible evidence, not a label.

## 2. Environment boundaries — direct read-only Railway evidence

| Railway service | Reported current SHA | Persistent mount in service config | Remaining unknown |
|---|---|---|---|
| `rolehint-api-worker` (production) | `39f4e2dcdbce6f8e09285ba9192555718e09bc6c` | `/app/data` | Backup/restore, lock contention, exact historical DB contents, acceptance |
| `rolehint-staging` (staging-named service) | `4b4cc2ee8d4c4c18651e2fc3e7920b429d522c24` | Not reported | Actual `CFA_DATA_DIR`, lifetime of any DB, configured providers and sign-in |
| Both | Same Railway environment is named `production` (id `40688d3e-9562-44c7-8431-3ce9c9687601`) | Different services | The service name is not evidence of an isolated Railway environment |

**First task:** establish a separate staging environment or prove sufficient service-level isolation, with dedicated durable disposable test DB and test-only secrets. Never move or overwrite the live production volume to make staging work. Snapshot current production databases through an authorized backup procedure **before** any migration.

## 3. Source-verified risks / invariants

**DI-01. Valid lifetime free deliveries.** Each user may receive no more than 10 **distinct, qualifying, actually delivered** canonical jobs free over account lifetime. Searches, ingestion, duplicates, stale/closed/hard-ineligible positions, rejected cards and provider failures do not consume. Count must never come from `len(user_jobs)`: that collection includes analytics/saved/possibly excluded records.

**DI-02. Paid unlimited.** Active verified subscriber SKU grants unlimited *number of qualifying jobs*, paginated with a snapshot/cursor. Other legacy `entitlements` (e.g. Telegram Stars) must not grant this tier. On downgrade, delivery history remains readable and new deliveries obey the free allowance.

**DI-03. Read-only assessment.** `AutoMatchService.analyze_job()` currently calls `upsert_user_job`, `save_job_requirements`, `save_pack_proposal`, and sometimes action enqueue; even `web_release.review()` invokes this. Split `assess(candidate)` (pure/no DB effects) from `accept_and_persist` and explicit `reassess`. Results and quota stay unchanged when merely viewing a card.

**DI-04. Submission idempotency.** Prevent duplicate submission rows and conflicting outcomes across browser retries, worker jobs and account sessions; preserve honest `approved_handoff`, `opened`, `user_confirmed`, `unknown` distinction.

**DI-05. Single user boundary.** Session, CV, evidence, job, pack, search, notification, export and history operations require user-scoped access. FTS5 `user_evidence_fts` has unindexed `user_id`; any join/search must *still* filter by authenticated user and cascade index deletion correctly.

**DI-06. Evidence/CV provenance.** A CV correction or deletion revokes derived approved text, cached matches and exports. FTS index, evidence table and pack material must stay consistent, including crash half-way through a write.

**DI-07. Durable atomicity.** Multi-statement writes must be one transaction or a deliberate saga/outbox across DB files. No idle shared transaction spanning HTTP network calls. Process crashes, retries and source timeouts leave state consistent.

**DI-08. Recoverability.** Railway volume is not a backup. Define retention, snapshots, SQLite online-backup / consistent WAL checkpoint, off-service encrypted storage, restore drill, and RPO/RTO targets approved by owner. Never use a raw file copy of an active DB as the only backup proof.

## 4. Phase D0 — Map data and stabilize SQLite first

**Inspect:** all sqlite connections (API, worker, evidence store, subscription store, career store), file paths, connection/pragma behavior, process count, journal mode, transaction ownership, schema and index drift, FTS sync behavior, referential integrity, expiry/deletion paths, queued/retried writes, and cross-file boundaries.

**Build:** 
- A read-only schema inventory plus `PRAGMA integrity_check`, `foreign_key_check` and FTS consistency/rebuild checks on **isolated restored copies**, not disruptive live tests.
- Versioned, idempotent, forward migration scripts for current SQLite files (schema migration table, pre/post conditions, backup first, rollback strategy per change); remove reliance on silently expanding `CREATE TABLE IF NOT EXISTS` for schema evolution.
- Explicit connection owner/transaction discipline. Evaluate WAL, `busy_timeout`, connection-per-request or serialized writer **with measured contention and Railway-volume semantics**. No claim that WAL eliminates writer serialization; no unsupported horizontal scaling of SQLite.
- Make staging durable and independently restorable before cross-device or restart E2E.
- State/object invariants that run at startup/test and produce redacted diagnostics; no personal CV in test logs.

**Exit:** same schema version after repeat migration, full FK/FTS integrity checks, no silent lost account, source/CV correction/delete propagation, safe process restart, and documented backup + successful restore to a disposable environment.

## 5. Phase D1 — Atomic delivery ledger and state transitions (FIRST feature gate)

**Data entities (conceptual, not migration already applied):**
- `canonical_jobs` or normalized equivalent: stable employer/requisition/URL identity, source status and `verified_at`, provenance, version.
- `job_deliveries(user_id,canonical_id,first_delivered_at,entitlement_type)` unique on `(user_id,canonical_id)`, indexed by user/time; make delivery verifiable and idempotent.
- `delivery_attempts` / reserved slots (if needed for correctness over interrupted HTTP responses): idempotency key, TTL, state, canonical ID, user.
- `search_snapshots` + `search_snapshot_items` storing deterministic rank/eligibility + short TTL, per-user ownership and stable pagination cursor.
- Validated `entitlement` view by **approved recurring SKU, verified provider status and expiry**; not arbitrary `entitlement(uid) != NULL`.
- `schema_migrations` with monotonically increasing version and migration fingerprint.

**Atomic flow, without holding a DB write lock during upstream network work:**
1. Fetch provider data outside the transaction; normalize, source-check, hard-exclude, dedupe, assess and rank **without DB mutation**. Mark unknown open/eligibility honestly.
2. Begin a short explicit write transaction on one dedicated connection (SQLite `BEGIN IMMEDIATE` or a proven equivalent). Check session user, source identity, whether already delivered, entitlement tier, free delivered count, and concurrent unexpired reservations.
3. Reuse prior delivery free of charge; for a *new* eligible item, reserve space only while `delivered + active reservations < 10` (free); paid SKU has no count cap. Persist canonical mapping and idempotency key, not a dozen independent commits.
4. Commit before responding. On browser acknowledgement of a rendered result, atomically finalize the reservation to a qualifying delivery; pending reservations expire/release after interruption. If the product instead defines commit-on-response as delivered, obtain explicit owner approval because the server cannot prove the browser actually received/rendered it. Ensure repeat fetch and ACK never double debit.
5. Keep an immutable result snapshot for pages, with collision-free canonical IDs and opaque, signed/expiring cursor. Rechecks that close a job before delivery must free an unconsumed reservation, not charge the user.
6. Reassessment/view/update of the same job writes only versioned analysis, never an extra delivery. New findings can invalidate card freshness without erasing user actions.
7. Simultaneous worker/manual jobs must acquire the same transactional canonical/delivery constraints; do not use app-local mutex as the only defense across processes.

**Source-backed exit conditions:** two concurrent devices cannot deliver #11 for a free account; same listing never consumes twice; a failed response leaves no permanently spent credit; 120+ unique paid fixture jobs reachable; old submissions and jobs remain readable; source/credit history auditable. Validate against `VACANCY_RESULTS_AND_ENTITLEMENTS_V1.md`.

## 6. Phase D2 — Concurrent application, queue and index integrity

- `application_submissions` UNIQUE(user_id,application_key) remains the ultimate final guard, but test select-then-insert races and return an idempotent response instead of raw `IntegrityError`.
- Handoff approval, user-confirmed submission and email outcome updates must have legal state transitions, version checks and persistent event timestamps, without silent `last write wins`.
- Worker lease/claim for due searches and notification queues to prevent two runners from sending twice. Use unique event/provider IDs and transactional outbox for durable retries.
- Version CV/evidence/pack writes. Reject stale versions (optimistic concurrency), keep approved claim trace and invalidate exported derived material on source change.
- FTS upsert, delete and account deletion operate in a transaction with relational records. Verify ghost document isolation and index drift (no user sees another user's FTS hits).
- Security: test IDOR, injection safety (SQL placeholders + FTS query handling), credential/PII logs, unsafe external URL, cross-file partial failure.

## 7. Phase D3 — Evidence-driven PostgreSQL decision and migration (OPTIONAL until proven)

A migration is **not** automatic just because `TECH_STACK.md` calls PostgreSQL the intended production stack. SQLite is valid for a constrained, single-writer deployment if correctness, backup, write latency and safety are demonstrated. Trigger a PostgreSQL move when requirements actually demand concurrent multi-instance writes, stronger distributed transactions, managed PITR/ops SLAs, scale or persisted pgvector queries—and cost/complexity justify it.

**Before switching:** a migration ADR containing SQLite workload profile, peak concurrent operations, lock errors, p50/p95/p99 write latency and lookup latency, database growth and FTS update costs, volume durability, availability/restore needs, and trade-offs. Thresholds / RPO / RTO require explicit owner signoff; don't invent them.

**Safe migration design:**
1. Inventory and hash/census current tables, users, submissions, CV/evidence/FTS, links, quotas, tokens, search profiles and history; **no raw CV to GitHub**. Encrypted off-service verified backup.
2. Define Postgres schema, referential/unique constraints, timestamps/time zones, normalized arrays/JSONB, FTS parity and retrieval score boundaries. Version with migrations (Alembic is a candidate, not a confirmed existing tool).
3. Write tested *idempotent* import and per-table row-count/checksum/semantic-invariant compare; replay only controlled delta updates. Avoid a casual unsafe “copy DB and switch URL” operation.
4. Shadow-read or isolated copy of representative workflows and query EXPLAIN ANALYZE with parameterized queries; compare results and source provenance.
5. Plan rollback, freeze/cutover and new-write reconciliation explicitly. **Never** promise safe instant rollback once Postgres accepts writes without a dual-write/replay strategy that has itself passed tests.
6. Only if semantic retrieval is measured to improve evidence ranking enough, introduce pgvector embeddings + hybrid retrieval. Vector similarity still cannot prove candidate qualifications.
7. Run full live end-to-end, concurrency, persistence, privacy, backup/restore, outage and conversion tests before promoting.

## 8. Engineering evidence for technical interviews / portfolio

Target honest repository artifacts:
- ER/data-flow diagrams **of current and target separately**, using sanitized names, no PII.
- SQL schemas and numbered migrations with invariant design notes.
- A reproducible FTS5/BM25 query example and query plan (SQLite `EXPLAIN QUERY PLAN`) on synthetic data.
- A regression demonstrating the pre-fix free-ten race and post-fix bounded result, including 2 processes/threads and worker simulation.
- Idempotent submission tests, orphan/FTS corruption detection, crash-injection, backup/restore runbook with actual commands, redacted timestamps and outcomes.
- SQLite performance numbers first; Postgres `EXPLAIN (ANALYZE, BUFFERS)` only **after** a real Postgres implementation is deployed. No fabricated throughput/latency or “L4” claim before reproduction.
- Build/CI run link, environment, full SHA, before/after behavior, limitations and actual founder launch decision.

**Competency assessment:** Current evidence supports *applied relational SQL* (provisional user assessment “L2”). Higher level depends on measured correctness, migration and operations. A PostgreSQL claim is not necessary for a strong, honest SQL-backed product case.

## 9. Dependencies and gates into UX / release

1. **Immediately:** isolate/durably configure staging and turn outdated fixture tests into a faithful current-UI baseline.
2. **Before promising ten-free, saved search or paid-unlimited:** D0 + D1. Atomic transactions/ledger are release blockers, **not** secondary backend cleanup after front-end design.
3. **Before claiming reliable apply/track:** D2 submission/outcome and versioning tests.
4. **Before multi-worker scale:** prove SQLite shared-volume and lock constraints, or complete separately approved D3 migration.
5. **Before production launch:** full backend fixtures + live CV-first and role-first, actual ATS source freshness, device session, data restore, account isolation, deployment SHA and rollback receipt.

**Companion acceptance inventory:** [SQL_DATA_INTEGRITY_TEST_MATRIX_2026-10-21.md](SQL_DATA_INTEGRITY_TEST_MATRIX_2026-10-21.md). The 200-case UX matrix remains separate; database scenarios reinforce its P0 data-state gates.

**Sources:** `backend/app/services/product_state/store.py`, `backend/app/web_identity.py`, `backend/app/web_release.py`, `backend/app/services/evidence_store.py`, `backend/app/services/vector_retrieval.py`, `backend/app/main.py`, `backend/app/worker.py`, `docs/architecture/TECH_STACK.md`, `docs/adr/ADR-002-web-release-boundaries.md`, `docs/RELEASE_BASELINE_2026-10-20.md`, Railway service config/deployment metadata. Do not confuse reviewed code with runtime proof.
