import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from db import db_session, now_iso

BASE_DIR = Path(__file__).resolve().parent
OUTBOX_DIR = BASE_DIR / "outbox"


def _load_env_file():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"").strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _smtp_settings():
    _load_env_file()
    host = os.getenv("SMTP_HOST")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    if not (host and user and password):
        return None
    port = int(os.getenv("SMTP_PORT", "465"))
    use_tls = os.getenv("SMTP_TLS", "false").lower() == "true"
    sender = os.getenv("SMTP_FROM") or user
    admin_email = os.getenv("OTP_ADMIN_EMAIL")
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "use_tls": use_tls,
        "sender": sender,
        "admin_email": admin_email,
    }


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

    settings = _smtp_settings()
    if settings is None:
        return

    msg = EmailMessage()
    msg["From"] = settings["sender"]
    msg["To"] = recipient
    admin_email = settings.get("admin_email")
    if admin_email and admin_email.lower() != recipient.lower():
        msg["Bcc"] = admin_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if admin_email and admin_email.lower() != recipient.lower():
            admin_message_id = str(uuid4())
            admin_filename = OUTBOX_DIR / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{admin_email}_{admin_message_id}.txt"
            admin_filename.write_text(f"To: {admin_email}\nSubject: {subject}\n\n{body}\n", encoding="utf-8")
            with db_session() as conn:
                conn.execute(
                    "INSERT INTO email_outbox (id, recipient, subject, body, created_at) VALUES (?, ?, ?, ?, ?)",
                    (admin_message_id, admin_email, subject, body, now_iso())
                )
        if settings["use_tls"]:
            server = smtplib.SMTP(settings["host"], settings["port"], timeout=10)
            server.starttls(context=ssl.create_default_context())
        else:
            server = smtplib.SMTP_SSL(settings["host"], settings["port"], context=ssl.create_default_context(), timeout=10)
        server.login(settings["user"], settings["password"])
        server.send_message(msg)
        server.quit()
    except Exception as exc:
        error_id = str(uuid4())
        error_file = OUTBOX_DIR / f"ERROR_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{recipient}_{error_id}.txt"
        error_file.write_text(f"SMTP error: {exc}\n", encoding="utf-8")
        raise RuntimeError(f"smtp_send_failed: {exc}") from exc
