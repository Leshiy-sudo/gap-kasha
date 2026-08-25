import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import config, local_library  # noqa: E402


class LocalLibraryTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_list_and_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(config, "LOCAL_BOOKS_PATH", Path(temporary)):
                path = await local_library.save_book(b"book", "Book.fb2")
                items = await local_library.list_books()
                data = await local_library.download_book(path)

        self.assertEqual(path, "local:/Book.fb2")
        self.assertEqual(items[0]["name"], "Book.fb2")
        self.assertEqual(data, b"book")

    async def test_does_not_overwrite_existing_book(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(config, "LOCAL_BOOKS_PATH", Path(temporary)):
                await local_library.save_book(b"first", "Book.fb2")
                with self.assertRaises(local_library.LocalLibraryConflictError):
                    await local_library.save_book(b"second", "Book.fb2")

    async def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(config, "LOCAL_BOOKS_PATH", Path(temporary)):
                with self.assertRaises(local_library.LocalLibraryError):
                    await local_library.download_book("local:/../secret.fb2")


if __name__ == "__main__":
    unittest.main()
