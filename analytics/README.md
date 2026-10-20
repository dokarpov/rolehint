# Job analytics foundation (isolated PostgreSQL slice)

This is an additive prototype, not a migration of existing SQLite user records and not a production deployment.

## Run
1. Start PostgreSQL 15+ in a local disposable database.
2. Run `psql -v ON_ERROR_STOP=1 -d rolehint_test -f analytics/sql/001_foundation.sql`.
3. Run `psql -v ON_ERROR_STOP=1 -d rolehint_test -f analytics/sql/002_smoke.sql` (transaction rolls back test data).

## Data contract
- `external_key` is a canonical ATS requisition ID or a deterministic normalized vacancy fingerprint.
- `event_key` is a stable external message/event ID or deterministic user action ID, not a random retry token.
- `confirmed=false` preserves imported/inferred observations without inflating the funnel.
- `owner_key` is an internal authenticated account identifier, never a client-provided authorization grant.
- Application stages are events, not mutable status columns; consumers must resolve the latest stage by occurred_at and id.
- Channel discovery is many-to-many; attribution policy is deferred rather than double-counting.

## Integration gate
Do not expose these tables through unauthenticated endpoints. Add row-level authorization in the API, reconciliation with existing SQLite state, event ordering tests, backup/restore, and real browser E2E before enabling this for users. Existing product routes remain unchanged.
