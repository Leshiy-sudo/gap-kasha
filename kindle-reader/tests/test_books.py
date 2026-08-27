import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import books, yandex_disk  # noqa: E402


class GetBookFormatRoutingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        books._book_cache.clear()
        books._fb2_conversion_cache.clear()

    async def test_epub_is_converted_before_parsing(self):
        parse = unittest.mock.Mock(return_value=("Title", [("text", False)]))
        with (
            patch.object(books, "download_book", AsyncMock(return_value=b"epub")),
            patch.object(
                books.convert,
                "convert_to_fb2",
                AsyncMock(return_value=b"<FictionBook/>")
            ) as conversion,
            patch.object(books, "parse_fb2", parse),
        ):
            result = await books.get_book("disk:/Книги/Book.epub")

        conversion.assert_awaited_once_with(b"epub", "Book.epub")
        parse.assert_called_once_with(b"<FictionBook/>")
        self.assertEqual(result["title"], "Title")

    async def test_conversion_result_is_cached(self):
        conversion = AsyncMock(return_value=b"<FictionBook/>")
        with patch.object(books.convert, "convert_to_fb2", conversion):
            first = await books.get_fb2_bytes("disk:/Книги/B.mobi", "B.mobi", b"one")
            second = await books.get_fb2_bytes("disk:/Книги/B.mobi", "B.mobi", b"one")

        conversion.assert_awaited_once()
        self.assertEqual(first, second)

    async def test_fb2_is_not_converted(self):
        conversion = AsyncMock()
        parse = unittest.mock.Mock(return_value=("Title", []))
        with (
            patch.object(books, "download_book", AsyncMock(return_value=b"fb2")),
            patch.object(books.convert, "convert_to_fb2", conversion),
            patch.object(books, "parse_fb2", parse),
        ):
            await books.get_book("disk:/Книги/Book.fb2")

        conversion.assert_not_awaited()
        parse.assert_called_once_with(b"fb2")


class LibraryFailoverTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        books._list_cache = {"items": None, "ts": 0.0}

    async def test_yandex_failure_keeps_last_successful_list(self):
        cached_item = {
            "path": "disk:/Книги/Book.fb2",
            "name": "Book.fb2",
            "size": 4,
            "created": "2026-08-25T11:30:00+00:00",
            "added_at_display": "25.08.2026 16:30",
        }
        books._list_cache = {"items": [cached_item], "ts": 0.0}
        with patch.object(
            books.yandex_disk,
            "list_books",
            AsyncMock(side_effect=yandex_disk.YandexDiskError("403")),
        ):
            items = await books.get_book_list()

        self.assertEqual(items[0]["name"], "Book.fb2")
        self.assertEqual(items[0]["added_at_display"], "25.08.2026 16:30")
        self.assertEqual(books.last_remote_error(), "403")


if __name__ == "__main__":
    unittest.main()
