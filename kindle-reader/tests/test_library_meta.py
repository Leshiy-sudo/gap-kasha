import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import library_meta  # noqa: E402
from PIL import Image  # noqa: E402


def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color=(1, 2, 3)).save(buffer, format="JPEG")
    return buffer.getvalue()


class LibraryMetaTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        temporary = Path(self._tmpdir.name)
        self._patches = [
            patch.object(library_meta, "_DB_PATH", temporary / "book_meta.db"),
            patch.object(library_meta, "_CUSTOM_COVERS_DIR", temporary / "custom_covers"),
        ]
        for p in self._patches:
            p.start()
        self.addCleanup(self._tmpdir.cleanup)
        for p in self._patches:
            self.addCleanup(p.stop)

    def test_missing_override_returns_none(self):
        self.assertIsNone(library_meta.get("local:/book.fb2"))
        self.assertEqual(library_meta.get_all(), {})

    def test_set_and_get_roundtrip(self):
        library_meta.set_override(
            "local:/book.fb2",
            title="Новое имя",
            author="Автор",
            series="Цикл",
            series_index=2,
            status="progress",
        )
        override = library_meta.get("local:/book.fb2")
        self.assertEqual(override.title, "Новое имя")
        self.assertEqual(override.author, "Автор")
        self.assertEqual(override.series, "Цикл")
        self.assertEqual(override.series_index, 2)
        self.assertEqual(override.status, "progress")
        self.assertFalse(override.has_custom_cover)

    def test_clearing_series_also_clears_series_index(self):
        library_meta.set_override(
            "local:/book.fb2",
            title=None,
            author=None,
            series="Цикл",
            series_index=3,
            status=None,
        )
        library_meta.set_override(
            "local:/book.fb2", title=None, author=None, series=None, series_index=5, status=None
        )
        override = library_meta.get("local:/book.fb2")
        self.assertIsNone(override.series)
        self.assertIsNone(override.series_index)

    def test_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            library_meta.set_override(
                "local:/book.fb2",
                title=None,
                author=None,
                series=None,
                series_index=None,
                status="unknown",
            )

    def test_save_custom_cover_sets_flag_and_survives_metadata_update(self):
        ok = library_meta.save_custom_cover("local:/book.fb2", _jpeg_bytes())
        self.assertTrue(ok)
        self.assertTrue(library_meta.get("local:/book.fb2").has_custom_cover)
        self.assertTrue(library_meta.custom_cover_path("local:/book.fb2").exists())

        library_meta.set_override(
            "local:/book.fb2", title="T", author=None, series=None, series_index=None, status=None
        )
        self.assertTrue(library_meta.get("local:/book.fb2").has_custom_cover)

    def test_save_custom_cover_rejects_non_image(self):
        ok = library_meta.save_custom_cover("local:/book.fb2", b"not an image")
        self.assertFalse(ok)
        self.assertIsNone(library_meta.get("local:/book.fb2"))

    def test_clear_custom_cover_removes_file_and_flag(self):
        library_meta.save_custom_cover("local:/book.fb2", _jpeg_bytes())
        library_meta.clear_custom_cover("local:/book.fb2")
        self.assertFalse(library_meta.custom_cover_path("local:/book.fb2").exists())
        self.assertFalse(library_meta.get("local:/book.fb2").has_custom_cover)

    def test_delete_override_removes_row_and_cover(self):
        library_meta.set_override(
            "local:/book.fb2", title="T", author=None, series=None, series_index=None, status=None
        )
        library_meta.save_custom_cover("local:/book.fb2", _jpeg_bytes())
        library_meta.delete_override("local:/book.fb2")
        self.assertIsNone(library_meta.get("local:/book.fb2"))
        self.assertFalse(library_meta.custom_cover_path("local:/book.fb2").exists())


if __name__ == "__main__":
    unittest.main()
