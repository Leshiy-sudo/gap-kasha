import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


MODULES_TO_RESET = [
    "main",
    "db",
    "security",
    "runtime_config",
    "email_service",
    "account_service",
    "legal_pages",
    "admin_panel",
    "autotest_admin",
]


@pytest.fixture
def app_ctx(tmp_path, monkeypatch):
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    db_path = tmp_path / "app.db"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "gapkassa-test-secret")
    monkeypatch.setenv("JWT_ISSUER", "gapkassa-test")
    monkeypatch.setenv("OTP_PEPPER", "gapkassa-test-otp")
    monkeypatch.setenv("PASSWORD_PEPPER", "gapkassa-test-password")
    monkeypatch.setenv("GOOGLE_WEB_CLIENT_ID", "test-web-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_AUTH_ALLOW_MOCK", "true")
    monkeypatch.setenv("CLIENT_ERROR_REPORT_EMAILS", "alerts@example.com")
    monkeypatch.setenv("AUTOTEST_STATUS_PATH", str(tmp_path / "autotest_status.json"))

    for module_name in MODULES_TO_RESET:
        sys.modules.pop(module_name, None)

    main = importlib.import_module("main")
    db = importlib.import_module("db")
    security = importlib.import_module("security")

    sent_emails = []

    def fake_send_email(recipient: str, subject: str, body: str):
        sent_emails.append(
            {
                "recipient": recipient,
                "subject": subject,
                "body": body,
            }
        )

    monkeypatch.setattr(main, "send_email", fake_send_email)

    with TestClient(main.app) as client:
        yield {
            "client": client,
            "main": main,
            "db": db,
            "security": security,
            "db_path": db_path,
            "sent_emails": sent_emails,
        }
