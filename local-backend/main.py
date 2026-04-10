import json
import os
import re
import hashlib
from uuid import uuid4
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import db_session, init_db, now_iso
from email_service import send_email
from security import (
    decode_token,
    generate_access_token,
    generate_otp_code,
    generate_refresh_token,
    hash_otp,
    hash_password,
    refresh_expiry,
    verify_password,
    verify_otp as verify_otp_code,
)

APP_ENV = os.getenv("APP_ENV", "local")
RAW_CORS_ORIGINS = os.getenv("CORS_ORIGINS", "")
OTP_TTL_MIN = int(os.getenv("OTP_TTL_MIN", "10"))
OTP_COOLDOWN_SEC = int(os.getenv("OTP_COOLDOWN_SEC", "60"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCKOUT_MIN = int(os.getenv("LOGIN_LOCKOUT_MIN", "15"))

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "30"))
MAX_DESCRIPTION_LENGTH = int(os.getenv("MAX_DESCRIPTION_LENGTH", "200"))
PASSWORD_MIN_LEN = int(os.getenv("PASSWORD_MIN_LEN", "8"))
PASSWORD_MAX_LEN = int(os.getenv("PASSWORD_MAX_LEN", "30"))
ALLOWED_ROLES = {"ADMIN", "MEMBER"}
ALLOWED_PAYMENT_STATUSES = {"EXPECTED", "PAID", "SKIPPED", "OVERDUE"}

app = FastAPI(title="GapKassa Local API", version="0.2.0")

def parse_cors_origins(raw: str) -> List[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


cors_origins = parse_cors_origins(RAW_CORS_ORIGINS)
if APP_ENV == "local":
    cors_allow_origins = ["*"]
    cors_allow_credentials = True
else:
    if not cors_origins:
        raise RuntimeError("CORS_ORIGINS must be set for non-local environments")
    cors_allow_origins = cors_origins
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageResponse(BaseModel):
    message: str


class RegisterOtpRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None
    phone: Optional[str] = None


class RegisterVerifyRequest(BaseModel):
    email: str
    code: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None


class MemberInput(BaseModel):
    email: str
    name: Optional[str] = None
    role: Optional[str] = None
    order_index: Optional[int] = None


class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    monthly_amount: int
    payment_day: int
    cycle_length_months: int
    auto_rotate: bool
    members: List[MemberInput]


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_amount: Optional[int] = None
    payment_day: Optional[int] = None
    cycle_length_months: Optional[int] = None
    auto_rotate: Optional[bool] = None
    member_count: Optional[int] = None


class PaymentStatusUpdate(BaseModel):
    status: str


class ScheduleItem(BaseModel):
    month: str
    receiver_id: str


class ScheduleUpdate(BaseModel):
    items: List[ScheduleItem]


def validate_email(email: str):
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="invalid_email")


def validate_text_length(value: Optional[str], field: str):
    if value is None:
        return
    if len(value) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"{field}_too_long")


def validate_description_length(value: Optional[str]):
    if value is None:
        return
    if len(value) > MAX_DESCRIPTION_LENGTH:
        raise HTTPException(status_code=400, detail="description_too_long")


def validate_password(password: str):
    if password is None:
        raise HTTPException(status_code=400, detail="password_required")
    if len(password) < PASSWORD_MIN_LEN or len(password) > PASSWORD_MAX_LEN:
        raise HTTPException(status_code=400, detail="password_invalid")


def normalize_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    validate_text_length(email, "email")
    validate_email(email)
    return email


def parse_iso_date(value: str, field: str) -> date:
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field}_invalid")


def normalize_role(role: Optional[str], default_role: str) -> str:
    if role is None:
        return default_role
    role_value = role.strip().upper()
    if role_value not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="invalid_role")
    return role_value


def normalize_status(status_value: str) -> str:
    value = status_value.strip().upper()
    if value not in ALLOWED_PAYMENT_STATUSES:
        raise HTTPException(status_code=400, detail="invalid_status")
    return value


def log_event(conn, actor_id, action, entity_type, entity_id, before, after, request: Request):
    conn.execute(
        """
        INSERT INTO audit_log (id, actor_id, action, entity_type, entity_id, before_json, after_json, ip, user_agent, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            actor_id,
            action,
            entity_type,
            entity_id,
            json.dumps(before) if before is not None else None,
            json.dumps(after) if after is not None else None,
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
            now_iso(),
        ),
    )


def login_locked_until(conn, email: str) -> Optional[datetime]:
    row = conn.execute(
        """
        SELECT created_at FROM login_attempts
        WHERE email = ? AND success = 0 AND created_at >= ?
        ORDER BY created_at DESC
        """,
        (
            email,
            (datetime.utcnow() - timedelta(minutes=LOGIN_LOCKOUT_MIN)).isoformat(),
        ),
    ).fetchall()
    if not row:
        return None
    if len(row) >= LOGIN_MAX_ATTEMPTS:
        last = datetime.fromisoformat(row[0]["created_at"])
        return last + timedelta(minutes=LOGIN_LOCKOUT_MIN)
    return None


def log_login_attempt(conn, email: str, success: bool, request: Request):
    conn.execute(
        """
        INSERT INTO login_attempts (id, email, success, ip, user_agent, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            email,
            1 if success else 0,
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
            now_iso(),
        ),
    )


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def get_current_user(request: Request):
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token")
    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    return dict(row)


def require_room_member(conn, room_id: str, user_id: str) -> str:
    row = conn.execute(
        "SELECT role FROM room_members WHERE room_id = ? AND user_id = ?",
        (room_id, user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=403, detail="room_access_denied")
    return row["role"]


def require_room_admin(conn, room_id: str, user_id: str):
    role = require_room_member(conn, room_id, user_id)
    if role != "ADMIN":
        raise HTTPException(status_code=403, detail="room_admin_required")


def add_months(base: date, months: int) -> date:
    total_month = (base.month - 1) + months
    year = base.year + total_month // 12
    month = total_month % 12 + 1
    day = min(base.day, 28)
    return date(year, month, day)


def generate_payments(room_id: str, member_ids: List[str], amount: int, payment_day: int, cycle_length: int):
    if len(member_ids) < 5 or len(member_ids) > 20:
        return []
    payments = []
    now_date = datetime.utcnow().date()
    clamped_day = max(1, min(payment_day, 28))
    for i in range(cycle_length):
        month_date = add_months(now_date, i).replace(day=clamped_day)
        receiver_id = member_ids[i % len(member_ids)]
        for payer_id in member_ids:
            if payer_id == receiver_id:
                continue
            payments.append(
                {
                    "id": str(uuid4()),
                    "room_id": room_id,
                    "payer_id": payer_id,
                    "receiver_id": receiver_id,
                    "amount": amount,
                    "month": month_date.isoformat(),
                    "status": "EXPECTED",
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                }
            )
    return payments


def serialize_room(row):
    data = dict(row)
    if data.get("auto_rotate") is not None:
        data["auto_rotate"] = bool(data["auto_rotate"])
    return data


def serialize_member(row):
    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "order_index": row["order_index"],
    }


def serialize_payment(row):
    return {
        "id": row["id"],
        "room_id": row["room_id"],
        "payer_id": row["payer_id"],
        "receiver_id": row["receiver_id"],
        "amount": row["amount"],
        "month": row["month"],
        "status": row["status"],
        "updated_at": row["updated_at"],
    }


def upsert_user(conn, email: str, name: Optional[str], request: Request):
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is not None:
        if name and not row["name"]:
            before = dict(row)
            conn.execute(
                "UPDATE users SET name = ?, updated_at = ? WHERE id = ?",
                (name, now_iso(), row["id"]),
            )
            updated = conn.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
            log_event(conn, row["id"], "user.update", "user", row["id"], before, dict(updated), request)
            return dict(updated)
        return dict(row)

    user_id = str(uuid4())
    now_str = now_iso()
    conn.execute(
        """
        INSERT INTO users (id, email, name, last_name, patronymic, phone, photo_url, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, email, name, None, None, None, None, now_str, now_str),
    )
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    log_event(conn, user_id, "user.create", "user", user_id, None, {"email": email}, request)
    return dict(user)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/request-otp", response_model=MessageResponse)
def request_register_otp(payload: RegisterOtpRequest, request: Request):
    email = normalize_email(payload.email)
    validate_password(payload.password)
    name = normalize_optional(payload.name)
    last_name = normalize_optional(payload.last_name)
    patronymic = normalize_optional(payload.patronymic)
    phone = normalize_optional(payload.phone)
    validate_text_length(name, "name")
    validate_text_length(last_name, "last_name")
    validate_text_length(patronymic, "patronymic")
    validate_text_length(phone, "phone")

    now = datetime.utcnow()
    with db_session() as conn:
        latest = conn.execute(
            "SELECT created_at FROM otp_codes WHERE email = ? ORDER BY created_at DESC LIMIT 1",
            (email,),
        ).fetchone()
        if latest:
            last_created = datetime.fromisoformat(latest["created_at"])
            if (now - last_created).total_seconds() < OTP_COOLDOWN_SEC:
                raise HTTPException(status_code=429, detail="otp_cooldown")

        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is not None and user["email_verified"] == 1:
            raise HTTPException(status_code=409, detail="email_exists")

        password_hash = hash_password(payload.password)
        now_str = now_iso()
        if user is None:
            user_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO users (
                    id, email, name, last_name, patronymic, phone, photo_url, password_hash, email_verified, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    email,
                    name,
                    last_name,
                    patronymic,
                    phone,
                    None,
                    password_hash,
                    0,
                    now_str,
                    now_str,
                ),
            )
            log_event(conn, user_id, "user.create", "user", user_id, None, {"email": email}, request)
            actor_id = user_id
        else:
            before = dict(user)
            conn.execute(
                """
                UPDATE users
                SET name = ?, last_name = ?, patronymic = ?, phone = ?, password_hash = ?, email_verified = 0, updated_at = ?
                WHERE id = ?
                """,
                (
                    name if name is not None else user["name"],
                    last_name if last_name is not None else user["last_name"],
                    patronymic if patronymic is not None else user["patronymic"],
                    phone if phone is not None else user["phone"],
                    password_hash,
                    now_str,
                    user["id"],
                ),
            )
            updated = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
            log_event(conn, user["id"], "user.update", "user", user["id"], before, dict(updated), request)
            actor_id = user["id"]

        code = generate_otp_code()
        conn.execute(
            """
            INSERT INTO otp_codes (id, email, code_hash, created_at, expires_at, attempts, max_attempts, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                email,
                hash_otp(code),
                now.isoformat(),
                (now + timedelta(minutes=OTP_TTL_MIN)).isoformat(),
                0,
                OTP_MAX_ATTEMPTS,
                request.client.host if request.client else None,
                request.headers.get("user-agent"),
            ),
        )
        log_event(conn, actor_id, "auth.register.request_otp", "auth", None, None, {"email": email}, request)

    send_email(
        recipient=email,
        subject="Ваш код подтверждения",
        body=f"Ваш код: {code}\nОн действителен {OTP_TTL_MIN} минут.",
    )

    return MessageResponse(message="otp_sent")


@app.post("/auth/verify-otp", response_model=AuthResponse)
def verify_register_otp(payload: RegisterVerifyRequest, request: Request):
    email = normalize_email(payload.email)
    code = payload.code.strip()
    if len(code) < 4:
        raise HTTPException(status_code=400, detail="invalid_code")

    with db_session() as conn:
        otp = conn.execute(
            """
            SELECT * FROM otp_codes
            WHERE email = ? AND used_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (email,),
        ).fetchone()
        if otp is None:
            raise HTTPException(status_code=400, detail="code_not_found")
        if datetime.utcnow() > datetime.fromisoformat(otp["expires_at"]):
            raise HTTPException(status_code=400, detail="code_expired")
        if otp["attempts"] >= otp["max_attempts"]:
            raise HTTPException(status_code=429, detail="code_attempts_exceeded")

        if not verify_otp_code(code, otp["code_hash"]):
            conn.execute(
                "UPDATE otp_codes SET attempts = attempts + 1 WHERE id = ?",
                (otp["id"],),
            )
            raise HTTPException(status_code=400, detail="code_invalid")

        conn.execute(
            "UPDATE otp_codes SET used_at = ? WHERE id = ?",
            (now_iso(), otp["id"]),
        )

        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None:
            raise HTTPException(status_code=400, detail="user_not_found")
        if user["email_verified"] == 1:
            raise HTTPException(status_code=409, detail="already_verified")
        if not user["password_hash"]:
            raise HTTPException(status_code=400, detail="password_missing")

        conn.execute(
            "UPDATE users SET email_verified = 1, updated_at = ? WHERE id = ?",
            (now_iso(), user["id"]),
        )
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()

        access_token = generate_access_token(user["id"])
        refresh_token = generate_refresh_token()
        conn.execute(
            """
            INSERT INTO refresh_tokens (id, user_id, token_hash, created_at, expires_at, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                user["id"],
                hash_refresh_token(refresh_token),
                now_iso(),
                refresh_expiry(),
                request.client.host if request.client else None,
                request.headers.get("user-agent"),
            ),
        )
        log_event(conn, user["id"], "auth.register.verify", "auth", None, None, {"email": email}, request)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "last_name": user["last_name"],
            "patronymic": user["patronymic"],
            "phone": user["phone"],
            "photo_url": user["photo_url"],
        },
    )


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request):
    email = normalize_email(payload.email)
    if not payload.password:
        raise HTTPException(status_code=400, detail="password_required")

    with db_session() as conn:
        locked_until = login_locked_until(conn, email)
        if locked_until:
            raise HTTPException(status_code=429, detail="login_locked")
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or not user["password_hash"]:
            log_login_attempt(conn, email, False, request)
            raise HTTPException(status_code=401, detail="invalid_credentials")
        if user["email_verified"] != 1:
            log_login_attempt(conn, email, False, request)
            raise HTTPException(status_code=403, detail="email_not_verified")
        if user["is_active"] != 1:
            log_login_attempt(conn, email, False, request)
            raise HTTPException(status_code=403, detail="user_inactive")
        if not verify_password(payload.password, user["password_hash"]):
            log_login_attempt(conn, email, False, request)
            raise HTTPException(status_code=401, detail="invalid_credentials")

        access_token = generate_access_token(user["id"])
        refresh_token = generate_refresh_token()
        conn.execute(
            """
            INSERT INTO refresh_tokens (id, user_id, token_hash, created_at, expires_at, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                user["id"],
                hash_refresh_token(refresh_token),
                now_iso(),
                refresh_expiry(),
                request.client.host if request.client else None,
                request.headers.get("user-agent"),
            ),
        )
        log_login_attempt(conn, email, True, request)
        log_event(conn, user["id"], "auth.login", "auth", None, None, {"email": email}, request)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "last_name": user["last_name"],
            "patronymic": user["patronymic"],
            "phone": user["phone"],
            "photo_url": user["photo_url"],
        },
    )


@app.post("/auth/refresh", response_model=AuthResponse)
def refresh_token(payload: RefreshRequest, request: Request):
    token_hash = hash_refresh_token(payload.refresh_token)
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT * FROM refresh_tokens
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (token_hash,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="refresh_not_found")
        if datetime.utcnow() > datetime.fromisoformat(row["expires_at"]):
            raise HTTPException(status_code=401, detail="refresh_expired")

        conn.execute(
            "UPDATE refresh_tokens SET revoked_at = ? WHERE id = ?",
            (now_iso(), row["id"]),
        )
        user = conn.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()
        if user is None:
            raise HTTPException(status_code=401, detail="user_not_found")

        access_token = generate_access_token(user["id"])
        refresh_token_value = generate_refresh_token()
        conn.execute(
            """
            INSERT INTO refresh_tokens (id, user_id, token_hash, created_at, expires_at, ip, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                user["id"],
                hash_refresh_token(refresh_token_value),
                now_iso(),
                refresh_expiry(),
                request.client.host if request.client else None,
                request.headers.get("user-agent"),
            ),
        )
        log_event(conn, user["id"], "auth.refresh", "auth", None, None, None, request)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token_value,
        user={
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "last_name": user["last_name"],
            "patronymic": user["patronymic"],
            "phone": user["phone"],
            "photo_url": user["photo_url"],
        },
    )


@app.post("/auth/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, request: Request, current_user: dict = Depends(get_current_user)):
    with db_session() as conn:
        if payload.refresh_token:
            token_hash = hash_refresh_token(payload.refresh_token)
            conn.execute(
                "UPDATE refresh_tokens SET revoked_at = ? WHERE token_hash = ?",
                (now_iso(), token_hash),
            )
        else:
            conn.execute(
                "UPDATE refresh_tokens SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (now_iso(), current_user["id"]),
            )
        log_event(conn, current_user["id"], "auth.logout", "auth", None, None, None, request)
    return MessageResponse(message="logged_out")


@app.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "last_name": current_user["last_name"],
        "patronymic": current_user["patronymic"],
        "phone": current_user["phone"],
        "photo_url": current_user["photo_url"],
    }


@app.patch("/me")
def update_me(payload: ProfileUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    with db_session() as conn:
        before = dict(current_user)
        validate_text_length(payload.name, "name")
        validate_text_length(payload.last_name, "last_name")
        validate_text_length(payload.patronymic, "patronymic")
        validate_text_length(payload.phone, "phone")
        name = payload.name if payload.name is not None else current_user["name"]
        last_name = payload.last_name if payload.last_name is not None else current_user["last_name"]
        patronymic = payload.patronymic if payload.patronymic is not None else current_user["patronymic"]
        phone = payload.phone if payload.phone is not None else current_user["phone"]
        photo_url = payload.photo_url if payload.photo_url is not None else current_user["photo_url"]
        conn.execute(
            "UPDATE users SET name = ?, last_name = ?, patronymic = ?, phone = ?, photo_url = ?, updated_at = ? WHERE id = ?",
            (name, last_name, patronymic, phone, photo_url, now_iso(), current_user["id"]),
        )
        user = conn.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],)).fetchone()
        log_event(conn, current_user["id"], "user.update", "user", current_user["id"], before, dict(user), request)

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "last_name": user["last_name"],
        "patronymic": user["patronymic"],
        "phone": user["phone"],
        "photo_url": user["photo_url"],
    }


@app.post("/rooms")
def create_room(payload: RoomCreate, request: Request, current_user: dict = Depends(get_current_user)):
    validate_text_length(payload.name, "room_name")
    validate_description_length(payload.description)
    if payload.monthly_amount <= 0:
        raise HTTPException(status_code=400, detail="amount_invalid")
    if payload.payment_day < 1 or payload.payment_day > 28:
        raise HTTPException(status_code=400, detail="payment_day_invalid")
    if payload.cycle_length_months < 1 or payload.cycle_length_months > 60:
        raise HTTPException(status_code=400, detail="cycle_length_invalid")
    if len(payload.members) < 5 or len(payload.members) > 20:
        raise HTTPException(status_code=400, detail="members_invalid")

    room_id = str(uuid4())
    now_str = now_iso()
    description = normalize_optional(payload.description)
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO rooms (
                id,
                name,
                description,
                monthly_amount,
                payment_day,
                cycle_length_months,
                auto_rotate,
                member_count,
                created_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                room_id,
                payload.name,
                description,
                payload.monthly_amount,
                payload.payment_day,
                payload.cycle_length_months,
                1 if payload.auto_rotate else 0,
                len(payload.members),
                current_user["id"],
                now_str,
                now_str,
            ),
        )

        members_payload = []
        member_ids = []
        for index, member in enumerate(payload.members):
            email = normalize_email(member.email)
            validate_text_length(member.name, "member_name")
            name = member.name.strip() if member.name else None
            user = upsert_user(conn, email, name, request)
            role = normalize_role(member.role, "ADMIN" if index == 0 else "MEMBER")
            order_index = member.order_index if member.order_index is not None else index
            conn.execute(
                """
                INSERT OR REPLACE INTO room_members (room_id, user_id, role, order_index, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (room_id, user["id"], role, order_index, now_str, now_str),
            )
            members_payload.append(
                {
                    "user_id": user["id"],
                    "email": user["email"],
                    "name": user["name"],
                    "role": role,
                    "order_index": order_index,
                }
            )
            member_ids.append(user["id"])

        payments_payload = generate_payments(
            room_id=room_id,
            member_ids=member_ids,
            amount=payload.monthly_amount,
            payment_day=payload.payment_day,
            cycle_length=payload.cycle_length_months,
        )
        for payment in payments_payload:
            conn.execute(
                """
                INSERT INTO payments (id, room_id, payer_id, receiver_id, amount, month, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payment["id"],
                    payment["room_id"],
                    payment["payer_id"],
                    payment["receiver_id"],
                    payment["amount"],
                    payment["month"],
                    payment["status"],
                    payment["created_at"],
                    payment["updated_at"],
                ),
            )

        log_event(
            conn,
            current_user["id"],
            "room.create",
            "room",
            room_id,
            None,
            {
                "name": payload.name,
                "member_count": len(payload.members),
            },
            request,
        )

    return {
        "room": {
            "id": room_id,
            "name": payload.name,
            "description": payload.description,
            "monthly_amount": payload.monthly_amount,
            "payment_day": payload.payment_day,
            "cycle_length_months": payload.cycle_length_months,
            "auto_rotate": payload.auto_rotate,
            "member_count": len(payload.members),
            "created_at": now_str,
        },
        "members": members_payload,
        "payments": payments_payload,
    }


@app.patch("/rooms/{room_id}")
def update_room(room_id: str, payload: RoomUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    with db_session() as conn:
        existing = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="room_not_found")
        require_room_admin(conn, room_id, current_user["id"])
        validate_text_length(payload.name if payload.name is not None else existing["name"], "room_name")
        name = payload.name if payload.name is not None else existing["name"]
        if payload.description is not None:
            description = normalize_optional(payload.description)
            validate_description_length(description)
        else:
            description = existing["description"]
        monthly_amount = payload.monthly_amount if payload.monthly_amount is not None else existing["monthly_amount"]
        payment_day = payload.payment_day if payload.payment_day is not None else existing["payment_day"]
        cycle_length = payload.cycle_length_months if payload.cycle_length_months is not None else existing["cycle_length_months"]
        auto_rotate = payload.auto_rotate if payload.auto_rotate is not None else bool(existing["auto_rotate"]) if existing["auto_rotate"] is not None else None
        member_count = payload.member_count if payload.member_count is not None else existing["member_count"]
        conn.execute(
            """
            UPDATE rooms
            SET name = ?, description = ?, monthly_amount = ?, payment_day = ?, cycle_length_months = ?, auto_rotate = ?, member_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                name,
                description,
                monthly_amount,
                payment_day,
                cycle_length,
                1 if auto_rotate else 0 if auto_rotate is not None else None,
                member_count,
                now_iso(),
                room_id,
            ),
        )
        updated = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        log_event(conn, current_user["id"], "room.update", "room", room_id, dict(existing), dict(updated), request)

    return {
        "id": updated["id"],
        "name": updated["name"],
        "description": updated["description"],
        "monthly_amount": updated["monthly_amount"],
        "payment_day": updated["payment_day"],
        "cycle_length_months": updated["cycle_length_months"],
        "auto_rotate": bool(updated["auto_rotate"]) if updated["auto_rotate"] is not None else None,
        "member_count": updated["member_count"],
        "created_at": updated["created_at"],
    }


@app.delete("/rooms/{room_id}", response_model=MessageResponse)
def delete_room(room_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    with db_session() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="room_not_found")
        require_room_admin(conn, room_id, current_user["id"])
        if room["created_by"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="room_delete_forbidden")

        paid = conn.execute(
            "SELECT COUNT(*) as cnt FROM payments WHERE room_id = ? AND status = 'PAID'",
            (room_id,),
        ).fetchone()
        if paid and paid["cnt"] > 0:
            raise HTTPException(status_code=409, detail="room_has_paid_payments")

        before = serialize_room(room)
        conn.execute("DELETE FROM payments WHERE room_id = ?", (room_id,))
        conn.execute("DELETE FROM room_members WHERE room_id = ?", (room_id,))
        conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        log_event(conn, current_user["id"], "room.delete", "room", room_id, before, None, request)

    return MessageResponse(message="room_deleted")


@app.get("/rooms")
def list_rooms(current_user: dict = Depends(get_current_user)):
    with db_session() as conn:
        rooms = conn.execute(
            """
            SELECT rooms.id, rooms.name, rooms.description, rooms.monthly_amount, rooms.payment_day, rooms.cycle_length_months,
                   rooms.auto_rotate, rooms.member_count, rooms.created_by, rooms.created_at, rooms.updated_at
            FROM rooms
            JOIN room_members ON room_members.room_id = rooms.id
            WHERE room_members.user_id = ?
            ORDER BY rooms.created_at DESC
            """,
            (current_user["id"],),
        ).fetchall()
    response = []
    for room in rooms:
        data = serialize_room(room)
        response.append(data)
    return response


@app.get("/rooms/{room_id}")
def get_room(room_id: str, current_user: dict = Depends(get_current_user)):
    with db_session() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="room_not_found")
        require_room_member(conn, room_id, current_user["id"])
        members = conn.execute(
            """
            SELECT room_members.user_id, room_members.role, room_members.order_index,
                   users.email, users.name
            FROM room_members
            JOIN users ON users.id = room_members.user_id
            WHERE room_members.room_id = ?
            ORDER BY room_members.order_index ASC
            """,
            (room_id,),
        ).fetchall()
        payments = conn.execute(
            "SELECT * FROM payments WHERE room_id = ? ORDER BY month DESC",
            (room_id,),
        ).fetchall()

    return {
        "room": serialize_room(room),
        "members": [serialize_member(row) for row in members],
        "payments": [serialize_payment(row) for row in payments],
    }


@app.get("/rooms/{room_id}/members")
def room_members(room_id: str, current_user: dict = Depends(get_current_user)):
    with db_session() as conn:
        require_room_member(conn, room_id, current_user["id"])
        members = conn.execute(
            """
            SELECT room_members.user_id, room_members.role, room_members.order_index,
                   users.email, users.name
            FROM room_members
            JOIN users ON users.id = room_members.user_id
            WHERE room_members.room_id = ?
            ORDER BY room_members.order_index ASC
            """,
            (room_id,),
        ).fetchall()
    return [serialize_member(row) for row in members]


@app.get("/rooms/{room_id}/payments")
def room_payments(room_id: str, current_user: dict = Depends(get_current_user)):
    with db_session() as conn:
        require_room_member(conn, room_id, current_user["id"])
        payments = conn.execute(
            "SELECT * FROM payments WHERE room_id = ? ORDER BY month DESC",
            (room_id,),
        ).fetchall()
    return [serialize_payment(row) for row in payments]


@app.patch("/payments/{payment_id}")
def update_payment(payment_id: str, payload: PaymentStatusUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    status_value = normalize_status(payload.status)
    with db_session() as conn:
        existing = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="payment_not_found")
        role = require_room_member(conn, existing["room_id"], current_user["id"])
        if role != "ADMIN" and existing["payer_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="payment_update_forbidden")
        conn.execute(
            "UPDATE payments SET status = ?, updated_at = ? WHERE id = ?",
            (status_value, now_iso(), payment_id),
        )
        updated = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        log_event(conn, current_user["id"], "payment.update", "payment", payment_id, dict(existing), dict(updated), request)

    return serialize_payment(updated)


@app.patch("/rooms/{room_id}/schedule")
def update_schedule(room_id: str, payload: ScheduleUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="schedule_empty")

    with db_session() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="room_not_found")
        require_room_admin(conn, room_id, current_user["id"])
        members = conn.execute(
            "SELECT user_id FROM room_members WHERE room_id = ? ORDER BY order_index ASC",
            (room_id,),
        ).fetchall()
        member_ids = [row["user_id"] for row in members]
        if not member_ids:
            raise HTTPException(status_code=400, detail="members_missing")
        clamped_day = max(1, min(room["payment_day"] or 1, 28))

        for item in payload.items:
            month_date = parse_iso_date(item.month, "month")
            month_prefix = month_date.strftime("%Y-%m")
            target_month = month_date.replace(day=clamped_day)
            receiver_id = item.receiver_id
            if receiver_id not in member_ids:
                raise HTTPException(status_code=400, detail="receiver_invalid")

            existing_payments = conn.execute(
                "SELECT * FROM payments WHERE room_id = ? AND substr(month, 1, 7) = ?",
                (room_id, month_prefix),
            ).fetchall()
            payment_by_payer = {}
            extra_ids = []
            for row in existing_payments:
                row_dict = dict(row)
                payer_id = row_dict["payer_id"]
                row_day = int(row_dict["month"][8:10])
                if payer_id not in payment_by_payer:
                    payment_by_payer[payer_id] = row_dict
                else:
                    existing = payment_by_payer[payer_id]
                    existing_day = int(existing["month"][8:10])
                    if existing_day == clamped_day:
                        extra_ids.append(row_dict["id"])
                    elif row_day == clamped_day:
                        extra_ids.append(existing["id"])
                        payment_by_payer[payer_id] = row_dict
                    else:
                        extra_ids.append(row_dict["id"])
            for payment_id in extra_ids:
                conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))

            for payer_id in list(payment_by_payer.keys()):
                if payer_id not in member_ids:
                    conn.execute("DELETE FROM payments WHERE id = ?", (payment_by_payer[payer_id]["id"],))

            for payer_id in member_ids:
                if payer_id == receiver_id:
                    if payer_id in payment_by_payer:
                        conn.execute("DELETE FROM payments WHERE id = ?", (payment_by_payer[payer_id]["id"],))
                    continue

                if payer_id in payment_by_payer:
                    conn.execute(
                        "UPDATE payments SET receiver_id = ?, month = ?, updated_at = ? WHERE id = ?",
                        (receiver_id, target_month.isoformat(), now_iso(), payment_by_payer[payer_id]["id"]),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO payments (id, room_id, payer_id, receiver_id, amount, month, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid4()),
                            room_id,
                            payer_id,
                            receiver_id,
                            room["monthly_amount"],
                            target_month.isoformat(),
                            "EXPECTED",
                            now_iso(),
                            now_iso(),
                        ),
                    )

        log_event(
            conn,
            current_user["id"],
            "room.schedule_update",
            "room",
            room_id,
            None,
            {"items": [item.dict() for item in payload.items]},
            request,
        )

    return {"message": "schedule_updated"}
