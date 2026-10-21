"""Transactional reservation and acknowledgement of distinct job opportunities.

NOT wired to ATS or HTTP yet. Reserve only a source-checked, eligible canonical
job. Billing status is DB-authoritative, never supplied by the browser.
"""
from __future__ import annotations
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_deliveries (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 canonical_id TEXT NOT NULL,
 delivered_at REAL NOT NULL,
 entitlement_type TEXT NOT NULL CHECK(entitlement_type IN ('free','paid')),
 PRIMARY KEY(user_id,canonical_id)
);
CREATE INDEX IF NOT EXISTS idx_job_deliveries_user_time ON job_deliveries(user_id,delivered_at);
CREATE TABLE IF NOT EXISTS job_delivery_reservations (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 canonical_id TEXT NOT NULL,
 request_id TEXT NOT NULL,
 reserved_at REAL NOT NULL,
 expires_at REAL NOT NULL,
 entitlement_type TEXT NOT NULL CHECK(entitlement_type IN ('free','paid')),
 PRIMARY KEY(user_id,canonical_id),
 UNIQUE(user_id,request_id)
);
CREATE INDEX IF NOT EXISTS idx_job_delivery_reservations_expiry ON job_delivery_reservations(expires_at);
"""


class DeliveryLedger:
    def __init__(self, db_path: str | Path, free_limit: int = 10, paid_skus=()):
        self.path = str(db_path)
        if self.path == ":memory:":
            raise ValueError("DeliveryLedger requires a durable SQLite file")
        if free_limit < 1:
            raise ValueError("free_limit must be positive")
        self.limit = free_limit
        # Empty default: commercial vacancy entitlement is not launched.
        self.paid_skus = tuple(str(s) for s in paid_skus if s)
        with self._connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=15000")
            yield conn
        finally:
            conn.close()

    def _paid(self, conn, user_id, now):
        if not self.paid_skus:
            return False
        marks = ",".join("?" for _ in self.paid_skus)
        sql = f"""SELECT 1 FROM entitlements WHERE user_id=? AND sku IN ({marks})
          AND status='active' AND active_from<=?
          AND (active_until IS NULL OR active_until>?) LIMIT 1"""
        return conn.execute(sql, (user_id, *self.paid_skus, now, now)).fetchone() is not None

    def _balance(self, conn, user_id, now):
        delivered = conn.execute("""SELECT COUNT(*) FROM job_deliveries
            WHERE user_id=? AND entitlement_type='free'""", (user_id,)).fetchone()[0]
        reserved = conn.execute("""SELECT COUNT(*) FROM job_delivery_reservations
            WHERE user_id=? AND entitlement_type='free' AND expires_at>?""",
            (user_id, now)).fetchone()[0]
        return max(0, self.limit - delivered - reserved)

    def reserve(self, user_id: str, canonical_id: str, request_id: str,
                now: float | None = None, ttl_seconds: int = 90):
        """Short write lock; caller must have filtered invalid/closed jobs first."""
        if not (user_id and canonical_id and 3 <= len(canonical_id) <= 300
                and request_id and 4 <= len(request_id) <= 128):
            raise ValueError("Invalid delivery identity")
        if not 5 <= ttl_seconds <= 600:
            raise ValueError("Reservation TTL out of range")
        now = time.time() if now is None else float(now)
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM job_delivery_reservations WHERE expires_at<=?", (now,))
                existing = conn.execute("""SELECT 1 FROM job_deliveries
                    WHERE user_id=? AND canonical_id=?""",
                    (user_id, canonical_id)).fetchone()
                if existing:
                    result = {"status": "already_delivered",
                              "free_remaining": self._balance(conn, user_id, now)}
                else:
                    pending = conn.execute("""SELECT request_id FROM job_delivery_reservations
                        WHERE user_id=? AND canonical_id=?""",
                        (user_id, canonical_id)).fetchone()
                    if pending:
                        result = {"status": "reserved" if pending["request_id"] == request_id
                                  else "pending_other_request",
                                  "free_remaining": self._balance(conn, user_id, now)}
                    else:
                        tier = "paid" if self._paid(conn, user_id, now) else "free"
                        if tier == "free" and self._balance(conn, user_id, now) == 0:
                            result = {"status": "exhausted", "free_remaining": 0}
                        else:
                            conn.execute("""INSERT INTO job_delivery_reservations
                              (user_id,canonical_id,request_id,reserved_at,expires_at,entitlement_type)
                              VALUES(?,?,?,?,?,?)""",
                              (user_id, canonical_id, request_id, now, now + ttl_seconds, tier))
                            result = {"status": "reserved",
                                      "free_remaining": self._balance(conn, user_id, now)}
                conn.commit()
                return result
            except Exception:
                conn.rollback()
                raise

    def acknowledge(self, user_id: str, canonical_id: str, request_id: str,
                    now: float | None = None):
        """Idempotently record receipt only after the client displays the result."""
        now = time.time() if now is None else float(now)
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                delivered = conn.execute("""SELECT entitlement_type FROM job_deliveries
                    WHERE user_id=? AND canonical_id=?""",
                    (user_id, canonical_id)).fetchone()
                if delivered:
                    conn.commit()
                    return {"status": "already_delivered",
                            "free_remaining": self._balance(conn, user_id, now)}
                pending = conn.execute("""SELECT entitlement_type,expires_at
                    FROM job_delivery_reservations
                    WHERE user_id=? AND canonical_id=? AND request_id=?""",
                    (user_id, canonical_id, request_id)).fetchone()
                if pending is None or pending["expires_at"] <= now:
                    conn.execute("""DELETE FROM job_delivery_reservations
                      WHERE user_id=? AND canonical_id=? AND request_id=?""",
                      (user_id, canonical_id, request_id))
                    conn.commit()
                    return {"status": "reservation_expired",
                            "free_remaining": self._balance(conn, user_id, now)}
                tier = pending["entitlement_type"]
                if tier == "paid" and not self._paid(conn, user_id, now):
                    conn.execute("""DELETE FROM job_delivery_reservations
                      WHERE user_id=? AND canonical_id=? AND request_id=?""",
                      (user_id, canonical_id, request_id))
                    conn.commit()
                    return {"status": "entitlement_expired",
                            "free_remaining": self._balance(conn, user_id, now)}
                conn.execute("""INSERT INTO job_deliveries
                  (user_id,canonical_id,delivered_at,entitlement_type)
                  VALUES(?,?,?,?)""", (user_id, canonical_id, now, tier))
                conn.execute("""DELETE FROM job_delivery_reservations
                  WHERE user_id=? AND canonical_id=? AND request_id=?""",
                  (user_id, canonical_id, request_id))
                remaining = self._balance(conn, user_id, now)
                conn.commit()
                return {"status": "delivered", "free_remaining": remaining}
            except Exception:
                conn.rollback()
                raise

    def count(self, user_id: str):
        with self._connection() as conn:
            return conn.execute("""SELECT COUNT(*) FROM job_deliveries
                WHERE user_id=?""", (user_id,)).fetchone()[0]
