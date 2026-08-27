import os
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from account_service import delete_user_account
from db import db_session, now_iso
from security import verify_otp as verify_otp_code

APP_NAME = os.getenv("APP_PUBLIC_NAME", "GapKassa")
LEGAL_ENTITY = os.getenv("LEGAL_ENTITY_NAME", "GapKassa")
SUPPORT_EMAIL = os.getenv("PUBLIC_SUPPORT_EMAIL", "support@gapkassa.local")
PRIVACY_EFFECTIVE_DATE = os.getenv("PRIVACY_EFFECTIVE_DATE", "2026-04-16")

PHONE_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")

router = APIRouter(include_in_schema=False)


class PublicDeleteAccountRequest(BaseModel):
    phone: str
    code: str


def _normalize_phone(value: str) -> str:
    cleaned = re.sub(r"[\s\-()]", "", (value or "").strip())
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned.lstrip("+")
    if not PHONE_REGEX.match(cleaned):
        raise HTTPException(status_code=400, detail="invalid_phone")
    return cleaned


PRIVACY_POLICY_HTML = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{APP_NAME} Privacy Policy</title>
  <style>
    body {{
      margin: 0;
      background: #f5f7fb;
      color: #172235;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .wrap {{
      max-width: 900px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .card {{
      background: white;
      border: 1px solid #dde5f0;
      border-radius: 20px;
      padding: 28px;
      box-shadow: 0 18px 40px rgba(23, 34, 53, 0.08);
    }}
    h1, h2 {{ margin-top: 0; }}
    h1 {{ font-size: 32px; margin-bottom: 8px; }}
    h2 {{ margin-top: 28px; font-size: 20px; }}
    p, li {{ line-height: 1.65; color: #31415f; }}
    ul {{ padding-left: 20px; }}
    .meta {{ color: #66748f; margin-bottom: 22px; }}
    a {{ color: #0d6efd; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Privacy Policy</h1>
      <p class="meta">Effective date: {PRIVACY_EFFECTIVE_DATE}</p>
      <p>{APP_NAME} is operated by {LEGAL_ENTITY}. This policy explains what data we collect, why we use it, how we protect it, and how users can request deletion.</p>

      <h2>What We Collect</h2>
      <ul>
        <li>Account data: phone number, name, surname, patronymic.</li>
        <li>App usage data necessary to operate the service: rooms, participants, payment schedule data, payment confirmations.</li>
        <li>Security and service logs: login attempts, OTP requests, refresh sessions, audit events.</li>
        <li>Push notification data, when Firebase Cloud Messaging is enabled: device registration token.</li>
      </ul>

      <h2>Why We Use Data</h2>
      <ul>
        <li>To create and maintain user accounts.</li>
        <li>To verify phone number ownership and protect login flows via a one-time code delivered through Telegram.</li>
        <li>To operate rooms, payment schedules, and participant flows.</li>
        <li>To secure the service, investigate abuse, and maintain auditability.</li>
        <li>To send service notifications and product messages when enabled.</li>
      </ul>

      <h2>How We Share Data</h2>
      <p>We do not sell personal data. Data may be processed by infrastructure and communication providers strictly to deliver service functionality, such as Telegram Gateway for one-time login codes or push notifications.</p>

      <h2>Retention</h2>
      <p>We retain data only as long as required to operate the service and protect it from abuse. When an account deletion request is completed, the account, authentication data, related memberships, related sessions, and associated personal records are removed. Rooms created by the deleting user may also be removed as part of this process.</p>

      <h2>Security</h2>
      <p>We use HTTPS in production, one-time codes instead of stored passwords, token-based authentication, and audit logging to protect user data and service integrity.</p>

      <h2>Your Rights</h2>
      <ul>
        <li>You can update your profile inside the app.</li>
        <li>You can request account deletion inside the app.</li>
        <li>You can also request deletion outside the app via the public page at <a href="/legal/delete-account">/legal/delete-account</a>.</li>
      </ul>

      <h2>Contact</h2>
      <p>For privacy questions or support requests, contact: <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p>
    </div>
  </div>
</body>
</html>"""


DELETE_ACCOUNT_HTML = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Delete {APP_NAME} Account</title>
  <style>
    body {{
      margin: 0;
      background: linear-gradient(180deg, #f2f6ff 0%, #f7f9fc 100%);
      color: #172235;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .wrap {{
      max-width: 520px;
      margin: 0 auto;
      padding: 40px 20px 48px;
    }}
    .card {{
      background: white;
      border: 1px solid #dde5f0;
      border-radius: 20px;
      padding: 24px;
      box-shadow: 0 18px 40px rgba(23, 34, 53, 0.08);
    }}
    h1 {{ margin-top: 0; font-size: 28px; }}
    p {{ color: #42506a; line-height: 1.6; }}
    label {{
      display: block;
      margin-bottom: 14px;
      color: #42506a;
      font-size: 14px;
    }}
    input {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #d7e0ee;
      border-radius: 12px;
      padding: 12px;
      margin-top: 6px;
      font: inherit;
    }}
    button {{
      width: 100%;
      border: 0;
      border-radius: 12px;
      padding: 13px 16px;
      font: inherit;
      font-weight: 700;
      color: white;
      background: #d64045;
      cursor: pointer;
    }}
    .status {{ margin-top: 14px; min-height: 24px; color: #17895d; }}
    .status.error {{ color: #d64045; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Delete Account</h1>
      <p>Use this page if you want to request deletion outside the app. This action is irreversible. Rooms created by your account may also be removed.</p>
      <label>Phone number
        <input id="phone" type="tel" autocomplete="tel" placeholder="+998901234567" />
      </label>
      <button onclick="sendCode()">Send code via Telegram</button>
      <label style="margin-top:14px">Code from Telegram
        <input id="code" type="text" autocomplete="one-time-code" />
      </label>
      <button onclick="submitDeletion()">Delete account</button>
      <div class="status" id="status"></div>
    </div>
  </div>
  <script>
    async function sendCode() {{
      const status = document.getElementById('status');
      status.className = 'status';
      status.textContent = 'Sending...';
      try {{
        const response = await fetch('/auth/phone/start', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ phone: document.getElementById('phone').value }})
        }});
        const text = await response.text();
        if (!response.ok) throw new Error(text || 'Request failed');
        status.textContent = 'Code sent via Telegram.';
      }} catch (error) {{
        status.className = 'status error';
        status.textContent = error.message;
      }}
    }}
    async function submitDeletion() {{
      const status = document.getElementById('status');
      status.className = 'status';
      status.textContent = 'Processing...';
      try {{
        const response = await fetch('/legal/delete-account/request', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            phone: document.getElementById('phone').value,
            code: document.getElementById('code').value
          }})
        }});
        const text = await response.text();
        if (!response.ok) throw new Error(text || 'Request failed');
        status.textContent = 'Account deletion completed.';
      }} catch (error) {{
        status.className = 'status error';
        status.textContent = error.message;
      }}
    }}
  </script>
</body>
</html>"""


@router.get("/legal/privacy-policy", response_class=HTMLResponse)
def privacy_policy_page():
    return HTMLResponse(PRIVACY_POLICY_HTML)


@router.get("/legal/delete-account", response_class=HTMLResponse)
def delete_account_page():
    return HTMLResponse(DELETE_ACCOUNT_HTML)


@router.post("/legal/delete-account/request")
def delete_account_public(payload: PublicDeleteAccountRequest, request: Request):
    phone = _normalize_phone(payload.phone)
    code = (payload.code or "").strip()
    if len(code) < 4:
        raise HTTPException(status_code=400, detail="invalid_code")

    with db_session() as conn:
        otp = conn.execute(
            """
            SELECT * FROM phone_otp_codes
            WHERE phone = ? AND used_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (phone,),
        ).fetchone()
        if otp is None:
            raise HTTPException(status_code=400, detail="code_not_found")
        if datetime.utcnow() > datetime.fromisoformat(otp["expires_at"]):
            raise HTTPException(status_code=400, detail="code_expired")
        if otp["attempts"] >= otp["max_attempts"]:
            raise HTTPException(status_code=429, detail="code_attempts_exceeded")
        if not verify_otp_code(code, otp["code_hash"]):
            conn.execute(
                "UPDATE phone_otp_codes SET attempts = attempts + 1 WHERE id = ?",
                (otp["id"],),
            )
            raise HTTPException(status_code=400, detail="code_invalid")
        conn.execute(
            "UPDATE phone_otp_codes SET used_at = ? WHERE id = ?",
            (now_iso(), otp["id"]),
        )

        user = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="account_not_found")
        delete_user_account(conn, user, request=request, source="public_web")

    return {"message": "account_deleted"}
