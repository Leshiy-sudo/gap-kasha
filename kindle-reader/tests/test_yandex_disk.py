import os
import unittest
from unittest.mock import patch

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("YANDEX_BOOKS_PATH", "/Книги")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import yandex_disk  # noqa: E402


class FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict:
        return self._body


class FakeAsyncClient:
    def __init__(
        self,
        get_response: FakeResponse | None = None,
        put_response: FakeResponse | None = None,
        delete_response: FakeResponse | None = None,
    ):
        self.get_response = get_response
        self.put_response = put_response
        self.delete_response = delete_response
        self.get_calls: list[tuple[str, dict]] = []
        self.put_calls: list[tuple[str, bytes]] = []
        self.delete_calls: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, url: str, **kwargs):
        self.get_calls.append((url, kwargs))
        return self.get_response

    async def put(self, url: str, *, content: bytes):
        self.put_calls.append((url, content))
        return self.put_response

    async def delete(self, url: str, **kwargs):
        self.delete_calls.append((url, kwargs))
        return self.delete_response


class UploadBookTests(unittest.IsolatedAsyncioTestCase):
    async def test_uploads_into_configured_books_folder(self):
        client = FakeAsyncClient(
            FakeResponse(200, {"href": "https://upload.example/file"}),
            FakeResponse(201),
        )
        with (
            patch.object(yandex_disk.config, "YANDEX_BOOKS_PATH", "/Книги"),
            patch.object(yandex_disk.httpx, "AsyncClient", return_value=client),
        ):
            path = await yandex_disk.upload_book(b"book-data", "book.fb2")

        self.assertEqual(path, "disk:/Книги/book.fb2")
        self.assertEqual(client.get_calls[0][1]["params"]["path"], "/Книги/book.fb2")
        self.assertEqual(
            client.put_calls, [("https://upload.example/file", b"book-data")]
        )

    async def test_reports_name_conflict(self):
        client = FakeAsyncClient(FakeResponse(409))
        with patch.object(yandex_disk.httpx, "AsyncClient", return_value=client):
            with self.assertRaises(yandex_disk.YandexDiskConflictError):
                await yandex_disk.upload_book(b"book-data", "book.fb2")
        self.assertEqual(client.put_calls, [])


class ListBooksTests(unittest.IsolatedAsyncioTestCase):
    async def test_requests_added_date_fields(self):
        client = FakeAsyncClient(
            get_response=FakeResponse(
                200,
                {
                    "_embedded": {
                        "items": [
                            {
                                "name": "Book.fb2",
                                "path": "disk:/Книги/Book.fb2",
                                "type": "file",
                                "created": "2026-08-25T11:30:00+00:00",
                            }
                        ]
                    }
                },
            )
        )
        with patch.object(yandex_disk.httpx, "AsyncClient", return_value=client):
            items = await yandex_disk.list_books()

        self.assertEqual(items[0]["created"], "2026-08-25T11:30:00+00:00")
        fields = client.get_calls[0][1]["params"]["fields"]
        self.assertIn("items.created", fields)
        self.assertIn("items.modified", fields)


class DeleteBookTests(unittest.IsolatedAsyncioTestCase):
    async def test_moves_book_to_yandex_trash(self):
        client = FakeAsyncClient(delete_response=FakeResponse(204))
        with (
            patch.object(yandex_disk.config, "YANDEX_BOOKS_PATH", "/Книги"),
            patch.object(yandex_disk.httpx, "AsyncClient", return_value=client),
        ):
            await yandex_disk.delete_book("disk:/Книги/Book.fb2")

        self.assertEqual(len(client.delete_calls), 1)
        _, kwargs = client.delete_calls[0]
        self.assertEqual(kwargs["params"]["path"], "/Книги/Book.fb2")
        self.assertEqual(kwargs["params"]["permanently"], "false")

    async def test_rejects_deletion_outside_books_folder(self):
        with patch.object(yandex_disk.config, "YANDEX_BOOKS_PATH", "/Книги"):
            with self.assertRaisesRegex(yandex_disk.YandexDiskError, "вне"):
                await yandex_disk.delete_book("disk:/Документы/secret.txt")


if __name__ == "__main__":
    unittest.main()
