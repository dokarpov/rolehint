"""Atomic delivery accounting regression. Synthetic SQLite only; no production data."""
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.services.product_state.delivery_ledger import DeliveryLedger


class DeliveryLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "product_state.db"
        with sqlite3.connect(self.db) as conn:
            conn.executescript("""
                CREATE TABLE users(id TEXT PRIMARY KEY);
                CREATE TABLE entitlements(
                    id TEXT PRIMARY KEY,user_id TEXT,sku TEXT,status TEXT,
                    active_from REAL,active_until REAL);
                INSERT INTO users VALUES('u1');
                INSERT INTO users VALUES('u2');
            """)
        self.ledger = DeliveryLedger(self.db, paid_skus=("rolehint_unlimited",))

    def tearDown(self):
        self.temp.cleanup()

    def test_twenty_five_concurrent_candidates_deliver_only_ten(self):
        def deliver(i):
            job, request = f"ashby:open_{i}", f"req-{i:03}"
            reservation = self.ledger.reserve("u1", job, request)
            if reservation["status"] == "reserved":
                return self.ledger.acknowledge("u1", job, request)["status"]
            return reservation["status"]

        with ThreadPoolExecutor(max_workers=12) as executor:
            states = list(executor.map(deliver, range(25)))
        self.assertEqual(states.count("delivered"), 10)
        self.assertEqual(states.count("exhausted"), 15)
        self.assertEqual(self.ledger.count("u1"), 10)
        self.assertEqual(self.ledger.reserve(
            "u1", "ashby:open_1", "repeat-1")["status"], "already_delivered")
        self.assertEqual(self.ledger.count("u1"), 10)

    def test_expired_reservation_does_not_charge_and_ack_is_idempotent(self):
        self.assertEqual(self.ledger.reserve(
            "u1", "ashby:one", "req-one", now=1000, ttl_seconds=5
        )["status"], "reserved")
        self.assertEqual(self.ledger.acknowledge(
            "u1", "ashby:one", "req-one", now=1007
        )["status"], "reservation_expired")
        self.assertEqual(self.ledger.count("u1"), 0)
        self.assertEqual(self.ledger.reserve(
            "u1", "ashby:one", "req-two", now=1008
        )["status"], "reserved")
        self.assertEqual(self.ledger.acknowledge(
            "u1", "ashby:one", "req-two", now=1009
        )["status"], "delivered")
        self.assertEqual(self.ledger.acknowledge(
            "u1", "ashby:one", "req-two", now=1010
        )["status"], "already_delivered")

    def test_paid_is_verified_by_specific_active_sku_not_any_entitlement(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO entitlements VALUES(?,?,?,?,?,?)",
                         ("a", "u1", "legacy_stars", "active", 1, 9999999999))
        self.assertEqual(self.ledger.reserve(
            "u1", "ats:one", "req-one", now=1000)["free_remaining"], 9)
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO entitlements VALUES(?,?,?,?,?,?)",
                         ("b", "u1", "rolehint_unlimited", "active", 1, 2000))
        paid = self.ledger.reserve("u1", "ats:two", "req-two", now=1000)
        self.assertEqual(paid["status"], "reserved")
        self.assertEqual(paid["free_remaining"], 9)
        self.assertEqual(self.ledger.acknowledge(
            "u1", "ats:two", "req-two", now=1001)["status"], "delivered")
        with sqlite3.connect(self.db) as conn:
            tier = conn.execute("""SELECT entitlement_type FROM job_deliveries
              WHERE user_id='u1' AND canonical_id='ats:two'""").fetchone()[0]
            self.assertEqual(tier, "paid")
        self.assertEqual(self.ledger.reserve(
            "u1", "ats:three", "req-three", now=1950, ttl_seconds=120
        )["status"], "reserved")
        self.assertEqual(self.ledger.acknowledge(
            "u1", "ats:three", "req-three", now=2005
        )["status"], "entitlement_expired")

    def test_same_employer_requisition_for_different_users_is_independent(self):
        for user in ("u1", "u2"):
            request = "req-" + user
            self.assertEqual(self.ledger.reserve(
                user, "ashby:shared", request)["status"], "reserved")
            self.assertEqual(self.ledger.acknowledge(
                user, "ashby:shared", request)["status"], "delivered")
        self.assertEqual(self.ledger.count("u1"), 1)
        self.assertEqual(self.ledger.count("u2"), 1)


if __name__ == "__main__":
    unittest.main()
