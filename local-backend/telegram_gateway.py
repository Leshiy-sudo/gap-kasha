"""Client for Telegram Gateway API (https://core.telegram.org/gateway) — delivers
OTP codes straight to a user's Telegram account. No bot, no user action beyond
entering their phone number: Telegram delivers the message the same way it
delivers its own login codes.
"""
import os
import logging

import httpx

logger = logging.getLogger("gapkassa.telegram_gateway")

TELEGRAM_GATEWAY_TOKEN = os.getenv("TELEGRAM_GATEWAY_TOKEN", "").strip()
GATEWAY_BASE_URL = os.getenv("TELEGRAM_GATEWAY_BASE_URL", "https://gatewayapi.telegram.org").rstrip("/")


class TelegramGatewayError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class TelegramGatewayNotConfigured(TelegramGatewayError):
    def __init__(self):
        super().__init__("telegram_gateway_not_configured")


def _call(method: str, payload: dict) -> dict:
    if not TELEGRAM_GATEWAY_TOKEN:
        raise TelegramGatewayNotConfigured()
    try:
        response = httpx.post(
            f"{GATEWAY_BASE_URL}/{method}",
            json=payload,
            headers={"Authorization": f"Bearer {TELEGRAM_GATEWAY_TOKEN}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("Telegram Gateway request failed: %s", exc)
        raise TelegramGatewayError("telegram_gateway_unavailable") from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise TelegramGatewayError("telegram_gateway_bad_response") from exc

    if not body.get("ok"):
        error = body.get("error")
        raise TelegramGatewayError(str(error or "telegram_gateway_error"))
    return body.get("result") or {}


def check_send_ability(phone: str) -> bool:
    """Free check: does this phone number have a Telegram account we can message?"""
    result = _call("checkSendAbility", {"phone_number": phone})
    return bool(result.get("request_id"))


def send_verification_code(phone: str, code: str, ttl_seconds: int = 300) -> str:
    """Delivers a code we generated ourselves to the user's Telegram account.
    Returns the Gateway request_id (kept for audit only, not required for verification
    since we verify the code against our own stored hash)."""
    result = _call(
        "sendVerificationMessage",
        {
            "phone_number": phone,
            "code": code,
            "ttl": ttl_seconds,
        },
    )
    return str(result.get("request_id", ""))
