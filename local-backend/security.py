import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
import jwt

APP_ENV = os.getenv("APP_ENV", "local")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ISSUER = os.getenv("JWT_ISSUER", "gapkassa-local")
JWT_ACCESS_TTL_MIN = int(os.getenv("JWT_ACCESS_TTL_MIN", "15"))
JWT_REFRESH_TTL_DAYS = int(os.getenv("JWT_REFRESH_TTL_DAYS", "30"))
OTP_PEPPER = os.getenv("OTP_PEPPER", "dev-otp-pepper")

if APP_ENV != "local":
    if JWT_SECRET == "dev-secret-change-me":
        raise RuntimeError("JWT_SECRET must be set for non-local environments")
    if OTP_PEPPER == "dev-otp-pepper":
        raise RuntimeError("OTP_PEPPER must be set for non-local environments")


def hash_otp(code: str) -> str:
    return hmac.new(OTP_PEPPER.encode(), code.encode(), hashlib.sha256).hexdigest()


def verify_otp(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(code), code_hash)


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def generate_access_token(user_id: str) -> str:
    # Use timezone-aware UTC to avoid local offset skew in timestamp()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iss": JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_ACCESS_TTL_MIN)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"], issuer=JWT_ISSUER)


def refresh_expiry() -> str:
    return (datetime.utcnow() + timedelta(days=JWT_REFRESH_TTL_DAYS)).isoformat()
