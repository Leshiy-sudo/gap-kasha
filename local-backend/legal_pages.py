import os
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from account_service import delete_user_account
from db import db_session
from security import verify_password

APP_NAME = os.getenv("APP_PUBLIC_NAME", "GapKassa")
LEGAL_ENTITY = os.getenv("LEGAL_ENTITY_NAME", "GapKassa")
SUPPORT_EMAIL = os.getenv("PUBLIC_SUPPORT_EMAIL", "support@gapkassa.local")
PRIVACY_EFFECTIVE_DATE = os.getenv("PRIVACY_EFFECTIVE_DATE", "2026-04-16")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter(include_in_schema=False)


class PublicDeleteAccountRequest(BaseModel):
    email: str
    password: str


def _normalize_email(value: str) -> str:
    email = (value or "").strip().lower()
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="invalid_email")
    return email


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
        <li>Account data: email, password hash, name, surname, patronymic, phone number.</li>
        <li>App usage data necessary to operate the service: rooms, participants, payment schedule data, payment confirmations.</li>
        <li>Security and service logs: login attempts, OTP requests, refresh sessions, audit events.</li>
        <li>Push notification data, when Firebase Cloud Messaging is enabled: device registration token.</li>
      </ul>

      <h2>Why We Use Data</h2>
      <ul>
        <li>To create and maintain user accounts.</li>
        <li>To verify email ownership and protect registration/login flows.</li>
        <li>To operate rooms, payment schedules, and participant flows.</li>
        <li>To secure the service, investigate abuse, and maintain auditability.</li>
        <li>To send service notifications and product messages when enabled.</li>
      </ul>

      <h2>How We Share Data</h2>
      <p>We do not sell personal data. Data may be processed by infrastructure and communication providers strictly to deliver service functionality such as email OTP or push notifications.</p>

      <h2>Retention</h2>
      <p>We retain data only as long as required to operate the service and protect it from abuse. When an account deletion request is completed, the account, authentication data, related memberships, related sessions, and associated personal records are removed. Rooms created by the deleting user may also be removed as part of this process.</p>

      <h2>Security</h2>
      <p>We use HTTPS in production, password hashing, token-based authentication, and audit logging to protect user data and service integrity.</p>

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
      <label>Email
        <input id="email" type="email" autocomplete="username" />
      </label>
      <label>Password
        <input id="password" type="password" autocomplete="current-password" />
      </label>
      <button onclick="submitDeletion()">Delete account</button>
      <div class="status" id="status"></div>
    </div>
  </div>
  <script>
    async function submitDeletion() {{
      const status = document.getElementById('status');
      status.className = 'status';
      status.textContent = 'Processing...';
      try {{
        const response = await fetch('/legal/delete-account/request', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            email: document.getElementById('email').value,
            password: document.getElementById('password').value
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
    email = _normalize_email(payload.email)
    password = (payload.password or "").strip()
    if not password:
        raise HTTPException(status_code=400, detail="password_required")

    with db_session() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or not user["password_hash"]:
            raise HTTPException(status_code=404, detail="account_not_found")
        if not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="invalid_credentials")
        delete_user_account(conn, user, request=request, source="public_web")

    return {"message": "account_deleted"}
