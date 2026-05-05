from tests.helpers import auth_headers, register_and_verify


def room_payload(owner_email: str):
    return {
        "name": "SecureRoom",
        "description": "security",
        "monthly_amount": 150000,
        "payment_day": 21,
        "cycle_length_months": 1,
        "auto_rotate": True,
        "members": [
            {"email": owner_email, "name": "owner", "role": "ADMIN"},
            {"email": "sec2@example.com", "name": "sec2"},
            {"email": "sec3@example.com", "name": "sec3"},
            {"email": "sec4@example.com", "name": "sec4"},
            {"email": "sec5@example.com", "name": "sec5"},
        ],
    }


def test_otp_bruteforce_blocks_after_max_attempts(app_ctx):
    client = app_ctx["client"]
    app_ctx["main"].generate_otp_code = lambda: "444444"
    with app_ctx["db"].db_session() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at, updated_by)
            VALUES ('otp_max_attempts', '2', '2026-04-16T00:00:00', 'test')
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at,
                updated_by = excluded.updated_by
            """
        )

    request_response = client.post(
        "/auth/request-otp",
        json={
            "email": "otp-brute@example.com",
            "password": "12345678",
            "name": "alice",
        },
    )
    assert request_response.status_code == 200, request_response.text

    for _ in range(2):
        invalid_response = client.post(
            "/auth/verify-otp",
            json={"email": "otp-brute@example.com", "code": "000000"},
        )
        assert invalid_response.status_code == 400
        assert invalid_response.json()["detail"] == "code_invalid"

    blocked_response = client.post(
        "/auth/verify-otp",
        json={"email": "otp-brute@example.com", "code": "444444"},
    )
    assert blocked_response.status_code == 429
    assert blocked_response.json()["detail"] == "code_attempts_exceeded"


def test_otp_code_cannot_be_replayed_after_success(app_ctx):
    client = app_ctx["client"]
    app_ctx["main"].generate_otp_code = lambda: "555555"

    request_response = client.post(
        "/auth/request-otp",
        json={
            "email": "otp-replay@example.com",
            "password": "12345678",
            "name": "alice",
        },
    )
    assert request_response.status_code == 200, request_response.text

    first_verify = client.post(
        "/auth/verify-otp",
        json={"email": "otp-replay@example.com", "code": "555555"},
    )
    assert first_verify.status_code == 200, first_verify.text

    replay_verify = client.post(
        "/auth/verify-otp",
        json={"email": "otp-replay@example.com", "code": "555555"},
    )
    assert replay_verify.status_code == 400
    assert replay_verify.json()["detail"] == "code_not_found"


def test_refresh_token_rejected_for_unverified_user(app_ctx):
    registered = register_and_verify(app_ctx, email="refresh-block@example.com", code="565656")

    with app_ctx["db"].db_session() as conn:
        conn.execute(
            "UPDATE users SET email_verified = 0 WHERE email = ?",
            ("refresh-block@example.com",),
        )

    response = app_ctx["client"].post(
        "/auth/refresh",
        json={"refresh_token": registered["refresh_token"]},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "email_not_verified"


def test_mass_assignment_payload_cannot_override_profile_or_room_ownership(app_ctx):
    user = register_and_verify(app_ctx, email="mass@example.com", code="676767")
    client = app_ctx["client"]
    headers = auth_headers(user["access_token"])

    profile_response = client.patch(
        "/me",
        headers=headers,
        json={
            "name": "maria",
            "email_verified": 0,
            "is_active": 0,
            "email": "attacker@example.com",
        },
    )
    assert profile_response.status_code == 200, profile_response.text

    with app_ctx["db"].db_session() as conn:
        updated_user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            ("mass@example.com",),
        ).fetchone()
        assert updated_user["name"] == "Maria"
        assert updated_user["email_verified"] == 1
        assert updated_user["is_active"] == 1

    room_response = client.post(
        "/rooms",
        headers=headers,
        json={
            **room_payload("mass@example.com"),
            "created_by": "evil-user",
            "member_count": 999,
        },
    )
    assert room_response.status_code == 200, room_response.text
    room_id = room_response.json()["room"]["id"]

    with app_ctx["db"].db_session() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
        assert room["created_by"] == user["user"]["id"]
        assert room["member_count"] == 5


def test_idor_is_blocked_for_rooms_and_payments(app_ctx):
    owner = register_and_verify(app_ctx, email="idor-owner@example.com", code="787878")
    outsider = register_and_verify(app_ctx, email="idor-outsider@example.com", code="797979")
    client = app_ctx["client"]

    room_response = client.post(
        "/rooms",
        headers=auth_headers(owner["access_token"]),
        json=room_payload("idor-owner@example.com"),
    )
    assert room_response.status_code == 200, room_response.text
    room_id = room_response.json()["room"]["id"]
    payment_id = room_response.json()["payments"][0]["id"]

    for path in (
        f"/rooms/{room_id}",
        f"/rooms/{room_id}/members",
        f"/rooms/{room_id}/payments",
    ):
        response = client.get(path, headers=auth_headers(outsider["access_token"]))
        assert response.status_code == 403
        assert response.json()["detail"] == "room_access_denied"

    payment_response = client.patch(
        f"/payments/{payment_id}",
        headers=auth_headers(outsider["access_token"]),
        json={"status": "PAID"},
    )
    assert payment_response.status_code == 403
    assert payment_response.json()["detail"] == "room_access_denied"

    schedule_response = client.patch(
        f"/rooms/{room_id}/schedule",
        headers=auth_headers(outsider["access_token"]),
        json={"items": [{"month": "2024-04-01", "receiver_id": room_response.json()["members"][1]["user_id"]}]},
    )
    assert schedule_response.status_code == 403
    assert schedule_response.json()["detail"] == "room_access_denied"

    delete_response = client.delete(
        f"/rooms/{room_id}",
        headers=auth_headers(outsider["access_token"]),
    )
    assert delete_response.status_code == 403
    assert delete_response.json()["detail"] == "room_access_denied"
