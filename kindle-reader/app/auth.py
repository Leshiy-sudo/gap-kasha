import hmac
import json
from functools import lru_cache

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import config
from .pwhash import hash_password

COOKIE_NAME = "session"
MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 дней — Kindle не должен спрашивать пароль каждый раз

_serializer = URLSafeTimedSerializer(config.SECRET_KEY, salt="kindle-reader-auth")


@lru_cache(maxsize=1)
def configured_users() -> dict[str, dict[str, str]]:
    if not config.AUTH_USERS_JSON:
        return {
            config.DEFAULT_USER_ID: {
                "name": "Талгат",
                "salt": config.PASSWORD_SALT,
                "hash": config.PASSWORD_HASH,
            }
        }
    raw = json.loads(config.AUTH_USERS_JSON)
    users: dict[str, dict[str, str]] = {}
    for user_id, values in raw.items():
        if not user_id or not isinstance(values, dict):
            raise ValueError("Некорректная настройка пользователей")
        users[user_id] = {
            "name": str(values["name"]),
            "salt": str(values["salt"]),
            "hash": str(values["hash"]),
        }
    if config.DEFAULT_USER_ID not in users:
        raise ValueError("Основной пользователь отсутствует в AUTH_USERS_JSON")
    return users


def user_choices() -> list[tuple[str, str]]:
    return [(user_id, values["name"]) for user_id, values in configured_users().items()]


def verify_password(user_id: str, password: str) -> bool:
    user = configured_users().get(user_id)
    if not user:
        return False
    salt = bytes.fromhex(user["salt"])
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, user["hash"])


def make_session_cookie(user_id: str) -> str:
    if user_id not in configured_users():
        raise ValueError("Неизвестный пользователь")
    return _serializer.dumps({"auth": True, "user_id": user_id})


def current_user_id(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = _serializer.loads(token, max_age=MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    if not data.get("auth"):
        return None
    # Старые подписанные сессии без user_id продолжают работать как Талгат.
    user_id = data.get("user_id") or config.DEFAULT_USER_ID
    return user_id if user_id in configured_users() else None


def is_authenticated(request: Request) -> bool:
    return current_user_id(request) is not None


def current_user_name(request: Request) -> str | None:
    user_id = current_user_id(request)
    return configured_users()[user_id]["name"] if user_id else None
