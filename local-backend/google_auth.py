import hashlib
import json
from dataclasses import dataclass
from typing import Optional


MOCK_GOOGLE_PREFIX = "mock-google:"


@dataclass
class GoogleIdentity:
    subject: str
    email: str
    email_verified: bool
    full_name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    nonce: Optional[str] = None


class GoogleTokenVerificationError(Exception):
    def __init__(self, code: str, status_code: int):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class GoogleAuthVerifier:
    def __init__(self, web_client_id: str, allow_mock: bool):
        self.web_client_id = (web_client_id or "").strip()
        self.allow_mock = allow_mock

    def verify(self, token: str, expected_nonce: Optional[str] = None) -> GoogleIdentity:
        raw_token = (token or "").strip()
        if not raw_token:
            raise GoogleTokenVerificationError("google_token_missing", 400)

        if self.allow_mock and raw_token.startswith(MOCK_GOOGLE_PREFIX):
            identity = self._parse_mock_token(raw_token)
        else:
            identity = self._verify_google_token(raw_token)

        if expected_nonce and identity.nonce and identity.nonce != expected_nonce:
            raise GoogleTokenVerificationError("google_nonce_invalid", 401)

        return identity

    def _parse_mock_token(self, raw_token: str) -> GoogleIdentity:
        payload = raw_token[len(MOCK_GOOGLE_PREFIX):].strip()
        if not payload:
            raise GoogleTokenVerificationError("google_mock_token_invalid", 401)

        if payload.startswith("{"):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise GoogleTokenVerificationError("google_mock_token_invalid", 401) from exc
        else:
            data = {"email": payload}

        email = str(data.get("email") or "").strip().lower()
        if not email:
            raise GoogleTokenVerificationError("google_email_missing", 401)

        subject = str(data.get("sub") or f"mock-{hashlib.sha256(email.encode()).hexdigest()[:24]}")
        return GoogleIdentity(
            subject=subject,
            email=email,
            email_verified=bool(data.get("email_verified", True)),
            full_name=_clean_optional(data.get("name")),
            given_name=_clean_optional(data.get("given_name")),
            family_name=_clean_optional(data.get("family_name")),
            picture=_clean_optional(data.get("picture")),
            nonce=_clean_optional(data.get("nonce")),
        )

    def _verify_google_token(self, raw_token: str) -> GoogleIdentity:
        if not self.web_client_id:
            raise GoogleTokenVerificationError("google_auth_not_configured", 503)

        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token
        except ImportError as exc:
            raise GoogleTokenVerificationError("google_auth_unavailable", 503) from exc

        try:
            claims = google_id_token.verify_oauth2_token(
                raw_token,
                google_requests.Request(),
                self.web_client_id,
            )
        except Exception as exc:
            raise GoogleTokenVerificationError("google_token_invalid", 401) from exc

        email = str(claims.get("email") or "").strip().lower()
        subject = str(claims.get("sub") or "").strip()
        if not subject:
            raise GoogleTokenVerificationError("google_subject_missing", 401)
        if not email:
            raise GoogleTokenVerificationError("google_email_missing", 401)

        return GoogleIdentity(
            subject=subject,
            email=email,
            email_verified=bool(claims.get("email_verified")),
            full_name=_clean_optional(claims.get("name")),
            given_name=_clean_optional(claims.get("given_name")),
            family_name=_clean_optional(claims.get("family_name")),
            picture=_clean_optional(claims.get("picture")),
            nonce=_clean_optional(claims.get("nonce")),
        )


def build_mock_google_token(
    email: str,
    *,
    subject: Optional[str] = None,
    name: Optional[str] = None,
    given_name: Optional[str] = None,
    family_name: Optional[str] = None,
    picture: Optional[str] = None,
    email_verified: bool = True,
) -> str:
    payload = json.dumps(
        {
            "email": email,
            "sub": subject,
            "name": name,
            "given_name": given_name,
            "family_name": family_name,
            "picture": picture,
            "email_verified": email_verified,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return f"{MOCK_GOOGLE_PREFIX}{payload}"


def _clean_optional(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
