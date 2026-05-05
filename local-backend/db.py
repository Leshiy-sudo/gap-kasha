import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data" / "app.db"))).expanduser()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                auth_provider TEXT NOT NULL DEFAULT 'email',
                google_sub TEXT,
                name TEXT,
                last_name TEXT,
                patronymic TEXT,
                phone TEXT,
                photo_url TEXT,
                password_hash TEXT,
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS otp_codes (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_attempts INTEGER NOT NULL DEFAULT 5,
                used_at TEXT,
                ip TEXT,
                user_agent TEXT
            );

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                ip TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS device_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS rooms (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                monthly_amount INTEGER,
                payment_day INTEGER,
                cycle_length_months INTEGER,
                auto_rotate INTEGER,
                member_count INTEGER,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS room_members (
                room_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                order_index INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (room_id, user_id),
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                payer_id TEXT NOT NULL,
                receiver_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                month TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms(id),
                FOREIGN KEY (payer_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_payments_room ON payments(room_id);
            CREATE INDEX IF NOT EXISTS idx_payments_month ON payments(room_id, month);

            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                actor_id TEXT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                before_json TEXT,
                after_json TEXT,
                ip TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS email_outbox (
                id TEXT PRIMARY KEY,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS login_attempts (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                success INTEGER NOT NULL,
                ip TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT
            );

            CREATE TABLE IF NOT EXISTS app_content (
                section TEXT NOT NULL,
                locale TEXT NOT NULL,
                content_key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT,
                PRIMARY KEY (section, locale, content_key)
            );
            CREATE INDEX IF NOT EXISTS idx_login_attempts_email_time ON login_attempts(email, created_at);
            """
        )
        ensure_user_columns(conn)
        ensure_room_columns(conn)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub_unique ON users(google_sub) WHERE google_sub IS NOT NULL"
        )
        conn.commit()


def ensure_user_columns(conn: sqlite3.Connection):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    alterations = []
    if "auth_provider" not in existing:
        alterations.append("ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'email'")
    if "google_sub" not in existing:
        alterations.append("ALTER TABLE users ADD COLUMN google_sub TEXT")
    if "last_name" not in existing:
        alterations.append("ALTER TABLE users ADD COLUMN last_name TEXT")
    if "patronymic" not in existing:
        alterations.append("ALTER TABLE users ADD COLUMN patronymic TEXT")
    if "photo_url" not in existing:
        alterations.append("ALTER TABLE users ADD COLUMN photo_url TEXT")
    if "password_hash" not in existing:
        alterations.append("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "email_verified" not in existing:
        alterations.append("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
    for stmt in alterations:
        conn.execute(stmt)


def ensure_room_columns(conn: sqlite3.Connection):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(rooms)").fetchall()}
    alterations = []
    if "monthly_amount" not in existing:
        alterations.append("ALTER TABLE rooms ADD COLUMN monthly_amount INTEGER")
    if "payment_day" not in existing:
        alterations.append("ALTER TABLE rooms ADD COLUMN payment_day INTEGER")
    if "cycle_length_months" not in existing:
        alterations.append("ALTER TABLE rooms ADD COLUMN cycle_length_months INTEGER")
    if "auto_rotate" not in existing:
        alterations.append("ALTER TABLE rooms ADD COLUMN auto_rotate INTEGER")
    if "member_count" not in existing:
        alterations.append("ALTER TABLE rooms ADD COLUMN member_count INTEGER")
    for stmt in alterations:
        conn.execute(stmt)


def now_iso() -> str:
    return datetime.utcnow().isoformat()
