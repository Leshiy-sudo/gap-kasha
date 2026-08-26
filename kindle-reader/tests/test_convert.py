import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import convert  # noqa: E402


class FakeProcess:
    def __init__(self, returncode: int = 0, stderr: bytes = b""):
        self.returncode = returncode
        self._stderr = stderr

    async def communicate(self):
        return b"", self._stderr

    def kill(self):
        self.returncode = -9


class SourceExtensionTests(unittest.TestCase):
    def test_detects_supported_sources(self):
        for name, expected in (
            ("book.txt", ".txt"),
            ("book.epub", ".epub"),
            ("book.mobi", ".mobi"),
            ("book.fb2", ".fb2"),
            ("book.fb2.zip", ".fb2"),
        ):
            self.assertEqual(convert._source_extension(name), expected)


class ConvertTests(unittest.IsolatedAsyncioTestCase):
    async def test_convert_to_fb2_uses_real_source_extension(self):
        captured = {}

        async def fake_exec(program, src, dst, **kwargs):
            captured["source"] = Path(src).suffix
            captured["data"] = Path(src).read_bytes()
            Path(dst).write_bytes(b"<FictionBook/>")
            return FakeProcess()

        with patch.object(convert.asyncio, "create_subprocess_exec", fake_exec):
            result = await convert.convert_to_fb2(b"epub-bytes", "Book.epub")

        self.assertEqual(captured, {"source": ".epub", "data": b"epub-bytes"})
        self.assertEqual(result, b"<FictionBook/>")

    async def test_epub_is_not_unwrapped_as_fb2_zip(self):
        captured = {}

        async def fake_exec(program, src, dst, **kwargs):
            captured["data"] = Path(src).read_bytes()
            Path(dst).write_bytes(b"mobi-bytes")
            return FakeProcess()

        epub_bytes = b"PK\x03\x04" + b"\x00" * 20
        with patch.object(convert.asyncio, "create_subprocess_exec", fake_exec):
            result = await convert.convert_book(epub_bytes, "Book.epub", "mobi")

        self.assertEqual(captured["data"], epub_bytes)
        self.assertEqual(result, b"mobi-bytes")

    async def test_reports_converter_failure(self):
        async def fake_exec(program, src, dst, **kwargs):
            return FakeProcess(returncode=1, stderr=b"boom")

        with patch.object(convert.asyncio, "create_subprocess_exec", fake_exec):
            with self.assertRaisesRegex(convert.ConversionError, "boom"):
                await convert.convert_to_fb2(b"data", "Book.mobi")

    async def test_reports_missing_calibre(self):
        with patch.object(
            convert.asyncio,
            "create_subprocess_exec",
            side_effect=FileNotFoundError,
        ):
            with self.assertRaisesRegex(convert.ConversionError, "Calibre"):
                await convert.convert_to_fb2(b"data", "Book.epub")


if __name__ == "__main__":
    unittest.main()
