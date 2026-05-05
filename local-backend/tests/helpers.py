import json
from typing import Any, Dict


def auth_headers(access_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def register_and_verify(
    app_ctx: Dict[str, Any],
    *,
    email: str,
    password: str = "12345678",
    name: str = "alice",
    last_name: str = "smith",
    patronymic: str = "johnson",
    code: str = "123456",
):
    client = app_ctx["client"]
    app_ctx["main"].generate_otp_code = lambda: code

    response = client.post(
        "/auth/request-otp",
        json={
            "email": email,
            "password": password,
            "name": name,
            "last_name": last_name,
            "patronymic": patronymic,
        },
    )
    assert response.status_code == 200, response.text

    verify_response = client.post(
        "/auth/verify-otp",
        json={"email": email, "code": code},
    )
    assert verify_response.status_code == 200, verify_response.text
    return verify_response.json()


def google_sign_in(
    app_ctx: Dict[str, Any],
    *,
    email: str,
    subject: str,
    name: str = "Alice",
    given_name: str = "Alice",
    family_name: str = "Smith",
    picture: str = "https://example.com/avatar.png",
    email_verified: bool = True,
):
    client = app_ctx["client"]
    token_payload = json.dumps(
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
    response = client.post(
        "/auth/google",
        json={"id_token": f"mock-google:{token_payload}"},
    )
    assert response.status_code == 200, response.text
    return response.json()
