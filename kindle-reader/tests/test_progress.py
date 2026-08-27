import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from app import progress


class PerUserProgressTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary.name) / "progress.db"
        self.path_patch = patch.object(progress, "_DB_PATH", self.db_path)
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.addCleanup(self.temporary.cleanup)

    def test_users_have_independent_pages(self):
        progress.set_page("talgat", "disk:/Book.fb2", 12)
        progress.set_page("igor", "disk:/Book.fb2", 3)

        self.assertEqual(progress.get_page("talgat", "disk:/Book.fb2"), 12)
        self.assertEqual(progress.get_page("igor", "disk:/Book.fb2"), 3)
        self.assertEqual(progress.get_all("talgat"), {"disk:/Book.fb2": 12})
        self.assertEqual(progress.get_all("igor"), {"disk:/Book.fb2": 3})

    def test_legacy_progress_is_migrated_to_talgat(self):
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                "CREATE TABLE progress (book_path TEXT PRIMARY KEY, page INTEGER NOT NULL, "
                "updated_at TEXT NOT NULL DEFAULT (datetime('now')))"
            )
            conn.execute(
                "INSERT INTO progress (book_path, page) VALUES (?, ?)",
                ("disk:/Legacy.fb2", 27),
            )

        self.assertEqual(progress.get_page("talgat", "disk:/Legacy.fb2"), 27)
        self.assertIsNone(progress.get_page("igor", "disk:/Legacy.fb2"))

    def test_deleting_book_clears_every_users_progress(self):
        progress.set_page("talgat", "disk:/Book.fb2", 12)
        progress.set_page("igor", "disk:/Book.fb2", 3)
        progress.delete("disk:/Book.fb2")
        self.assertIsNone(progress.get_page("talgat", "disk:/Book.fb2"))
        self.assertIsNone(progress.get_page("igor", "disk:/Book.fb2"))


if __name__ == "__main__":
    unittest.main()
