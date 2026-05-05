import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db import init_db, db_session, now_iso  # noqa: E402


UI_TEST_EMAIL = os.getenv("UI_TEST_EMAIL", "uiqa@example.com").strip().lower()
UI_TEST_NAME = os.getenv("UI_TEST_NAME", "Uiqa")
UI_TEST_GOOGLE_SUB = os.getenv("UI_TEST_GOOGLE_SUB", "android-ui-test")


def cleanup_user_rooms(conn, user_id: str):
    room_ids = [
        row["id"]
        for row in conn.execute(
            "SELECT id FROM rooms WHERE created_by = ?",
            (user_id,),
        ).fetchall()
    ]
    for room_id in room_ids:
        conn.execute("DELETE FROM payments WHERE room_id = ?", (room_id,))
        conn.execute("DELETE FROM room_members WHERE room_id = ?", (room_id,))
        conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))


def seed_user():
    init_db()
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (UI_TEST_EMAIL,),
        ).fetchone()
        now = now_iso()

        if row is None:
            conn.execute(
                """
                INSERT INTO users (
                    id, email, auth_provider, google_sub, name, last_name, patronymic, phone,
                    photo_url, password_hash, email_verified, created_at, updated_at, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "ui-test-user",
                    UI_TEST_EMAIL,
                    "google",
                    UI_TEST_GOOGLE_SUB,
                    UI_TEST_NAME,
                    None,
                    None,
                    None,
                    None,
                    None,
                    1,
                    now,
                    now,
                    1,
                ),
            )
            user_id = "ui-test-user"
        else:
            user_id = row["id"]
            conn.execute(
                """
                UPDATE users
                SET email = ?, auth_provider = ?, google_sub = ?, name = ?, password_hash = ?,
                    email_verified = 1, is_active = 1, updated_at = ?
                WHERE id = ?
                """,
                (UI_TEST_EMAIL, "google", UI_TEST_GOOGLE_SUB, UI_TEST_NAME, None, now, user_id),
            )

        cleanup_user_rooms(conn, user_id)
        conn.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM device_tokens WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM otp_codes WHERE email = ?", (UI_TEST_EMAIL,))

    print(f"Seeded UI test Google user: {UI_TEST_EMAIL}")


if __name__ == "__main__":
    seed_user()
