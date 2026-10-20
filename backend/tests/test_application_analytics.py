import sqlite3
import unittest

from app.services.product_state.application_analytics import migrate, record_event, timeline, funnel

class ApplicationAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
          CREATE TABLE users(id TEXT PRIMARY KEY);
          CREATE TABLE user_jobs(user_id TEXT,job_id TEXT,PRIMARY KEY(user_id,job_id));
          INSERT INTO users VALUES ('u1'),('u2');
          INSERT INTO user_jobs VALUES ('u1','j1'),('u1','j2'),('u2','j3');
        """)
        migrate(self.db)

    def tearDown(self):
        self.db.close()

    def test_migration_repeatable(self):
        migrate(self.db)
        self.assertEqual(funnel(self.db,"u1")["applied"],0)

    def test_confirmed_reach_and_deduplication(self):
        record_event(self.db,"u1","j1","apply-1","applied","user",True,1)
        record_event(self.db,"u1","j1","apply-1","applied","user",True,1)
        record_event(self.db,"u1","j1","email-2","interview","email",False,2)
        self.assertEqual(funnel(self.db,"u1")["applied"],1)
        self.assertEqual(funnel(self.db,"u1")["interview"],0)
        self.assertEqual(len(timeline(self.db,"u1","j1")),2)

    def test_user_isolation_and_missing_job(self):
        record_event(self.db,"u2","j3","apply","applied","user",True)
        self.assertEqual(funnel(self.db,"u1")["applied"],0)
        self.assertEqual(timeline(self.db,"u1","j3"),[])
        with self.assertRaises(ValueError):
            record_event(self.db,"u1","j3","wrong","applied","user",True)

    def test_invalid_stage_rejected(self):
        with self.assertRaises(ValueError):
            record_event(self.db,"u1","j1","bad","invented","user",True)

if __name__ == "__main__":
    unittest.main()
