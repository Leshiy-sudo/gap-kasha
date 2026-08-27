import os
import unittest
from unittest.mock import Mock

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import books, main  # noqa: E402


class AddedAtTests(unittest.TestCase):
    def test_formats_added_at_in_reader_timezone(self):
        self.assertEqual(
            books.format_added_at("2026-08-25T11:30:00+00:00"),
            "25.08.2026 16:30",
        )

    def test_handles_missing_or_invalid_date(self):
        self.assertEqual(books.format_added_at(None), "Дата неизвестна")
        self.assertEqual(books.format_added_at("not-a-date"), "Дата неизвестна")


class PaginationTests(unittest.TestCase):
    def test_slices_items_and_clamps_page(self):
        items = [{"name": str(number)} for number in range(23)]

        page_items, page, total_pages = main._paginate_items(items, 2)
        self.assertEqual(
            [item["name"] for item in page_items],
            [str(number) for number in range(10, 20)],
        )
        self.assertEqual((page, total_pages), (2, 3))

        last_items, page, total_pages = main._paginate_items(items, 99)
        self.assertEqual(
            [item["name"] for item in last_items], ["20", "21", "22"]
        )
        self.assertEqual((page, total_pages), (3, 3))

    def test_builds_compact_page_window(self):
        self.assertEqual(
            main._pagination_window(20, 40),
            [1, None, 18, 19, 20, 21, 22, None, 40],
        )


class LibraryUrlTests(unittest.TestCase):
    def test_preserves_search_author_page_and_deleted_message(self):
        url = main._library_url(
            page=3,
            q="война и мир",
            author="Лев Толстой",
            deleted="Книга.fb2",
        )
        self.assertIn("page=3", url)
        self.assertIn("q=%D0%B2%D0%BE%D0%B9%D0%BD%D0%B0", url)
        self.assertIn("author=%D0%9B%D0%B5%D0%B2", url)
        self.assertIn("deleted=%D0%9A%D0%BD%D0%B8%D0%B3%D0%B0.fb2", url)


class BrowserModeTests(unittest.TestCase):
    @staticmethod
    def request(user_agent: str):
        request = Mock()
        request.headers = {"user-agent": user_agent}
        return request

    def test_detects_kindle_and_silk_browsers(self):
        self.assertTrue(main._is_kindle(self.request("Mozilla/5.0 Kindle/3.0")))
        self.assertTrue(main._is_kindle(self.request("Mozilla/5.0 Silk/3.13")))

    def test_uses_modern_mode_for_regular_browser(self):
        self.assertFalse(main._is_kindle(self.request("Mozilla/5.0 Chrome/140")))
