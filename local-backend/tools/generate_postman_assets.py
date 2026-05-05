import json
from pathlib import Path
from typing import List, Optional


ROOT = Path(__file__).resolve().parents[2]
POSTMAN_DIR = ROOT / "postman"


def script(*lines: str) -> str:
    return "\n".join(lines)


def event(listen: str, script_text: str) -> dict:
    return {
        "listen": listen,
        "script": {
            "type": "text/javascript",
            "exec": script_text.splitlines(),
        },
    }


def url(path: str, query: Optional[List[dict]] = None) -> dict:
    raw = "{{baseUrl}}" + path
    if query:
        query_string = "&".join(f"{item['key']}={item['value']}" for item in query)
        raw += "?" + query_string
    return {
        "raw": raw,
        "host": ["{{baseUrl}}"],
        "path": [part for part in path.strip("/").split("/") if part],
        **({"query": query} if query else {}),
    }


def json_body(payload: str) -> dict:
    return {
        "mode": "raw",
        "raw": payload,
        "options": {"raw": {"language": "json"}},
    }


def request_item(
    name: str,
    method: str,
    path: str,
    *,
    body: Optional[str] = None,
    query: Optional[List[dict]] = None,
    auth: Optional[dict] = None,
    tests: Optional[str] = None,
    prerequest: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    item = {
        "name": name,
        "request": {
            "method": method,
            "header": [{"key": "Content-Type", "value": "application/json"}] if body else [],
            "url": url(path, query),
            **({"body": json_body(body)} if body else {}),
            **({"auth": auth} if auth else {}),
            **({"description": description} if description else {}),
        },
        "response": [],
    }
    events = []
    if prerequest:
        events.append(event("prerequest", prerequest))
    if tests:
        events.append(event("test", tests))
    if events:
        item["event"] = events
    return item


def bearer_auth() -> dict:
    return {"type": "bearer", "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}]}


def basic_auth() -> dict:
    return {
        "type": "basic",
        "basic": [
            {"key": "username", "value": "{{adminUsername}}", "type": "string"},
            {"key": "password", "value": "{{adminPassword}}", "type": "string"},
        ],
    }


def build_collection() -> dict:
    assert_test = script(
        "pm.test('HTTP 200', function () {",
        "  pm.response.to.have.status(200);",
        "});",
    )

    return {
        "info": {
            "name": "GapKassa Local API",
            "_postman_id": "cbe31674-7e77-41ad-bdbe-6f32bf596c49",
            "description": "Local Postman collection for GapKassa backend. Manual/destructive requests are prefixed with [MANUAL].",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": [
            {
                "name": "Public",
                "item": [
                    request_item(
                        "Health",
                        "GET",
                        "/health",
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.status).to.eql('ok');",
                        ),
                    ),
                    request_item(
                        "App Config RU",
                        "GET",
                        "/app/config",
                        query=[{"key": "lang", "value": "ru"}],
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.ads).to.be.an('object');",
                            "pm.expect(json.texts).to.be.an('object');",
                        ),
                    ),
                    request_item(
                        "App Config UZ",
                        "GET",
                        "/app/config",
                        query=[{"key": "lang", "value": "uz"}],
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.ads).to.be.an('object');",
                            "pm.expect(json.texts).to.be.an('object');",
                        ),
                    ),
                    request_item(
                        "Privacy Policy",
                        "GET",
                        "/legal/privacy-policy",
                        tests=script(
                            assert_test,
                            "pm.expect(pm.response.text()).to.include('Privacy Policy');",
                        ),
                    ),
                    request_item(
                        "Delete Account Page",
                        "GET",
                        "/legal/delete-account",
                        tests=script(
                            assert_test,
                            "pm.expect(pm.response.text()).to.include('Delete Account');",
                        ),
                    ),
                ],
            },
            {
                "name": "Auth",
                "item": [
                    request_item(
                        "Request OTP [MANUAL]",
                        "POST",
                        "/auth/request-otp",
                        body=json.dumps(
                            {
                                "email": "{{otpEmail}}",
                                "password": "{{otpPassword}}",
                                "name": "Postman",
                                "last_name": "Otp",
                                "patronymic": "Flow",
                                "phone": "+998901112233",
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        prerequest=script(
                            "pm.environment.set('otpEmail', `postman-otp-${Date.now()}@example.com`);",
                            "pm.environment.set('otpPassword', '12345678');",
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.message).to.eql('otp_sent');",
                        ),
                        description="Creates a new OTP registration candidate. Fill otp_code manually in the next request.",
                    ),
                    request_item(
                        "Verify OTP [MANUAL]",
                        "POST",
                        "/auth/verify-otp",
                        body=json.dumps(
                            {
                                "email": "{{otpEmail}}",
                                "code": "{{otpCode}}",
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.environment.set('access_token', json.access_token);",
                            "pm.environment.set('refresh_token', json.refresh_token);",
                            "pm.environment.set('user_id', json.user.id);",
                        ),
                        description="Paste the OTP code into otpCode before sending.",
                    ),
                    request_item(
                        "Login",
                        "POST",
                        "/auth/login",
                        body=json.dumps(
                            {
                                "email": "{{testEmail}}",
                                "password": "{{testPassword}}",
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.user.email).to.eql(pm.environment.get('testEmail'));",
                            "pm.environment.set('access_token', json.access_token);",
                            "pm.environment.set('refresh_token', json.refresh_token);",
                            "pm.environment.set('user_id', json.user.id);",
                        ),
                    ),
                    request_item(
                        "Refresh Token",
                        "POST",
                        "/auth/refresh",
                        body=json.dumps({"refresh_token": "{{refresh_token}}"}, ensure_ascii=False, indent=2),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.environment.set('access_token', json.access_token);",
                            "pm.environment.set('refresh_token', json.refresh_token);",
                        ),
                    ),
                    request_item(
                        "Logout",
                        "POST",
                        "/auth/logout",
                        auth=bearer_auth(),
                        body=json.dumps({"refresh_token": "{{refresh_token}}"}, ensure_ascii=False, indent=2),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.message).to.eql('logged_out');",
                        ),
                    ),
                ],
            },
            {
                "name": "Profile And Device",
                "auth": bearer_auth(),
                "item": [
                    request_item(
                        "Register FCM Token",
                        "POST",
                        "/devices/fcm-token",
                        auth=bearer_auth(),
                        body=json.dumps(
                            {
                                "token": "postman-fcm-{{$guid}}-01234567890123456789",
                                "platform": "android",
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.message).to.eql('device_token_saved');",
                        ),
                    ),
                    request_item(
                        "Get Me",
                        "GET",
                        "/me",
                        auth=bearer_auth(),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.email).to.eql(pm.environment.get('testEmail'));",
                        ),
                    ),
                    request_item(
                        "Update Me",
                        "PATCH",
                        "/me",
                        auth=bearer_auth(),
                        body=json.dumps(
                            {
                                "name": "Postman",
                                "last_name": "Runner",
                                "patronymic": "Smoke",
                                "phone": "+998901234567",
                                "photo_url": "https://example.com/avatar-postman.png",
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.name).to.eql('Postman');",
                            "pm.expect(json.last_name).to.eql('Runner');",
                        ),
                    ),
                ],
            },
            {
                "name": "Rooms",
                "auth": bearer_auth(),
                "item": [
                    request_item(
                        "List Rooms",
                        "GET",
                        "/rooms",
                        auth=bearer_auth(),
                        tests=script(
                            assert_test,
                            "pm.expect(pm.response.json()).to.be.an('array');",
                        ),
                    ),
                    request_item(
                        "Create Room",
                        "POST",
                        "/rooms",
                        auth=bearer_auth(),
                        body=json.dumps(
                            {
                                "name": "GapKassa Postman {{$timestamp}}",
                                "description": "Room created from Postman collection",
                                "monthly_amount": 120000,
                                "payment_day": 15,
                                "cycle_length_months": 2,
                                "auto_rotate": True,
                                "members": [
                                    {"email": "{{testEmail}}", "name": "owner", "role": "ADMIN"},
                                    {"email": "postman-member2@example.com", "name": "member2"},
                                    {"email": "postman-member3@example.com", "name": "member3"},
                                    {"email": "postman-member4@example.com", "name": "member4"},
                                    {"email": "postman-member5@example.com", "name": "member5"},
                                ],
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.room.member_count).to.eql(5);",
                            "pm.environment.set('room_id', json.room.id);",
                            "pm.environment.set('payment_id', json.payments[0].id);",
                            "pm.environment.set('receiver_id', json.members[1].user_id);",
                        ),
                    ),
                    request_item(
                        "Get Room",
                        "GET",
                        "/rooms/{{room_id}}",
                        auth=bearer_auth(),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.room.id).to.eql(pm.environment.get('room_id'));",
                            "pm.expect(json.members.length).to.be.at.least(5);",
                        ),
                    ),
                    request_item(
                        "Get Room Members",
                        "GET",
                        "/rooms/{{room_id}}/members",
                        auth=bearer_auth(),
                        tests=script(
                            assert_test,
                            "pm.expect(pm.response.json()).to.be.an('array');",
                        ),
                    ),
                    request_item(
                        "Get Room Payments",
                        "GET",
                        "/rooms/{{room_id}}/payments",
                        auth=bearer_auth(),
                        tests=script(
                            assert_test,
                            "pm.expect(pm.response.json()).to.be.an('array');",
                        ),
                    ),
                    request_item(
                        "Update Payment",
                        "PATCH",
                        "/payments/{{payment_id}}",
                        auth=bearer_auth(),
                        body=json.dumps({"status": "PAID"}, ensure_ascii=False, indent=2),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.status).to.eql('PAID');",
                        ),
                    ),
                    request_item(
                        "Update Schedule",
                        "PATCH",
                        "/rooms/{{room_id}}/schedule",
                        auth=bearer_auth(),
                        body=json.dumps(
                            {"items": [{"month": "2026-06-01", "receiver_id": "{{receiver_id}}"}]},
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.message).to.eql('schedule_updated');",
                        ),
                    ),
                    request_item(
                        "Update Room",
                        "PATCH",
                        "/rooms/{{room_id}}",
                        auth=bearer_auth(),
                        body=json.dumps(
                            {
                                "name": "GapKassa Postman Updated",
                                "description": "Updated from Postman",
                                "monthly_amount": 130000,
                                "payment_day": 18,
                                "cycle_length_months": 2,
                                "auto_rotate": True,
                                "member_count": 5,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.name).to.eql('GapKassa Postman Updated');",
                        ),
                    ),
                    request_item(
                        "Delete Room [MANUAL]",
                        "DELETE",
                        "/rooms/{{room_id}}",
                        auth=bearer_auth(),
                        tests=script(
                            "pm.test('HTTP 200 or 409', function () {",
                            "  pm.expect([200, 409]).to.include(pm.response.code);",
                            "});",
                        ),
                        description="Manual because deleting a room is destructive and will fail with 409 if a payment is already marked PAID.",
                    ),
                ],
            },
            {
                "name": "Admin",
                "auth": basic_auth(),
                "item": [
                    request_item(
                        "Overview",
                        "GET",
                        "/admin/api/overview",
                        auth=basic_auth(),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.stats).to.be.an('object');",
                        ),
                    ),
                    request_item(
                        "Get Settings",
                        "GET",
                        "/admin/api/settings",
                        auth=basic_auth(),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.settings).to.be.an('object');",
                        ),
                    ),
                    request_item(
                        "Update Settings",
                        "PUT",
                        "/admin/api/settings",
                        auth=basic_auth(),
                        body=json.dumps(
                            {
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
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.message).to.eql('settings_saved');",
                        ),
                    ),
                    request_item(
                        "Get Content",
                        "GET",
                        "/admin/api/content",
                        auth=basic_auth(),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.locales).to.be.an('object');",
                        ),
                    ),
                    request_item(
                        "Update Content",
                        "PUT",
                        "/admin/api/content",
                        auth=basic_auth(),
                        body=json.dumps(
                            {
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
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.message).to.eql('content_saved');",
                        ),
                    ),
                    request_item(
                        "Autotest Status",
                        "GET",
                        "/admin/api/tests",
                        auth=basic_auth(),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.summary).to.be.an('object');",
                        ),
                    ),
                    request_item(
                        "Run Backend Autotests [MANUAL]",
                        "POST",
                        "/admin/api/tests/run",
                        auth=basic_auth(),
                        body=json.dumps({"suites": ["backend_api"]}, ensure_ascii=False, indent=2),
                        tests=script(
                            "pm.test('HTTP 200 or 409', function () {",
                            "  pm.expect([200, 409]).to.include(pm.response.code);",
                            "});",
                        ),
                    ),
                    request_item(
                        "Stop Autotests [MANUAL]",
                        "POST",
                        "/admin/api/tests/stop",
                        auth=basic_auth(),
                        tests=script(
                            assert_test,
                            "const json = pm.response.json();",
                            "pm.expect(json.message).to.eql('autotests_stopped');",
                        ),
                    ),
                ],
            },
            {
                "name": "Destructive Manual",
                "item": [
                    request_item(
                        "Delete Current User [MANUAL]",
                        "DELETE",
                        "/me",
                        auth=bearer_auth(),
                        tests=script(
                            "pm.test('HTTP 200 or 401', function () {",
                            "  pm.expect([200, 401]).to.include(pm.response.code);",
                            "});",
                        ),
                    ),
                    request_item(
                        "Public Delete Account [MANUAL]",
                        "POST",
                        "/legal/delete-account/request",
                        body=json.dumps(
                            {
                                "email": "{{testEmail}}",
                                "password": "{{testPassword}}",
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        tests=script(
                            "pm.test('HTTP 200 or 404 or 401', function () {",
                            "  pm.expect([200, 401, 404]).to.include(pm.response.code);",
                            "});",
                        ),
                    ),
                ],
            },
        ],
        "variable": [
            {"key": "baseUrl", "value": "http://127.0.0.1:8080"},
        ],
    }


def build_environment() -> dict:
    return {
        "name": "GapKassa Local",
        "values": [
            {"key": "baseUrl", "value": "http://127.0.0.1:8080", "enabled": True},
            {"key": "adminUsername", "value": "admin", "enabled": True},
            {"key": "adminPassword", "value": "admin", "enabled": True},
            {"key": "testEmail", "value": "uiqa@example.com", "enabled": True},
            {"key": "testPassword", "value": "12345678", "enabled": True},
            {"key": "otpEmail", "value": "", "enabled": True},
            {"key": "otpPassword", "value": "12345678", "enabled": True},
            {"key": "otpCode", "value": "", "enabled": True},
            {"key": "access_token", "value": "", "enabled": True},
            {"key": "refresh_token", "value": "", "enabled": True},
            {"key": "user_id", "value": "", "enabled": True},
            {"key": "room_id", "value": "", "enabled": True},
            {"key": "payment_id", "value": "", "enabled": True},
            {"key": "receiver_id", "value": "", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_at": "2026-04-17T00:00:00.000Z",
        "_postman_exported_using": "Codex",
    }


def main():
    POSTMAN_DIR.mkdir(parents=True, exist_ok=True)
    collection_path = POSTMAN_DIR / "GapKassa Local API.postman_collection.json"
    environment_path = POSTMAN_DIR / "GapKassa Local.postman_environment.json"

    collection_path.write_text(
        json.dumps(build_collection(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    environment_path.write_text(
        json.dumps(build_environment(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(collection_path)
    print(environment_path)


if __name__ == "__main__":
    main()
