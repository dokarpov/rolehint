"""SQLite integrity and backup regressions use synthetic temporary files only."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.services.product_state.sqlite_integrity import (
    DATABASES, inspect_sqlite, backup_sqlite, backup_database_set,
)


class SQLiteIntegrityTests(unittest.TestCase):
    def test_online_backup_preserves_data_and_fts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "product_state.db"
            conn = sqlite3.connect(source)
            conn.executescript("""
                PRAGMA foreign_keys=ON;
                CREATE TABLE users(id TEXT PRIMARY KEY);
                CREATE TABLE user_jobs(
                    user_id TEXT REFERENCES users(id), job_id TEXT,
                    PRIMARY KEY(user_id,job_id));
                CREATE TABLE user_evidence(
                    user_id TEXT, evidence_id TEXT, PRIMARY KEY(user_id,evidence_id));
                CREATE VIRTUAL TABLE user_evidence_fts USING fts5(
                    user_id UNINDEXED,evidence_id UNINDEXED,claim);
                INSERT INTO users VALUES('u1');
                INSERT INTO user_jobs VALUES('u1','ashby:r1');
                INSERT INTO user_evidence VALUES('u1','e1');
                INSERT INTO user_evidence_fts VALUES('u1','e1','synthetic data');
            """)
            conn.commit()
            report = inspect_sqlite(source)
            self.assertTrue(report["integrity_ok"])
            self.assertEqual(report["foreign_key_errors"], 0)
            self.assertTrue(report["fts_count_matches"])

            target = root / "backup" / "product_state.db"
            result = backup_sqlite(source, target)
            self.assertTrue(target.exists())
            self.assertEqual(len(result["sha256"]), 64)
            conn.execute("INSERT INTO users VALUES('u2')")
            conn.commit()
            with sqlite3.connect(target) as restored:
                self.assertEqual(
                    restored.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
            with self.assertRaises(FileExistsError):
                backup_sqlite(source, target)
            conn.close()

    def test_invalid_foreign_key_backup_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "product_state.db"
            with sqlite3.connect(source) as conn:
                conn.executescript("""
                    CREATE TABLE users(id TEXT PRIMARY KEY);
                    CREATE TABLE user_jobs(user_id TEXT REFERENCES users(id), job_id TEXT);
                    INSERT INTO user_jobs VALUES('missing','x');
                """)
            self.assertEqual(inspect_sqlite(source)["foreign_key_errors"], 1)
            destination = root / "copy" / "product_state.db"
            with self.assertRaises(ValueError):
                backup_sqlite(source, destination)
            self.assertFalse(destination.exists())

    def test_multi_file_backup_explicitly_not_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            for name in DATABASES:
                with sqlite3.connect(source / name) as conn:
                    conn.execute("CREATE TABLE t(id INTEGER PRIMARY KEY)")
                    conn.execute("INSERT INTO t VALUES(1)")
            target = root / "snapshot"
            result = backup_database_set(source, target)
            self.assertIs(result["atomic_across_files"], False)
            self.assertEqual(len(result["databases"]), 3)
            self.assertTrue((target / "manifest.json").is_file())
            with self.assertRaises(FileExistsError):
                backup_database_set(source, target)


if __name__ == "__main__":
    unittest.main()
