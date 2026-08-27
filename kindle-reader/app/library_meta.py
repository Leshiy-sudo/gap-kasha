from __future__ import annotations

import hashlib
import io
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "book_meta.db"
_CUSTOM_COVERS_DIR = Path(__file__).resolve().parent.parent / "data" / "custom_covers"
_COVER_MAX_SIZE = (200, 300)
_COVER_JPEG_QUALITY = 72
_COVER_MAX_BYTES = 10 * 1024 * 1024
_COVER_MAX_PIXELS = 20_000_000

STATUS_CHOICES = ("progress", "read", "planned")
STATUS_LABELS = {
    None: "Без статуса",
    "progress": "В процессе",
    "read": "Прочитано",
    "planned": "В планах",
}


@dataclass(frozen=True)
class BookOverride:
    title: str | None
    author: str | None
    series: str | None
    series_index: int | None
    status: str | None
    has_custom_cover: bool


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS book_overrides ("
        "path TEXT PRIMARY KEY, "
        "title TEXT, "
        "author TEXT, "
        "series TEXT, "
        "series_index INTEGER, "
        "status TEXT, "
        "has_custom_cover INTEGER NOT NULL DEFAULT 0, "
        "updated_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    return conn


def custom_cover_path(book_path: str) -> Path:
    """Путь к файлу пользовательской обложки (имя — хэш пути книги)."""
    digest = hashlib.sha1(book_path.encode("utf-8")).hexdigest()
    return _CUSTOM_COVERS_DIR / f"{digest}.jpg"


def get(path: str) -> BookOverride | None:
    """Ручные правки одной книги, если они есть."""
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT title, author, series, series_index, status, has_custom_cover "
            "FROM book_overrides WHERE path = ?",
            (path,),
        ).fetchone()
    if row is None:
        return None
    title, author, series, series_index, status, has_custom_cover = row
    return BookOverride(
        title=title,
        author=author,
        series=series,
        series_index=series_index,
        status=status,
        has_custom_cover=bool(has_custom_cover),
    )


def get_all() -> dict[str, BookOverride]:
    """Все ручные правки, путь → BookOverride."""
    with closing(_connect()) as conn, conn:
        rows = conn.execute(
            "SELECT path, title, author, series, series_index, status, has_custom_cover "
            "FROM book_overrides"
        ).fetchall()
    return {
        path: BookOverride(
            title=title,
            author=author,
            series=series,
            series_index=series_index,
            status=status,
            has_custom_cover=bool(has_custom_cover),
        )
        for path, title, author, series, series_index, status, has_custom_cover in rows
    }


def set_override(
    path: str,
    *,
    title: str | None,
    author: str | None,
    series: str | None,
    series_index: int | None,
    status: str | None,
) -> None:
    """Сохранить ручные правки метаданных книги. `None`/пустая строка в
    поле — значит «убрать переопределение», а не «записать пустую строку»."""
    if status is not None and status not in STATUS_CHOICES:
        raise ValueError(f"Неизвестный статус чтения: {status!r}")
    if not series:
        series_index = None

    existing = get(path)
    has_custom_cover = existing.has_custom_cover if existing else False

    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO book_overrides "
            "(path, title, author, series, series_index, status, has_custom_cover, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now')) "
            "ON CONFLICT(path) DO UPDATE SET "
            "title = excluded.title, author = excluded.author, series = excluded.series, "
            "series_index = excluded.series_index, status = excluded.status, "
            "updated_at = excluded.updated_at",
            (path, title, author, series, series_index, status, int(has_custom_cover)),
        )


def delete_override(path: str) -> None:
    """Удалить переопределения и файл пользовательской обложки книги."""
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM book_overrides WHERE path = ?", (path,))
    clear_custom_cover(path)


def _ensure_covers_dir() -> None:
    _CUSTOM_COVERS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    _CUSTOM_COVERS_DIR.chmod(0o700)


def save_custom_cover(path: str, image_bytes: bytes) -> bool:
    """Сохранить загруженную пользователем обложку как миниатюру JPEG и
    отметить книгу флагом has_custom_cover. False — если файл не картинка."""
    if len(image_bytes) > _COVER_MAX_BYTES:
        return False
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            if image.width * image.height > _COVER_MAX_PIXELS:
                return False
            image.thumbnail(_COVER_MAX_SIZE)
            prepared = image.convert("RGB")
            _ensure_covers_dir()
            destination = custom_cover_path(path)
            prepared.save(destination, format="JPEG", quality=_COVER_JPEG_QUALITY)
            destination.chmod(0o600)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError):
        return False

    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO book_overrides (path, has_custom_cover, updated_at) "
            "VALUES (?, 1, datetime('now')) "
            "ON CONFLICT(path) DO UPDATE SET "
            "has_custom_cover = 1, updated_at = excluded.updated_at",
            (path,),
        )
    return True


def clear_custom_cover(path: str) -> None:
    custom_cover_path(path).unlink(missing_ok=True)
    with closing(_connect()) as conn, conn:
        conn.execute(
            "UPDATE book_overrides SET has_custom_cover = 0 WHERE path = ?", (path,)
        )
