import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from db import BASE_DIR, DB_PATH, db_session, now_iso

SUPPORTED_LOCALES = ("ru", "uz")
AD_KEYS = ("badge", "title", "body", "cta")
TEXT_KEYS = ("helper_register_otp", "verification_hint", "message_verification_sent")

DEFAULT_SETTINGS: Dict[str, str] = {
    "otp_ttl_min": os.getenv("OTP_TTL_MIN", "10"),
    "otp_cooldown_sec": os.getenv("OTP_COOLDOWN_SEC", "30"),
    "otp_max_attempts": os.getenv("OTP_MAX_ATTEMPTS", "5"),
    "login_max_attempts": os.getenv("LOGIN_MAX_ATTEMPTS", "5"),
    "login_lockout_min": os.getenv("LOGIN_LOCKOUT_MIN", "15"),
    "max_text_length": os.getenv("MAX_TEXT_LENGTH", "30"),
    "max_description_length": os.getenv("MAX_DESCRIPTION_LENGTH", "200"),
    "password_min_len": os.getenv("PASSWORD_MIN_LEN", "8"),
    "password_max_len": os.getenv("PASSWORD_MAX_LEN", "30"),
    "min_members_per_room": os.getenv("MIN_MEMBERS_PER_ROOM", "5"),
    "max_members_per_room": os.getenv("MAX_MEMBERS_PER_ROOM", "20"),
    "max_daily_otp_requests": os.getenv("MAX_DAILY_OTP_REQUESTS", "300"),
    "db_soft_limit_mb": os.getenv("DB_SOFT_LIMIT_MB", "256"),
    "outbox_soft_limit_mb": os.getenv("OUTBOX_SOFT_LIMIT_MB", "64"),
    "audit_retention_days": os.getenv("AUDIT_RETENTION_DAYS", "180"),
    "ad_enabled": os.getenv("AD_ENABLED", "1"),
    "ad_target_url": os.getenv("AD_TARGET_URL", ""),
}

DEFAULT_CONTENT: Dict[str, Dict[str, Dict[str, str]]] = {
    "ru": {
        "ad": {
            "badge": "AD",
            "title": "Тестовая интеграция",
            "body": "GapPay: скидка 20% на комиссии до 30 апреля. Подключение за 5 минут.",
            "cta": "Подключить",
        },
        "text": {
            "helper_register_otp": "Мы отправим код подтверждения на указанный email.",
            "verification_hint": "Можно вставить ссылку из письма — приложение извлечёт код.",
            "message_verification_sent": "Письмо с кодом отправлено. Проверьте почту.",
        },
    },
    "uz": {
        "ad": {
            "badge": "AD",
            "title": "Test integratsiya",
            "body": "GapPay: 30 aprelgacha komissiyaga 20% chegirma. Ulanish 5 daqiqa.",
            "cta": "Ulash",
        },
        "text": {
            "helper_register_otp": "Tasdiqlash kodi emailingizga yuboriladi.",
            "verification_hint": "Xatdagi havolani joylashtirsangiz ham bo‘ladi — ilova kodni ajratib oladi.",
            "message_verification_sent": "Kodli xat yuborildi. Pochtangizni tekshiring.",
        },
    },
}

OUTBOX_DIR = BASE_DIR / "outbox"


def _clone_default_content() -> Dict[str, Dict[str, Dict[str, str]]]:
    return {
        locale: {
            section: values.copy()
            for section, values in sections.items()
        }
        for locale, sections in DEFAULT_CONTENT.items()
    }


def _coerce_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _folder_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def _bytes_to_mb(value: int) -> float:
    return round(value / (1024 * 1024), 2)


def list_settings(conn=None) -> Dict[str, str]:
    close_conn = False
    if conn is None:
        session = db_session()
        conn = session.__enter__()
        close_conn = True
    try:
        settings = DEFAULT_SETTINGS.copy()
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        settings.update({row["key"]: row["value"] for row in rows})
        return settings
    finally:
        if close_conn:
            session.__exit__(None, None, None)


def get_setting(key: str, default: Optional[str] = None, conn=None) -> str:
    settings = list_settings(conn)
    if default is None:
        default = DEFAULT_SETTINGS.get(key, "")
    return settings.get(key, default)


def get_setting_int(key: str, default: int, conn=None) -> int:
    raw_value = get_setting(key, str(default), conn)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


def get_setting_bool(key: str, default: bool = False, conn=None) -> bool:
    raw_value = get_setting(key, "1" if default else "0", conn).strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def upsert_settings(values: Dict[str, Any], actor_id: str = "admin"):
    filtered = {
        key: _coerce_string(value)
        for key, value in values.items()
        if key in DEFAULT_SETTINGS
    }
    if not filtered:
        return
    with db_session() as conn:
        for key, value in filtered.items():
            conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at, updated_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
                """,
                (key, value, now_iso(), actor_id),
            )


def list_content(conn=None) -> Dict[str, Dict[str, Dict[str, str]]]:
    close_conn = False
    if conn is None:
        session = db_session()
        conn = session.__enter__()
        close_conn = True
    try:
        content = _clone_default_content()
        rows = conn.execute(
            "SELECT section, locale, content_key, value FROM app_content"
        ).fetchall()
        for row in rows:
            locale = row["locale"]
            section = row["section"]
            key = row["content_key"]
            if locale not in content:
                content[locale] = {"ad": {}, "text": {}}
            content.setdefault(locale, {}).setdefault(section, {})[key] = row["value"]
        return content
    finally:
        if close_conn:
            session.__exit__(None, None, None)


def upsert_content(locales: Dict[str, Dict[str, Dict[str, Any]]], actor_id: str = "admin"):
    with db_session() as conn:
        for locale, sections in locales.items():
            if locale not in SUPPORTED_LOCALES:
                continue
            for key in AD_KEYS:
                value = _coerce_string(sections.get("ad", {}).get(key))
                conn.execute(
                    """
                    INSERT INTO app_content (section, locale, content_key, value, updated_at, updated_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(section, locale, content_key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at,
                        updated_by = excluded.updated_by
                    """,
                    ("ad", locale, key, value or DEFAULT_CONTENT[locale]["ad"][key], now_iso(), actor_id),
                )
            for key in TEXT_KEYS:
                value = _coerce_string(sections.get("text", {}).get(key))
                conn.execute(
                    """
                    INSERT INTO app_content (section, locale, content_key, value, updated_at, updated_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(section, locale, content_key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at,
                        updated_by = excluded.updated_by
                    """,
                    ("text", locale, key, value or DEFAULT_CONTENT[locale]["text"][key], now_iso(), actor_id),
                )


def build_public_config(language: str = "ru") -> Dict[str, Any]:
    locale = language if language in SUPPORTED_LOCALES else "ru"
    settings = list_settings()
    content = list_content().get(locale, DEFAULT_CONTENT[locale])
    return {
        "generated_at": now_iso(),
        "ads": {
            "enabled": get_setting_bool("ad_enabled", True),
            "badge": content["ad"]["badge"],
            "title": content["ad"]["title"],
            "body": content["ad"]["body"],
            "cta": content["ad"]["cta"],
            "target_url": get_setting("ad_target_url", ""),
        },
        "texts": content["text"],
    }


def collect_admin_overview() -> Dict[str, Any]:
    with db_session() as conn:
        settings = list_settings(conn)
        now = now_iso()
        since_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        stats = {
            "generated_at": now,
            "users_total": conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"],
            "users_verified": conn.execute(
                "SELECT COUNT(*) AS count FROM users WHERE email_verified = 1"
            ).fetchone()["count"],
            "users_active": conn.execute(
                "SELECT COUNT(*) AS count FROM users WHERE is_active = 1"
            ).fetchone()["count"],
            "rooms_total": conn.execute("SELECT COUNT(*) AS count FROM rooms").fetchone()["count"],
            "payments_total": conn.execute("SELECT COUNT(*) AS count FROM payments").fetchone()["count"],
            "payments_paid": conn.execute(
                "SELECT COUNT(*) AS count FROM payments WHERE status = 'PAID'"
            ).fetchone()["count"],
            "otp_last_24h": conn.execute(
                "SELECT COUNT(*) AS count FROM otp_codes WHERE created_at >= ?",
                (since_24h,),
            ).fetchone()["count"],
            "failed_logins_last_24h": conn.execute(
                "SELECT COUNT(*) AS count FROM login_attempts WHERE success = 0 AND created_at >= ?",
                (since_24h,),
            ).fetchone()["count"],
            "audit_rows": conn.execute("SELECT COUNT(*) AS count FROM audit_log").fetchone()["count"],
            "email_outbox_rows": conn.execute(
                "SELECT COUNT(*) AS count FROM email_outbox"
            ).fetchone()["count"],
        }
        recent_audit = [
            {
                "created_at": row["created_at"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "actor_id": row["actor_id"],
            }
            for row in conn.execute(
                """
                SELECT created_at, action, entity_type, entity_id, actor_id
                FROM audit_log
                ORDER BY created_at DESC
                LIMIT 12
                """
            ).fetchall()
        ]

    db_size_mb = _bytes_to_mb(_folder_size_bytes(DB_PATH))
    outbox_size_mb = _bytes_to_mb(_folder_size_bytes(OUTBOX_DIR))
    db_soft_limit = get_setting_int("db_soft_limit_mb", 256)
    outbox_soft_limit = get_setting_int("outbox_soft_limit_mb", 64)
    return {
        "stats": {
            **stats,
            "db_size_mb": db_size_mb,
            "outbox_size_mb": outbox_size_mb,
            "outbox_files": len(list(OUTBOX_DIR.glob("*"))) if OUTBOX_DIR.exists() else 0,
            "db_soft_limit_mb": db_soft_limit,
            "outbox_soft_limit_mb": outbox_soft_limit,
            "db_soft_limit_reached": db_size_mb >= db_soft_limit,
            "outbox_soft_limit_reached": outbox_size_mb >= outbox_soft_limit,
        },
        "settings": settings,
        "recent_audit": recent_audit,
    }
