from tests.helpers import auth_headers, register_and_verify


def room_payload(owner_email: str, *, payment_day: int = 15, cycle_length: int = 2):
    members = [
        {"email": owner_email, "name": "owner", "role": "ADMIN"},
        {"email": "member2@example.com", "name": "member2"},
        {"email": "member3@example.com", "name": "member3"},
        {"email": "member4@example.com", "name": "member4"},
        {"email": "member5@example.com", "name": "member5"},
    ]
    return {
        "name": "Room Alpha",
        "description": "Main room",
        "monthly_amount": 120000,
        "payment_day": payment_day,
        "cycle_length_months": cycle_length,
        "auto_rotate": True,
        "members": members,
    }


def test_create_room_persists_members_payments_and_audit_log(app_ctx):
    owner = register_and_verify(app_ctx, email="owner@example.com", code="444444")

    response = app_ctx["client"].post(
        "/rooms",
        headers=auth_headers(owner["access_token"]),
        json=room_payload("owner@example.com"),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    room_id = payload["room"]["id"]

    assert payload["room"]["member_count"] == 5
    assert len(payload["members"]) == 5
    assert len(payload["payments"]) == 8

    with app_ctx["db"].db_session() as conn:
        member_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM room_members WHERE room_id = ?",
            (room_id,),
        ).fetchone()["cnt"]
        payment_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM payments WHERE room_id = ?",
            (room_id,),
        ).fetchone()["cnt"]
        actions = [
            row["action"]
            for row in conn.execute(
                "SELECT action FROM audit_log WHERE entity_id = ?",
                (room_id,),
            ).fetchall()
        ]

    assert member_count == 5
    assert payment_count == 8
    assert "room.create" in actions


def test_delete_room_allowed_before_paid_and_blocked_after_first_paid_payment(app_ctx):
    owner = register_and_verify(app_ctx, email="room-delete@example.com", code="555555")
    client = app_ctx["client"]
    headers = auth_headers(owner["access_token"])

    created = client.post("/rooms", headers=headers, json=room_payload("room-delete@example.com", cycle_length=1))
    assert created.status_code == 200, created.text
    room_id = created.json()["room"]["id"]

    delete_response = client.delete(f"/rooms/{room_id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text

    second_room = client.post("/rooms", headers=headers, json=room_payload("room-delete@example.com", cycle_length=1))
    assert second_room.status_code == 200, second_room.text
    room_id = second_room.json()["room"]["id"]
    payment_id = second_room.json()["payments"][0]["id"]

    mark_paid = client.patch(
        f"/payments/{payment_id}",
        headers=headers,
        json={"status": "PAID"},
    )
    assert mark_paid.status_code == 200, mark_paid.text

    blocked_delete = client.delete(f"/rooms/{room_id}", headers=headers)
    assert blocked_delete.status_code == 409
    assert blocked_delete.json()["detail"] == "room_has_paid_payments"


def test_schedule_update_clamps_payment_day_for_short_months(app_ctx):
    owner = register_and_verify(app_ctx, email="schedule@example.com", code="666666")
    client = app_ctx["client"]
    headers = auth_headers(owner["access_token"])

    created = client.post(
        "/rooms",
        headers=headers,
        json=room_payload("schedule@example.com", payment_day=31, cycle_length=2),
    )
    assert created.status_code == 200, created.text
    room_id = created.json()["room"]["id"]
    receiver_id = created.json()["members"][1]["user_id"]

    update_response = client.patch(
        f"/rooms/{room_id}/schedule",
        headers=headers,
        json={"items": [{"month": "2024-02-01", "receiver_id": receiver_id}]},
    )
    assert update_response.status_code == 200, update_response.text

    payments_response = client.get(f"/rooms/{room_id}/payments", headers=headers)
    assert payments_response.status_code == 200, payments_response.text
    february_rows = [
        row for row in payments_response.json()
        if row["month"].startswith("2024-02")
    ]

    assert february_rows
    assert all(row["month"] == "2024-02-29" for row in february_rows)
    assert all(row["receiver_id"] == receiver_id for row in february_rows)


def test_schedule_update_rejects_receiver_outside_room(app_ctx):
    owner = register_and_verify(app_ctx, email="schedule-invalid@example.com", code="777777")
    client = app_ctx["client"]
    headers = auth_headers(owner["access_token"])

    created = client.post(
        "/rooms",
        headers=headers,
        json=room_payload("schedule-invalid@example.com", payment_day=28, cycle_length=1),
    )
    assert created.status_code == 200, created.text
    room_id = created.json()["room"]["id"]

    response = client.patch(
        f"/rooms/{room_id}/schedule",
        headers=headers,
        json={"items": [{"month": "2024-03-01", "receiver_id": "missing-user"}]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "receiver_invalid"
