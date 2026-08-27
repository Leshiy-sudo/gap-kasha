import sqlite3
from contextlib import closing
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "progress.db"
DEFAULT_USER_ID = "talgat"


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS progress ("
        "user_id TEXT NOT NULL, "
        "book_path TEXT NOT NULL, "
        "page INTEGER NOT NULL, "
        "updated_at TEXT NOT NULL DEFAULT (datetime('now')), "
        "PRIMARY KEY (user_id, book_path)"
        ")"
    )


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(progress)").fetchall()
    }
    if columns and "user_id" not in columns:
        with conn:
            conn.execute("ALTER TABLE progress RENAME TO progress_legacy")
            _create_schema(conn)
            conn.execute(
                "INSERT INTO progress (user_id, book_path, page, updated_at) "
                "SELECT ?, book_path, page, updated_at FROM progress_legacy",
                (DEFAULT_USER_ID,),
            )
            conn.execute("DROP TABLE progress_legacy")
    else:
        _create_schema(conn)
    return conn


def get_page(user_id: str, book_path: str) -> int | None:
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT page FROM progress WHERE user_id = ? AND book_path = ?",
            (user_id, book_path),
        ).fetchone()
    return row[0] if row else None


def set_page(user_id: str, book_path: str, page: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO progress (user_id, book_path, page, updated_at) "
            "VALUES (?, ?, ?, datetime('now')) "
            "ON CONFLICT(user_id, book_path) DO UPDATE SET "
            "page = excluded.page, updated_at = excluded.updated_at",
            (user_id, book_path, page),
        )


def get_all(user_id: str) -> dict[str, int]:
    with closing(_connect()) as conn, conn:
        rows = conn.execute(
            "SELECT book_path, page FROM progress WHERE user_id = ?", (user_id,)
        ).fetchall()
    return dict(rows)


def delete(book_path: str, user_id: str | None = None) -> None:
    with closing(_connect()) as conn, conn:
        if user_id is None:
            conn.execute("DELETE FROM progress WHERE book_path = ?", (book_path,))
        else:
            conn.execute(
                "DELETE FROM progress WHERE user_id = ? AND book_path = ?",
                (user_id, book_path),
            )
