import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import main  # noqa: E402


BOOK = {
    "path": "disk:/Книги/Book.fb2",
    "name": "Book.fb2",
    "size": 100,
    "added_at_display": "27.08.2026 12:00",
}


class LibraryViewTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def _patches(self):
        return (
            patch.object(main.auth, "is_authenticated", return_value=True),
            patch.object(
                main.books, "get_book_list", AsyncMock(return_value=[BOOK])
            ),
            patch.object(main.books, "last_remote_error", return_value=None),
            patch.object(main.metadata.book_metadata, "get_all", return_value={}),
            patch.object(main.metadata.book_metadata, "kick", Mock()),
            patch.object(main.metadata.book_metadata, "is_running", return_value=False),
            patch.object(main.library_meta, "get_all", return_value={}),
            patch.object(main.progress, "get_all", return_value={}),
        )

    def test_regular_browser_gets_modern_library(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
            response = self.client.get(
                "/", headers={"user-agent": "Mozilla/5.0 Chrome/140"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Сказки Лешего", response.text)
        self.assertIn("style_modern.css", response.text)
        self.assertIn("Редактировать", response.text)

    def test_kindle_gets_lightweight_library(self):
        patches = self._patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7]:
            response = self.client.get(
                "/", headers={"user-agent": "Mozilla/5.0 Kindle/3.0"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Сказки Лешего", response.text)
        self.assertNotIn("style_modern.css", response.text)
        self.assertIn("style.css", response.text)


if __name__ == "__main__":
    unittest.main()
