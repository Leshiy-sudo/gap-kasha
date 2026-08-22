import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "progress.db"


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS progress ("
        "book_path TEXT PRIMARY KEY, "
        "page INTEGER NOT NULL, "
        "updated_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    return conn


def get_page(book_path: str) -> int | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT page FROM progress WHERE book_path = ?", (book_path,)
        ).fetchone()
    return row[0] if row else None


def set_page(book_path: str, page: int) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO progress (book_path, page, updated_at) "
            "VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(book_path) DO UPDATE SET "
            "page = excluded.page, updated_at = excluded.updated_at",
            (book_path, page),
        )


def get_all() -> dict[str, int]:
    with _connect() as conn:
        rows = conn.execute("SELECT book_path, page FROM progress").fetchall()
    return dict(rows)
