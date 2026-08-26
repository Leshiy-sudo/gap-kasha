from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from . import books
from .parsers.fb2 import parse_fb2_metadata

logger = logging.getLogger("kindle_reader.metadata")

_PROJECT_DATA = Path(__file__).resolve().parent.parent / "data"
_COVER_MAX_SIZE = (160, 240)
_COVER_JPEG_QUALITY = 70
_COVER_MAX_BYTES = 10 * 1024 * 1024
_COVER_MAX_PIXELS = 20_000_000
_ENRICH_CONCURRENCY = 2
_ENRICH_BATCH_SIZE = 10


@dataclass(frozen=True)
class BookMeta:
    size: int
    title: str | None
    author: str | None
    has_cover: bool


class BookMetadataStore:
    """Кэш названий, авторов и уменьшенных обложек."""

    def __init__(
        self,
        db_path: Path | None = None,
        covers_dir: Path | None = None,
    ):
        self._db_path = db_path or _PROJECT_DATA / "book_meta.db"
        self._covers_dir = covers_dir or _PROJECT_DATA / "covers"
        self._task: asyncio.Task | None = None

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS book_meta ("
            "path TEXT PRIMARY KEY, "
            "size INTEGER NOT NULL, "
            "title TEXT, "
            "author TEXT, "
            "has_cover INTEGER NOT NULL, "
            "updated_at TEXT NOT NULL DEFAULT (datetime('now'))"
            ")"
        )
        return conn

    def cover_path(self, book_path: str) -> Path:
        digest = hashlib.sha256(book_path.encode("utf-8")).hexdigest()
        return self._covers_dir / f"{digest}.jpg"

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def get_all(self) -> dict[str, BookMeta]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT path, size, title, author, has_cover FROM book_meta"
            ).fetchall()
        return {
            path: BookMeta(
                size=size,
                title=title,
                author=author,
                has_cover=bool(has_cover),
            )
            for path, size, title, author, has_cover in rows
        }

    def get(self, path: str) -> BookMeta | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT size, title, author, has_cover "
                "FROM book_meta WHERE path = ?",
                (path,),
            ).fetchone()
        if row is None:
            return None
        size, title, author, has_cover = row
        return BookMeta(
            size=size,
            title=title,
            author=author,
            has_cover=bool(has_cover),
        )

    def _store(self, path: str, meta: BookMeta) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO book_meta "
                "(path, size, title, author, has_cover, updated_at) "
                "VALUES (?, ?, ?, ?, ?, datetime('now')) "
                "ON CONFLICT(path) DO UPDATE SET "
                "size = excluded.size, title = excluded.title, "
                "author = excluded.author, has_cover = excluded.has_cover, "
                "updated_at = excluded.updated_at",
                (path, meta.size, meta.title, meta.author, int(meta.has_cover)),
            )
            conn.commit()

    def kick(self, visible_items: list[dict]) -> None:
        """Обработать только ограниченную порцию книг текущей страницы."""
        if self.is_running():
            return
        cached = self.get_all()
        pending = [
            item
            for item in visible_items
            if self._needs_enrichment(item, cached)
        ][:_ENRICH_BATCH_SIZE]
        if pending:
            self._task = asyncio.create_task(self._enrich_all(pending))

    @staticmethod
    def _needs_enrichment(item: dict, cached: dict[str, BookMeta]) -> bool:
        meta = cached.get(item["path"])
        return meta is None or meta.size != item.get("size", 0)

    async def _enrich_all(self, items: list[dict]) -> None:
        semaphore = asyncio.Semaphore(_ENRICH_CONCURRENCY)

        async def process(item: dict) -> None:
            async with semaphore:
                try:
                    await self._enrich_one(item)
                except Exception:
                    logger.exception(
                        "Failed to enrich book metadata for %s", item["path"]
                    )

        await asyncio.gather(*(process(item) for item in items))

    async def _enrich_one(self, item: dict) -> None:
        path = item["path"]
        size = int(item.get("size", 0))
        name = item["name"]

        if name.lower().endswith(".txt"):
            self._store(
                path,
                BookMeta(size=size, title=None, author=None, has_cover=False),
            )
            return

        data = await books.download_book(path)
        fb2_data = await books.get_fb2_bytes(path, name, data)
        info = parse_fb2_metadata(fb2_data)

        has_cover = False
        if info.cover_bytes:
            has_cover = await asyncio.to_thread(
                self._save_cover, path, info.cover_bytes
            )
        if not has_cover:
            self.cover_path(path).unlink(missing_ok=True)

        self._store(
            path,
            BookMeta(
                size=size,
                title=info.title,
                author=info.author,
                has_cover=has_cover,
            ),
        )

    def _save_cover(self, path: str, cover_bytes: bytes) -> bool:
        if len(cover_bytes) > _COVER_MAX_BYTES:
            return False
        try:
            with Image.open(io.BytesIO(cover_bytes)) as image:
                if image.width * image.height > _COVER_MAX_PIXELS:
                    return False
                image.thumbnail(_COVER_MAX_SIZE)
                prepared = image.convert("L")
                self._covers_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                self._covers_dir.chmod(0o700)
                destination = self.cover_path(path)
                prepared.save(
                    destination,
                    format="JPEG",
                    quality=_COVER_JPEG_QUALITY,
                    optimize=True,
                )
                destination.chmod(0o600)
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError):
            logger.warning("Rejected cover image for %s", path)
            return False
        return True

    def delete(self, path: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM book_meta WHERE path = ?", (path,))
            conn.commit()
        self.cover_path(path).unlink(missing_ok=True)


book_metadata = BookMetadataStore()
