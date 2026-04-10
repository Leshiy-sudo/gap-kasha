from pathlib import Path
from uuid import uuid4
from datetime import datetime
from db import db_session, now_iso

BASE_DIR = Path(__file__).resolve().parent
OUTBOX_DIR = BASE_DIR / "outbox"


def send_email(recipient: str, subject: str, body: str):
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    message_id = str(uuid4())
    filename = OUTBOX_DIR / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{recipient}_{message_id}.txt"
    filename.write_text(f"To: {recipient}\nSubject: {subject}\n\n{body}\n", encoding="utf-8")

    with db_session() as conn:
        conn.execute(
            "INSERT INTO email_outbox (id, recipient, subject, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (message_id, recipient, subject, body, now_iso())
        )
