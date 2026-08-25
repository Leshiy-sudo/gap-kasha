from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from . import config

PATH_PREFIX = "local:/"


class LocalLibraryError(RuntimeError):
    pass


class LocalLibraryConflictError(LocalLibraryError):
    pass


def _ensure_directory() -> None:
    try:
        config.LOCAL_BOOKS_PATH.mkdir(parents=True, exist_ok=True, mode=0o700)
        config.LOCAL_BOOKS_PATH.chmod(0o700)
    except OSError as exc:
        raise LocalLibraryError("Не удалось подготовить локальную библиотеку") from exc


def _file_path(book_path: str) -> Path:
    if not book_path.startswith(PATH_PREFIX):
        raise LocalLibraryError("Некорректный путь локальной книги")
    name = book_path[len(PATH_PREFIX) :]
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise LocalLibraryError("Некорректный путь локальной книги")
    return config.LOCAL_BOOKS_PATH / name


def _save(data: bytes, name: str) -> str:
    path = _file_path(f"{PATH_PREFIX}{name}")
    _ensure_directory()
    try:
        with path.open("xb") as destination:
            destination.write(data)
        path.chmod(0o600)
    except FileExistsError as exc:
        raise LocalLibraryConflictError("Книга уже существует") from exc
    except OSError as exc:
        raise LocalLibraryError("Не удалось сохранить локальную книгу") from exc
    return f"{PATH_PREFIX}{name}"


async def save_book(data: bytes, name: str) -> str:
    return await asyncio.to_thread(_save, data, name)


def _list_books() -> list[dict]:
    try:
        _ensure_directory()
        paths = [path for path in config.LOCAL_BOOKS_PATH.iterdir() if path.is_file()]
    except OSError as exc:
        raise LocalLibraryError("Не удалось прочитать локальную библиотеку") from exc

    items = []
    for path in paths:
        if not path.name.lower().endswith((".fb2", ".fb2.zip", ".txt")):
            continue
        stat = path.stat()
        items.append(
            {
                "name": path.name,
                "path": f"{PATH_PREFIX}{path.name}",
                "type": "file",
                "size": stat.st_size,
                "created": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
            }
        )
    items.sort(key=lambda item: item["name"].lower())
    return items


async def list_books() -> list[dict]:
    return await asyncio.to_thread(_list_books)


def _download(book_path: str) -> bytes:
    path = _file_path(book_path)
    try:
        return path.read_bytes()
    except OSError as exc:
        raise LocalLibraryError("Не удалось открыть локальную книгу") from exc


async def download_book(book_path: str) -> bytes:
    return await asyncio.to_thread(_download, book_path)


def _delete(book_path: str) -> None:
    path = _file_path(book_path)
    try:
        path.unlink()
    except FileNotFoundError as exc:
        raise LocalLibraryError("Книга уже удалена") from exc
    except OSError as exc:
        raise LocalLibraryError("Не удалось удалить локальную книгу") from exc


async def delete_book(book_path: str) -> None:
    await asyncio.to_thread(_delete, book_path)
