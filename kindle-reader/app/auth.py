import hmac

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import config
from .pwhash import hash_password

COOKIE_NAME = "session"
MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 дней — Kindle не должен спрашивать пароль каждый раз

_serializer = URLSafeTimedSerializer(config.SECRET_KEY, salt="kindle-reader-auth")


def verify_password(password: str) -> bool:
    salt = bytes.fromhex(config.PASSWORD_SALT)
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, config.PASSWORD_HASH)


def make_session_cookie() -> str:
    return _serializer.dumps({"auth": True})


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        data = _serializer.loads(token, max_age=MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return False
    return bool(data.get("auth"))
