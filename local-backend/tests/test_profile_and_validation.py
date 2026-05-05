from tests.helpers import auth_headers, google_sign_in, register_and_verify


def test_profile_update_requires_name_and_capitalizes_person_fields(app_ctx):
    user = register_and_verify(app_ctx, email="profile@example.com", code="888888")
    client = app_ctx["client"]
    headers = auth_headers(user["access_token"])

    update_response = client.patch(
        "/me",
        headers=headers,
        json={
            "name": "   ivan",
            "last_name": "petrov",
            "patronymic": "sergeevich",
        },
    )
    assert update_response.status_code == 200, update_response.text
    payload = update_response.json()
    assert payload["name"] == "Ivan"
    assert payload["last_name"] == "Petrov"
    assert payload["patronymic"] == "Sergeevich"

    empty_name_response = client.patch(
        "/me",
        headers=headers,
        json={"name": "   "},
    )
    assert empty_name_response.status_code == 400
    assert empty_name_response.json()["detail"] == "name_required"


def test_validation_rejects_short_device_token_and_small_room(app_ctx):
    user = register_and_verify(app_ctx, email="validation@example.com", code="999999")
    client = app_ctx["client"]
    headers = auth_headers(user["access_token"])

    token_response = client.post(
        "/devices/fcm-token",
        headers=headers,
        json={"token": "short", "platform": "android"},
    )
    assert token_response.status_code == 400
    assert token_response.json()["detail"] == "token_invalid"

    room_response = client.post(
        "/rooms",
        headers=headers,
        json={
            "name": "Tiny Room",
            "description": "small",
            "monthly_amount": 1000,
            "payment_day": 5,
            "cycle_length_months": 1,
            "auto_rotate": True,
            "members": [
                {"email": "validation@example.com", "name": "owner", "role": "ADMIN"},
                {"email": "a2@example.com", "name": "a2"},
                {"email": "a3@example.com", "name": "a3"},
                {"email": "a4@example.com", "name": "a4"},
            ],
        },
    )
    assert room_response.status_code == 400
    assert room_response.json()["detail"] == "members_invalid"


def test_validation_enforces_text_limits_for_room_fields(app_ctx):
    user = register_and_verify(app_ctx, email="limits@example.com", code="121212")
    client = app_ctx["client"]
    headers = auth_headers(user["access_token"])

    too_long_name_response = client.post(
        "/rooms",
        headers=headers,
        json={
            "name": "R" * 31,
            "description": "ok",
            "monthly_amount": 1000,
            "payment_day": 5,
            "cycle_length_months": 1,
            "auto_rotate": True,
            "members": [
                {"email": "limits@example.com", "name": "owner", "role": "ADMIN"},
                {"email": "b2@example.com", "name": "b2"},
                {"email": "b3@example.com", "name": "b3"},
                {"email": "b4@example.com", "name": "b4"},
                {"email": "b5@example.com", "name": "b5"},
            ],
        },
    )
    assert too_long_name_response.status_code == 400
    assert too_long_name_response.json()["detail"] == "room_name_too_long"

    too_long_description_response = client.post(
        "/rooms",
        headers=headers,
        json={
            "name": "Valid room",
            "description": "D" * 201,
            "monthly_amount": 1000,
            "payment_day": 5,
            "cycle_length_months": 1,
            "auto_rotate": True,
            "members": [
                {"email": "limits@example.com", "name": "owner", "role": "ADMIN"},
                {"email": "c2@example.com", "name": "c2"},
                {"email": "c3@example.com", "name": "c3"},
                {"email": "c4@example.com", "name": "c4"},
                {"email": "c5@example.com", "name": "c5"},
            ],
        },
    )
    assert too_long_description_response.status_code == 400
    assert too_long_description_response.json()["detail"] == "description_too_long"


def test_delete_me_removes_user_and_returns_success(app_ctx):
    auth = google_sign_in(
        app_ctx,
        email="delete-me@example.com",
        subject="delete-me-subject",
        name="Delete Me",
        given_name="Delete",
        family_name="Me",
    )
    client = app_ctx["client"]
    headers = auth_headers(auth["access_token"])

    delete_response = client.delete("/me", headers=headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["message"] == "account_deleted"

    with app_ctx["db"].db_session() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            ("delete-me@example.com",),
        ).fetchone()
        assert user is None


def test_client_error_report_sends_email(app_ctx):
    client = app_ctx["client"]

    response = client.post(
        "/client-errors",
        json={
            "kind": "fatal",
            "report_id": "report-123",
            "occurred_at": "2026-05-05T12:30:00Z",
            "exception_type": "java.lang.IllegalStateException",
            "message": "Crash in profile screen",
            "stacktrace": "java.lang.IllegalStateException: Crash in profile screen",
            "thread_name": "main",
            "app_version": "26.02",
            "build_type": "release",
            "package_name": "com.gapkassa",
            "api_base_url": "https://api.example.com/",
            "device_model": "Pixel 8",
            "android_version": "15",
            "user_id": "user-1",
            "user_email": "qa@example.com",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["message"] == "client_error_reported"
    assert len(app_ctx["sent_emails"]) == 1
    assert app_ctx["sent_emails"][0]["recipient"] == "alerts@example.com"
    assert "Crash in profile screen" in app_ctx["sent_emails"][0]["body"]
