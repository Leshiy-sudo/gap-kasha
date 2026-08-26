import base64
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from PIL import Image  # noqa: E402
from app import metadata  # noqa: E402


def make_cover() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (300, 400), color=(120, 50, 10)).save(buffer, "JPEG")
    return buffer.getvalue()


class MetadataStoreTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.store = metadata.BookMetadataStore(
            db_path=root / "book_meta.db", covers_dir=root / "covers"
        )
        self.addCleanup(self.temporary.cleanup)

    def test_store_get_and_delete_roundtrip(self):
        value = metadata.BookMeta(42, "Название", "Автор", False)
        self.store._store("local:/book.fb2", value)
        self.assertEqual(self.store.get("local:/book.fb2"), value)
        self.store.delete("local:/book.fb2")
        self.assertIsNone(self.store.get("local:/book.fb2"))

    async def test_txt_skips_download(self):
        item = {"path": "local:/book.txt", "name": "book.txt", "size": 5}
        with patch.object(
            metadata.books, "download_book", AsyncMock(side_effect=AssertionError)
        ):
            await self.store._enrich_one(item)
        self.assertEqual(
            self.store.get(item["path"]), metadata.BookMeta(5, None, None, False)
        )

    async def test_extracts_and_reduces_cover(self):
        cover = make_cover()
        fb2 = f'''<FictionBook xmlns="urn:fb2" xmlns:l="http://www.w3.org/1999/xlink">
          <description><title-info><book-title>Книга</book-title>
          <author><first-name>Автор</first-name></author>
          <coverpage><image l:href="#c"/></coverpage></title-info></description>
          <body><section><p>Текст</p></section></body>
          <binary id="c">{base64.b64encode(cover).decode()}</binary>
        </FictionBook>'''.encode()
        item = {"path": "local:/book.fb2", "name": "book.fb2", "size": 99}
        with patch.object(metadata.books, "download_book", AsyncMock(return_value=fb2)):
            await self.store._enrich_one(item)

        value = self.store.get(item["path"])
        self.assertEqual((value.title, value.author), ("Книга", "Автор"))
        self.assertTrue(value.has_cover)
        with Image.open(self.store.cover_path(item["path"])) as saved:
            self.assertLessEqual(saved.width, 160)
            self.assertLessEqual(saved.height, 240)
            self.assertEqual(saved.mode, "L")

    async def test_epub_uses_conversion_path(self):
        fb2 = b'<FictionBook xmlns="urn:fb2"><description><title-info><book-title>EPUB</book-title></title-info></description><body/></FictionBook>'
        item = {"path": "local:/book.epub", "name": "book.epub", "size": 8}
        with (
            patch.object(metadata.books, "download_book", AsyncMock(return_value=b"epub")),
            patch.object(metadata.books, "get_fb2_bytes", AsyncMock(return_value=fb2)) as conversion,
        ):
            await self.store._enrich_one(item)

        conversion.assert_awaited_once_with(item["path"], item["name"], b"epub")
        self.assertEqual(self.store.get(item["path"]).title, "EPUB")


if __name__ == "__main__":
    unittest.main()
