from typing import Optional
from uuid import uuid4
import json

from fastapi import Request

from db import now_iso


def log_event(
    conn,
    actor_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: Optional[str],
    before,
    after,
    request: Optional[Request] = None,
):
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
            request.client.host if request and request.client else None,
            request.headers.get("user-agent") if request else None,
            now_iso(),
        ),
    )


def _ensure_room_integrity_after_member_delete(conn, room_id: str):
    remaining_count = conn.execute(
        "SELECT COUNT(*) AS count FROM room_members WHERE room_id = ?",
        (room_id,),
    ).fetchone()["count"]

    if remaining_count <= 0:
        conn.execute("DELETE FROM payments WHERE room_id = ?", (room_id,))
        conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        return

    admin_exists = conn.execute(
        "SELECT 1 FROM room_members WHERE room_id = ? AND role = 'ADMIN' LIMIT 1",
        (room_id,),
    ).fetchone()
    if admin_exists is None:
        fallback = conn.execute(
            "SELECT user_id FROM room_members WHERE room_id = ? ORDER BY order_index ASC LIMIT 1",
            (room_id,),
        ).fetchone()
        if fallback is not None:
            conn.execute(
                "UPDATE room_members SET role = 'ADMIN', updated_at = ? WHERE room_id = ? AND user_id = ?",
                (now_iso(), room_id, fallback["user_id"]),
            )

    conn.execute(
        "UPDATE rooms SET member_count = ?, updated_at = ? WHERE id = ?",
        (remaining_count, now_iso(), room_id),
    )


def delete_user_account(
    conn,
    user_row,
    request: Optional[Request] = None,
    source: str = "self_service",
):
    user = dict(user_row)
    user_id = user["id"]
    email = user["email"]

    created_rooms = [
        row["id"]
        for row in conn.execute(
            "SELECT id FROM rooms WHERE created_by = ?",
            (user_id,),
        ).fetchall()
    ]

    member_rooms = [
        row["room_id"]
        for row in conn.execute(
            "SELECT room_id FROM room_members WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        if row["room_id"] not in created_rooms
    ]

    for room_id in created_rooms:
        conn.execute("DELETE FROM payments WHERE room_id = ?", (room_id,))
        conn.execute("DELETE FROM room_members WHERE room_id = ?", (room_id,))
        conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))

    if member_rooms:
        for room_id in member_rooms:
            conn.execute(
                "DELETE FROM payments WHERE room_id = ? AND (payer_id = ? OR receiver_id = ?)",
                (room_id, user_id, user_id),
            )
            conn.execute(
                "DELETE FROM room_members WHERE room_id = ? AND user_id = ?",
                (room_id, user_id),
            )
            _ensure_room_integrity_after_member_delete(conn, room_id)

    conn.execute("DELETE FROM refresh_tokens WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM device_tokens WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM otp_codes WHERE email = ?", (email,))
    conn.execute("DELETE FROM login_attempts WHERE email = ?", (email,))
    conn.execute("DELETE FROM email_outbox WHERE recipient = ?", (email,))
    conn.execute(
        "DELETE FROM audit_log WHERE actor_id = ? OR (entity_type = 'user' AND entity_id = ?)",
        (user_id, user_id),
    )
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    log_event(
        conn=conn,
        actor_id=None,
        action="account.delete",
        entity_type="account",
        entity_id=None,
        before=None,
        after={
            "source": source,
            "deleted_user_id": user_id,
            "deleted_created_rooms": len(created_rooms),
            "updated_member_rooms": len(member_rooms),
        },
        request=request,
    )
