from tests.helpers import auth_headers, google_sign_in, register_and_verify


def test_register_verify_login_flow_persists_user_and_audit_log(app_ctx):
    data = register_and_verify(
        app_ctx,
        email="qa-auth@example.com",
        name="alice",
        last_name="smith",
        patronymic="johnson",
        code="654321",
    )

    assert data["user"]["email"] == "qa-auth@example.com"
    assert data["user"]["name"] == "Alice"
    assert data["user"]["last_name"] == "Smith"
    assert data["user"]["patronymic"] == "Johnson"
    assert data["access_token"]
    assert data["refresh_token"]
    assert len(app_ctx["sent_emails"]) == 1

    login_response = app_ctx["client"].post(
        "/auth/login",
        json={
            "email": "qa-auth@example.com",
            "password": "12345678",
        },
    )
    assert login_response.status_code == 200, login_response.text

    with app_ctx["db"].db_session() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            ("qa-auth@example.com",),
        ).fetchone()
        assert user is not None
        assert user["email_verified"] == 1
        assert user["password_hash"] != "12345678"
        actions = [
            row["action"]
            for row in conn.execute(
                "SELECT action FROM audit_log ORDER BY created_at ASC"
            ).fetchall()
        ]

    assert "user.create" in actions
    assert "auth.register.request_otp" in actions
    assert "auth.register.verify" in actions
    assert "auth.login" in actions


def test_google_login_creates_user_and_audit_log(app_ctx):
    data = google_sign_in(
        app_ctx,
        email="google-user@example.com",
        subject="google-sub-1",
        name="Alice Smith",
        given_name="Alice",
        family_name="Smith",
    )

    assert data["user"]["email"] == "google-user@example.com"
    assert data["user"]["name"] == "Alice"
    assert data["user"]["last_name"] == "Smith"
    assert data["user"]["photo_url"] == "https://example.com/avatar.png"
    assert data["access_token"]
    assert data["refresh_token"]
    assert app_ctx["sent_emails"] == []

    with app_ctx["db"].db_session() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            ("google-user@example.com",),
        ).fetchone()
        assert user is not None
        assert user["auth_provider"] == "google"
        assert user["google_sub"] == "google-sub-1"
        assert user["email_verified"] == 1
        actions = [
            row["action"]
            for row in conn.execute(
                "SELECT action FROM audit_log ORDER BY created_at ASC"
            ).fetchall()
        ]

    assert "user.create" in actions
    assert "auth.google.login" in actions


def test_google_login_links_existing_email_user(app_ctx):
    existing = register_and_verify(
        app_ctx,
        email="linked@example.com",
        name="alice",
        last_name="smith",
        patronymic="johnson",
        code="654322",
    )

    linked = google_sign_in(
        app_ctx,
        email="linked@example.com",
        subject="google-linked-sub",
        name="Alice Smith",
        given_name="Alice",
        family_name="Smith",
    )

    assert linked["user"]["id"] == existing["user"]["id"]

    with app_ctx["db"].db_session() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            ("linked@example.com",),
        ).fetchone()
        assert user is not None
        assert user["auth_provider"] == "google"
        assert user["google_sub"] == "google-linked-sub"


def test_google_login_rejects_unverified_google_email(app_ctx):
    client = app_ctx["client"]
    response = client.post(
        "/auth/google",
        json={
            "id_token": (
                "mock-google:{\"email\":\"not-verified@example.com\","
                "\"sub\":\"google-sub-2\",\"email_verified\":false}"
            )
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "google_email_not_verified"


def test_request_otp_rejects_existing_verified_email(app_ctx):
    register_and_verify(app_ctx, email="existing@example.com", code="111111")
    with app_ctx["db"].db_session() as conn:
        conn.execute("DELETE FROM otp_codes WHERE email = ?", ("existing@example.com",))

    response = app_ctx["client"].post(
        "/auth/request-otp",
        json={
            "email": "existing@example.com",
            "password": "12345678",
            "name": "alice",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "email_exists"


def test_request_otp_returns_error_when_email_delivery_fails(app_ctx):
    def failing_send_email(recipient: str, subject: str, body: str):
        raise RuntimeError("smtp_send_failed: rejected")

    app_ctx["main"].send_email = failing_send_email

    response = app_ctx["client"].post(
        "/auth/request-otp",
        json={
            "email": "smtp-failure@example.com",
            "password": "12345678",
            "name": "alice",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "otp_delivery_failed"

    with app_ctx["db"].db_session() as conn:
        otp = conn.execute(
            "SELECT * FROM otp_codes WHERE email = ?",
            ("smtp-failure@example.com",),
        ).fetchone()
        assert otp is None

        actions = [
            row["action"]
            for row in conn.execute(
                "SELECT action FROM audit_log WHERE action = 'auth.otp_email_failed'"
            ).fetchall()
        ]
        assert actions == ["auth.otp_email_failed"]


def test_login_lockout_after_repeated_failed_attempts(app_ctx):
    register_and_verify(app_ctx, email="locked@example.com", code="222222")
    with app_ctx["db"].db_session() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at, updated_by)
            VALUES ('login_max_attempts', '2', '2026-04-16T00:00:00', 'test')
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at,
                updated_by = excluded.updated_by
            """
        )

    for _ in range(2):
        response = app_ctx["client"].post(
            "/auth/login",
            json={
                "email": "locked@example.com",
                "password": "wrong-pass",
            },
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid_credentials"

    locked_response = app_ctx["client"].post(
        "/auth/login",
        json={
            "email": "locked@example.com",
            "password": "12345678",
        },
    )

    assert locked_response.status_code == 429
    assert locked_response.json()["detail"] == "login_locked"


def test_logout_cannot_revoke_foreign_refresh_token(app_ctx):
    user_one = google_sign_in(app_ctx, email="u1@example.com", subject="google-u1")
    user_two = google_sign_in(app_ctx, email="u2@example.com", subject="google-u2")

    logout_response = app_ctx["client"].post(
        "/auth/logout",
        headers=auth_headers(user_one["access_token"]),
        json={"refresh_token": user_two["refresh_token"]},
    )
    assert logout_response.status_code == 200, logout_response.text

    refresh_response = app_ctx["client"].post(
        "/auth/refresh",
        json={"refresh_token": user_two["refresh_token"]},
    )
    assert refresh_response.status_code == 200, refresh_response.text

    own_logout_response = app_ctx["client"].post(
        "/auth/logout",
        headers=auth_headers(user_one["access_token"]),
        json={"refresh_token": user_one["refresh_token"]},
    )
    assert own_logout_response.status_code == 200, own_logout_response.text

    revoked_refresh_response = app_ctx["client"].post(
        "/auth/refresh",
        json={"refresh_token": user_one["refresh_token"]},
    )
    assert revoked_refresh_response.status_code == 401
    assert revoked_refresh_response.json()["detail"] == "refresh_not_found"


def test_me_rejects_inactive_user_even_with_valid_access_token(app_ctx):
    registered = google_sign_in(
        app_ctx,
        email="inactive@example.com",
        subject="google-inactive",
    )

    with app_ctx["db"].db_session() as conn:
        conn.execute(
            "UPDATE users SET is_active = 0 WHERE email = ?",
            ("inactive@example.com",),
        )

    response = app_ctx["client"].get(
        "/me",
        headers=auth_headers(registered["access_token"]),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "user_inactive"
