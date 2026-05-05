import base64
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple, Union
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:8080"
ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = ROOT / "local-backend" / "tools" / "seed_ui_test_data.py"


def api_request(
    method: str,
    path: str,
    *,
    json_body: Optional[dict] = None,
    bearer_token: Optional[str] = None,
    basic_auth: Optional[Tuple[str, str]] = None,
) -> Tuple[int, Union[dict, list, str]]:
    headers = {}
    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    if basic_auth:
        creds = base64.b64encode(f"{basic_auth[0]}:{basic_auth[1]}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {creds}"

    request = Request(BASE_URL + path, data=body, headers=headers, method=method)
    try:
        with urlopen(request) as response:
            content_type = response.headers.get("Content-Type", "")
            payload = response.read().decode("utf-8")
            if "application/json" in content_type:
                return response.status, json.loads(payload)
            return response.status, payload
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(payload)
        except json.JSONDecodeError:
            return exc.code, payload


def expect(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def main():
    subprocess.check_call([sys.executable, str(SEED_SCRIPT)])

    status, health = api_request("GET", "/health")
    expect(status == 200 and health["status"] == "ok", "health failed")

    status, config = api_request("GET", "/app/config?lang=ru")
    expect(status == 200 and "ads" in config and "texts" in config, "app config failed")

    status, login = api_request(
        "POST",
        "/auth/google",
        json_body={
            "id_token": (
                "mock-google:{\"email\":\"uiqa@example.com\","
                "\"sub\":\"android-ui-test\",\"name\":\"Uiqa\","
                "\"given_name\":\"Uiqa\",\"family_name\":\"\","
                "\"email_verified\":true}"
            )
        },
    )
    expect(status == 200, f"google login failed: {login}")
    access_token = login["access_token"]
    refresh_token = login["refresh_token"]

    status, profile = api_request("GET", "/me", bearer_token=access_token)
    expect(status == 200 and profile["email"] == "uiqa@example.com", "get me failed")

    status, updated_profile = api_request(
        "PATCH",
        "/me",
        bearer_token=access_token,
        json_body={
            "name": "Postman",
            "last_name": "Runner",
            "patronymic": "Smoke",
            "phone": "+998901234567",
            "photo_url": "https://example.com/avatar-postman.png",
        },
    )
    expect(status == 200 and updated_profile["name"] == "Postman", "update me failed")

    status, token_result = api_request(
        "POST",
        "/devices/fcm-token",
        bearer_token=access_token,
        json_body={
            "token": "postman-fcm-smoke-01234567890123456789",
            "platform": "android",
        },
    )
    expect(status == 200 and token_result["message"] == "device_token_saved", "device token failed")

    status, created = api_request(
        "POST",
        "/rooms",
        bearer_token=access_token,
        json_body={
            "name": "GapKassa Smoke Room",
            "description": "Created by api_smoke.py",
            "monthly_amount": 120000,
            "payment_day": 15,
            "cycle_length_months": 2,
            "auto_rotate": True,
            "members": [
                {"email": "uiqa@example.com", "name": "owner", "role": "ADMIN"},
                {"email": "postman-member2@example.com", "name": "member2"},
                {"email": "postman-member3@example.com", "name": "member3"},
                {"email": "postman-member4@example.com", "name": "member4"},
                {"email": "postman-member5@example.com", "name": "member5"},
            ],
        },
    )
    expect(status == 200, f"create room failed: {created}")
    room_id = created["room"]["id"]
    payment_id = created["payments"][0]["id"]
    receiver_id = created["members"][1]["user_id"]

    for path in ("/rooms", f"/rooms/{room_id}", f"/rooms/{room_id}/members", f"/rooms/{room_id}/payments"):
        status, payload = api_request("GET", path, bearer_token=access_token)
        expect(status == 200, f"GET {path} failed: {payload}")

    status, payment = api_request(
        "PATCH",
        f"/payments/{payment_id}",
        bearer_token=access_token,
        json_body={"status": "PAID"},
    )
    expect(status == 200 and payment["status"] == "PAID", "update payment failed")

    status, schedule = api_request(
        "PATCH",
        f"/rooms/{room_id}/schedule",
        bearer_token=access_token,
        json_body={"items": [{"month": "2026-06-01", "receiver_id": receiver_id}]},
    )
    expect(status == 200 and schedule["message"] == "schedule_updated", "update schedule failed")

    status, room = api_request(
        "PATCH",
        f"/rooms/{room_id}",
        bearer_token=access_token,
        json_body={
            "name": "GapKassa Smoke Room Updated",
            "description": "Updated by api_smoke.py",
            "monthly_amount": 130000,
            "payment_day": 18,
            "cycle_length_months": 2,
            "auto_rotate": True,
            "member_count": 5,
        },
    )
    expect(status == 200 and room["name"] == "GapKassa Smoke Room Updated", "update room failed")

    for path in ("/admin/api/overview", "/admin/api/settings", "/admin/api/content", "/admin/api/tests"):
        status, payload = api_request("GET", path, basic_auth=("admin", "admin"))
        expect(status == 200, f"admin GET {path} failed: {payload}")

    status, settings = api_request(
        "PUT",
        "/admin/api/settings",
        basic_auth=("admin", "admin"),
        json_body={
            "settings": {
                "otp_ttl_min": "10",
                "otp_cooldown_sec": "30",
                "otp_max_attempts": "5",
                "login_max_attempts": "5",
                "login_lockout_min": "15",
                "max_text_length": "30",
                "max_description_length": "200",
                "password_min_len": "8",
                "password_max_len": "30",
                "min_members_per_room": "5",
                "max_members_per_room": "20",
                "max_daily_otp_requests": "300",
                "db_soft_limit_mb": "256",
                "outbox_soft_limit_mb": "64",
                "audit_retention_days": "180",
                "ad_enabled": "1",
                "ad_target_url": "https://example.com/postman-ad",
            }
        },
    )
    expect(status == 200 and settings["message"] == "settings_saved", "update settings failed")

    status, content = api_request(
        "PUT",
        "/admin/api/content",
        basic_auth=("admin", "admin"),
        json_body={
            "locales": {
                "ru": {
                    "ad": {
                        "badge": "AD",
                        "title": "Postman admin update",
                        "body": "Коллекция Postman обновила этот рекламный блок локально.",
                        "cta": "Открыть",
                    },
                    "text": {
                        "helper_register_otp": "Код подтверждения отправится на email.",
                        "verification_hint": "Вставьте код из письма или всю ссылку целиком.",
                        "message_verification_sent": "Письмо с кодом успешно отправлено.",
                    },
                },
                "uz": {
                    "ad": {
                        "badge": "AD",
                        "title": "Postman admin update",
                        "body": "Postman kolleksiyasi bu reklama blokini lokal ravishda yangiladi.",
                        "cta": "Ochish",
                    },
                    "text": {
                        "helper_register_otp": "Tasdiqlash kodi emailingizga yuboriladi.",
                        "verification_hint": "Xatdagi kod yoki havolani to‘liq kiriting.",
                        "message_verification_sent": "Kodli xat muvaffaqiyatli yuborildi.",
                    },
                },
            }
        },
    )
    expect(status == 200 and content["message"] == "content_saved", "update content failed")

    status, refreshed = api_request(
        "POST",
        "/auth/refresh",
        json_body={"refresh_token": refresh_token},
    )
    expect(status == 200 and refreshed["access_token"], "refresh failed")

    status, logout = api_request(
        "POST",
        "/auth/logout",
        bearer_token=refreshed["access_token"],
        json_body={"refresh_token": refreshed["refresh_token"]},
    )
    expect(status == 200 and logout["message"] == "logged_out", "logout failed")

    print("API smoke passed")


if __name__ == "__main__":
    main()
