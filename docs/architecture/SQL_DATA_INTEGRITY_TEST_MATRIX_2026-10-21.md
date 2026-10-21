# RoleHint — SQL data-integrity and migration acceptance matrix
**Created:** 2026-10-21 · **48 test scenarios** · **Status:** design-only. All rows start **UNTESTED**. No fabricated runtime results.

Companion to [SQL integrity architecture plan](SQL_DATA_INTEGRITY_PLAN_2026-10-21.md), [200-case UX matrix](../UX_EDGE_CASE_MATRIX_2026-10-21.md), [release tests](../RELEASE_TEST_MATRIX.md), and [results entitlements](../VACANCY_RESULTS_AND_ENTITLEMENTS_V1.md). P0 database guarantees block affected first-user or public-tier release, even if UI passes.

**Run order:** validate isolated staging storage/config → migrate schema into disposable fixture DB → DB/worker concurrency and crash/duplicate tests → human-observable browser and cross-device tests → source integrity → backup/restore → performance → optional PostgreSQL dry run. Never run destructive load, corrupt backups, crash injection, or test migrations against the live production volume.

**Evidence per row:** exact full SHA, schema migration revision, SQLite version, Railway service/environment, test user/fixture IDs (synthetic), worker count, concurrency level, status/SQL invariant, timing, trace/log snippet with PII removed, failure/fix evidence. Runtime status values: PASS / FAIL / BLOCKED / UNTESTED.

## Topology, connection safety and schema

| ID | Injection / condition | Expected invariant | Priority | Status |
|---|---|---|---|---|
| DB01 | Every runtime process points to intended DB files | Inspect FastAPI, worker, Telegram and scheduled jobs; no unexpected ephemeral path | P0 | UNTESTED |
| DB02 | Staging restarts and redeploys | Same synthetic test account/job/CV survives only if staging promises persistence | P0 | UNTESTED |
| DB03 | Staging and production isolation | No shared databases, secrets, PII or volume writes; separate deploy decisions | P0 | UNTESTED |
| DB04 | Foreign-key enforcement on every SQLite connection | PRAGMA foreign_keys=ON and foreign_key_check success on all writable connections | P0 | UNTESTED |
| DB05 | Schema upgrade from previously deployed DB | Old seeded schema migrates forward without dropped data; repeated migration idempotent | P0 | UNTESTED |
| DB06 | Schema creation races (two API startups) | No incompatible DDL, partial schema or startup corruption | P0 | UNTESTED |
| DB07 | FTS5 availability and schema parity | Same search behavior on target Linux SQLite build; no unsupported extension | P1 | UNTESTED |
| DB08 | Journal/timeout policy under contention | Measure lock errors, bounded retries, WAL suitability, no indefinite requests | P0 | UNTESTED |
| DB09 | Foreign key ON DELETE cascade across files | Confirm which relationships are cross-file and cannot be enforced by ordinary SQLite FK | P0 | UNTESTED |
| DB10 | App and worker have separate connections to same file | No shared Python connection misuse, concurrent transactions safe or serialized | P0 | UNTESTED |

## Free delivery and paid entitlements

| ID | Injection / condition | Expected invariant | Priority | Status |
|---|---|---|---|---|
| DL01 | Two simultaneous requests for last free vacancy | At most 10 counted; one free slot awarded once | P0 | UNTESTED |
| DL02 | Same canonical vacancy across five ATS sources | One delivery and one lifetime charge | P0 | UNTESTED |
| DL03 | Distinct requisitions with identical title/employer | Two true jobs remain distinct; no incorrect deduplication | P0 | UNTESTED |
| DL04 | Closed, ineligible or unverified source before delivery | Does not debit free allowance; explicit status and replacement option | P0 | UNTESTED |
| DL05 | Network fails after reservation, before result rendered | Pending expires/released; retry remains idempotent | P0 | UNTESTED |
| DL06 | Client renders twice/ACK twice | Same canonical ID charged no more than once | P0 | UNTESTED |
| DL07 | Worker and browser deliver same job concurrently | Same transaction/unique index enforces single delivery | P0 | UNTESTED |
| DL08 | Browser refresh and different device | History and available free credits consistent | P0 | UNTESTED |
| DL09 | Subscription active vs another active SKU | Only explicitly authorized paid subscription unlocks unlimited vacancies | P0 | UNTESTED |
| DL10 | Paid 120 unique jobs across pages | All accessible, no duplicate or ten-limit leakage | P0 | UNTESTED |
| DL11 | Subscription expires during pagination | Previously delivered remains visible, new delivery correctly gated, explicit resume | P0 | UNTESTED |
| DL12 | Quota ledger backfill of historic accounts | Never silently charge old unverified/blocked jobs; reviewed migration policy | P0 | UNTESTED |
| DL13 | Two login identities later explicitly linked | No credit reset or duplicate delivery history without approved merge contract | P1 | UNTESTED |
| DL14 | Rollback after a debit transaction | No charge-without-job record; journal/audit entry survives correctly | P0 | UNTESTED |

## Applications, evidence, indexes and user isolation

| ID | Injection / condition | Expected invariant | Priority | Status |
|---|---|---|---|---|
| AP01 | Two tabs save different drafts | Optimistic version conflict, no silent overwrite | P1 | UNTESTED |
| AP02 | Submission request repeated at network boundary | Exactly one application key, user sees idempotent result | P0 | UNTESTED |
| AP03 | Handoff approved but no employer submission | No application submitted record; status remains handoff/unknown | P0 | UNTESTED |
| AP04 | Failed submission transaction mid-write | All-or-nothing application+event+history updates | P0 | UNTESTED |
| AP05 | Incoming Gmail event repeated/out of order | Deduplicate message/provider IDs and preserve correct response status | P0 | UNTESTED |
| AP06 | Worker queues same notification twice | One consented notification or durable dedupe with safe retries | P0 | UNTESTED |
| AP07 | Edit CV claim used in prepared pack | Invalidate or version supporting evidence and old outward-facing draft/export | P0 | UNTESTED |
| AP08 | Delete CV / account evidence | No orphaned FTS entries, cache snapshots, source-derived pack text beyond policy | P0 | UNTESTED |
| AP09 | FTS5 search across two users with similar CV | Results always restricted to requester; zero private evidence leakage | P0 | UNTESTED |
| AP10 | FTS5 upsert/delete crash injection | Index synchronized with evidence after rollback/recovery; rebuild recovery tested | P0 | UNTESTED |
| AP11 | Cross-account job_id, pack_id, token | Foreign user returns 404/403; no data revealed | P0 | UNTESTED |
| AP12 | Repeat review of saved opportunity | No quota debit, new jobs or action queue side effect unless explicitly requested | P0 | UNTESTED |

## Recovery, performance, and migration evidence

| ID | Injection / condition | Expected invariant | Priority | Status |
|---|---|---|---|---|
| OP01 | Consistent backup of active multi-file SQLite DBs | Each DB and required crypto material captured safely; restore proves usefulness | P0 | UNTESTED |
| OP02 | Restore drill into disposable staging | Exact synthetic users, applications, evidence and quota verify after recovery | P0 | UNTESTED |
| OP03 | Sudden process kill during multi-step write | No partial account/delivery/application state; pending work recoverable | P0 | UNTESTED |
| OP04 | Volume temporarily read-only/full | Clear maintenance error and no fake success or irreversible data loss | P0 | UNTESTED |
| OP05 | Measure peak concurrent search/write load | Record p50/p95/p99, SQLite lock errors and fixture/data size | P1 | UNTESTED |
| OP06 | FTS search benchmark and query plan | Document SQLite EXPLAIN QUERY PLAN + actual run numbers, not fabricated EXPLAIN ANALYZE | P1 | UNTESTED |
| OP07 | PostgreSQL sample migration only after ADR | Row count, canonical IDs and semantic invariants parity on sanitized dataset | P1 | UNTESTED |
| OP08 | Migration failure and rollback after cutover | Document when rollback is safe; no silent divergence of newly written data | P0 | UNTESTED |
| OP09 | pgvector relevance experiment, if justified | Measure precision/evidence quality gains vs SQLite FTS + LSI; no invented improvement | P2 | UNTESTED |
| OP10 | Schema migration rollback and restart | Compatible app/database versions and redacted rollback evidence | P0 | UNTESTED |
| OP11 | Database encryption and retention | No plaintext secret in backup/log, key availability tested on restore | P0 | UNTESTED |
| OP12 | Timed disaster recovery objectives | Document agreed RPO/RTO, actual observed restoration time and data-loss bound | P1 | UNTESTED |

## Release and SQL interview evidence requirements

- **Data safety:** all applicable P0 cases PASS with accurate deployed version and isolated data, or remain BLOCKED with no public claims.
- **Correctness:** count distinct *accepted, delivered* qualifying vacancies, not all analyzed/user_jobs rows; preserve affected user's state on retries and migrations.
- **Benchmark:** publish actual measurement methodology/fixture size/elapsed time/query plan and environment; do not label estimated figures as observed.
- **L4 competency case:** once implemented and measured, publish ER/schema design, SQL query plans, versioned migration records, concurrent failure and solution, backup/restore proof, results and limitations. PostgreSQL and pgvector only after real migration, not because TECH_STACK.md mentions them.
