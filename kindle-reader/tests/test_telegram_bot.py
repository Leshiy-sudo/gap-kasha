import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import telegram_bot, yandex_disk  # noqa: E402


class FakeTelegramClient:
    def __init__(self, data: bytes = b"book-data"):
        self.data = data
        self.messages: list[tuple[int, str]] = []
        self.downloads: list[str] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))

    async def download_file(self, file_id: str) -> bytes:
        self.downloads.append(file_id)
        return self.data


def document_update(
    *, user_id: int = 42, filename: str = "book.fb2", size: int = 100
) -> dict:
    return {
        "update_id": 10,
        "message": {
            "from": {"id": user_id},
            "chat": {"id": user_id, "type": "private"},
            "document": {
                "file_id": "telegram-file-id",
                "file_name": filename,
                "file_size": size,
            },
        },
    }


class FilenameTests(unittest.TestCase):
    def test_removes_path_and_keeps_supported_suffix(self):
        self.assertEqual(
            telegram_bot.normalize_book_filename("../folder/My Book.FB2"),
            "My Book.FB2",
        )

    def test_rejects_unsupported_format(self):
        with self.assertRaisesRegex(ValueError, "Поддерживаются"):
            telegram_bot.normalize_book_filename("book.epub")

    def test_limits_filename_length(self):
        name = telegram_bot.normalize_book_filename("a" * 300 + ".fb2.zip")
        self.assertEqual(len(name), 180)
        self.assertTrue(name.endswith(".fb2.zip"))


class OffsetStoreTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = telegram_bot.OffsetStore(Path(temporary) / "offset.txt")
            self.assertIsNone(store.load())
            store.save(123)
            self.assertEqual(store.load(), 123)


class UpdateHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_imports_document_for_allowed_user(self):
        client = FakeTelegramClient()
        upload = AsyncMock(return_value="disk:/Книги/book.fb2")
        with patch.object(yandex_disk, "upload_book", upload):
            await telegram_bot.handle_update(
                client,
                document_update(),
                allowed_user_ids=frozenset({42}),
                max_file_size=20 * 1024 * 1024,
                reader_url="https://reader.example",
            )

        upload.assert_awaited_once_with(b"book-data", "book.fb2")
        self.assertEqual(client.downloads, ["telegram-file-id"])
        self.assertIn("добавлена", client.messages[-1][1])
        self.assertIn("https://reader.example", client.messages[-1][1])

    async def test_rejects_unauthorized_user_before_download(self):
        client = FakeTelegramClient()
        await telegram_bot.handle_update(
            client,
            document_update(user_id=99),
            allowed_user_ids=frozenset({42}),
            max_file_size=20 * 1024 * 1024,
            reader_url="https://reader.example",
        )
        self.assertEqual(client.downloads, [])
        self.assertIn("закрыт", client.messages[-1][1])

    async def test_rejects_large_file_before_download(self):
        client = FakeTelegramClient()
        await telegram_bot.handle_update(
            client,
            document_update(size=21 * 1024 * 1024),
            allowed_user_ids=frozenset({42}),
            max_file_size=20 * 1024 * 1024,
            reader_url="https://reader.example",
        )
        self.assertEqual(client.downloads, [])
        self.assertIn("слишком большой", client.messages[-1][1])

    async def test_reports_existing_book(self):
        client = FakeTelegramClient()
        upload = AsyncMock(
            side_effect=yandex_disk.YandexDiskConflictError("already exists")
        )
        with patch.object(yandex_disk, "upload_book", upload):
            await telegram_bot.handle_update(
                client,
                document_update(),
                allowed_user_ids=frozenset({42}),
                max_file_size=20 * 1024 * 1024,
                reader_url="https://reader.example",
            )
        self.assertIn("уже есть", client.messages[-1][1])


if __name__ == "__main__":
    unittest.main()
