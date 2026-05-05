import os
import secrets
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from autotest_admin import SUITE_ORDER, SUITES, load_status, start_background_run, stop_background_run

from runtime_config import (
    DEFAULT_CONTENT,
    DEFAULT_SETTINGS,
    build_public_config,
    collect_admin_overview,
    list_content,
    list_settings,
    upsert_content,
    upsert_settings,
)

router = APIRouter(include_in_schema=False)
security = HTTPBasic()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
APP_ENV = os.getenv("APP_ENV", "local")

if APP_ENV != "local" and ADMIN_PASSWORD == "admin":
    raise RuntimeError("ADMIN_PASSWORD must be set for non-local environments")


class AdminSettingsPayload(BaseModel):
    settings: Dict[str, Any]


class AdminContentPayload(BaseModel):
    locales: Dict[str, Dict[str, Dict[str, Any]]]


class AdminTestRunPayload(BaseModel):
    suites: list[str] = Field(default_factory=list)


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    username_ok = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    password_ok = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="admin_auth_failed",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


ADMIN_PAGE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GapKassa Admin</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f6fb;
      --card: #ffffff;
      --line: #d9e1ef;
      --text: #142033;
      --muted: #61708a;
      --accent: #0d6efd;
      --danger: #d64045;
      --ok: #17895d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: linear-gradient(180deg, #eef4ff 0%, var(--bg) 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .wrap {
      max-width: 1360px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 20px;
    }
    .hero h1 {
      margin: 0 0 8px;
      font-size: 32px;
      line-height: 1.1;
    }
    .hero p {
      margin: 0;
      color: var(--muted);
      max-width: 760px;
    }
    .toolbar {
      display: flex;
      gap: 12px;
      align-items: center;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 20px;
    }
    .card, .panel {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 10px 24px rgba(20, 32, 51, 0.06);
    }
    .card {
      padding: 16px;
    }
    .card small {
      display: block;
      color: var(--muted);
      margin-bottom: 10px;
    }
    .card strong {
      font-size: 28px;
      line-height: 1;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
      gap: 16px;
      margin-bottom: 16px;
    }
    .panel {
      padding: 18px;
    }
    .panel h2 {
      margin: 0 0 8px;
      font-size: 20px;
    }
    .panel p.note {
      margin: 0 0 16px;
      color: var(--muted);
      font-size: 14px;
    }
    .fields {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .locale-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 13px;
      color: var(--muted);
    }
    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 11px 12px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    textarea { min-height: 88px; resize: vertical; }
    fieldset {
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
    }
    legend {
      padding: 0 6px;
      color: var(--text);
      font-weight: 600;
    }
    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 14px;
    }
    button {
      border: 0;
      border-radius: 12px;
      padding: 11px 14px;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }
    button.primary {
      background: var(--accent);
      color: white;
    }
    button.secondary {
      background: #edf3ff;
      color: var(--accent);
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border-radius: 999px;
      background: #edf3ff;
      color: var(--accent);
      font-weight: 600;
      font-size: 13px;
    }
    .warn { color: var(--danger); }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 10px 0;
      border-bottom: 1px solid #edf1f7;
      text-align: left;
      font-size: 14px;
    }
    th { color: var(--muted); font-weight: 600; }
    .status {
      margin-top: 10px;
      min-height: 20px;
      font-size: 14px;
      color: var(--ok);
    }
    .status.error { color: var(--danger); }
    .test-panel {
      margin-bottom: 16px;
    }
    .test-toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 14px;
    }
    .test-summary {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    .mini-card {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: #fbfcff;
    }
    .mini-card small {
      display: block;
      color: var(--muted);
      margin-bottom: 6px;
    }
    .mini-card strong {
      font-size: 20px;
    }
    .test-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .test-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: #fff;
    }
    .test-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
    }
    .test-card p {
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 14px;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 78px;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .badge-idle, .badge-queued {
      background: #eef3fb;
      color: #51627d;
    }
    .badge-running {
      background: #edf3ff;
      color: var(--accent);
    }
    .badge-passed {
      background: #e8faf3;
      color: var(--ok);
    }
    .badge-failed, .badge-cancelled {
      background: #ffeff0;
      color: var(--danger);
    }
    .compact-actions {
      display: flex;
      gap: 8px;
      margin: 10px 0;
    }
    button.tiny {
      padding: 9px 11px;
      border-radius: 10px;
      font-size: 13px;
    }
    .test-meta {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 8px;
    }
    pre.logbox {
      margin: 0;
      padding: 12px;
      border-radius: 12px;
      background: #0f1727;
      color: #dce8ff;
      font-size: 12px;
      line-height: 1.5;
      white-space: pre-wrap;
      max-height: 180px;
      overflow: auto;
    }
    .detail-list {
      margin: 8px 0 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 13px;
    }
    @media (max-width: 1100px) {
      .grid, .layout, .fields, .locale-grid, .test-grid, .test-summary { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <h1>GapKassa Admin</h1>
        <p>Панель управления лимитами OTP/нагрузки, рекламным блоком, динамическими текстами и общим состоянием backend.</p>
      </div>
      <div class="toolbar">
        <button class="secondary" onclick="loadAll()">Обновить</button>
        <span class="pill" id="generatedAt">Загрузка…</span>
      </div>
    </div>

    <div class="grid" id="statsGrid"></div>

    <section class="panel test-panel">
      <h2>Автотесты</h2>
      <p class="note">Короткая сводка по backend/API, Android quality и UI smoke. Кнопки ниже запускают локальные прогоны прямо с этого стенда перед push.</p>
      <div class="test-toolbar">
        <button class="secondary" onclick="runSuites(['backend_api'])">Backend/API</button>
        <button class="secondary" onclick="runSuites(['android_quality'])">Android unit + lint</button>
        <button class="secondary" onclick="runSuites(['android_ui'])">UI smoke</button>
        <button class="primary" onclick="runSuites(['all'])">Прогнать все</button>
        <button class="secondary" onclick="stopTests()">Остановить</button>
      </div>
      <div class="test-summary" id="testSummary"></div>
      <div class="test-grid" id="testGrid"></div>
      <div class="status" id="testsStatus"></div>
    </section>

    <div class="layout">
      <section class="panel">
        <h2>Лимиты и нагрузка</h2>
        <p class="note">Эти значения применяются backend сразу: OTP, логины, длины полей, лимиты участников и мягкие пороги хранения.</p>
        <div class="fields">
          <label>OTP TTL, минут<input id="otp_ttl_min" type="number" min="1" /></label>
          <label>OTP cooldown, секунд<input id="otp_cooldown_sec" type="number" min="0" /></label>
          <label>OTP max attempts<input id="otp_max_attempts" type="number" min="1" /></label>
          <label>Daily OTP cap<input id="max_daily_otp_requests" type="number" min="1" /></label>
          <label>Login max attempts<input id="login_max_attempts" type="number" min="1" /></label>
          <label>Login lockout, минут<input id="login_lockout_min" type="number" min="1" /></label>
          <label>Min text length cap<input id="max_text_length" type="number" min="1" /></label>
          <label>Description cap<input id="max_description_length" type="number" min="1" /></label>
          <label>Password min<input id="password_min_len" type="number" min="1" /></label>
          <label>Password max<input id="password_max_len" type="number" min="1" /></label>
          <label>Min members per room<input id="min_members_per_room" type="number" min="1" /></label>
          <label>Max members per room<input id="max_members_per_room" type="number" min="1" /></label>
          <label>DB soft limit, MB<input id="db_soft_limit_mb" type="number" min="1" /></label>
          <label>Outbox soft limit, MB<input id="outbox_soft_limit_mb" type="number" min="1" /></label>
          <label>Audit retention, days<input id="audit_retention_days" type="number" min="1" /></label>
          <label>Ad target URL<input id="ad_target_url" type="url" placeholder="https://..." /></label>
          <label>
            Реклама включена
            <select id="ad_enabled">
              <option value="1">Да</option>
              <option value="0">Нет</option>
            </select>
          </label>
        </div>
        <div class="actions">
          <button class="primary" onclick="saveSettings()">Сохранить лимиты</button>
        </div>
        <div class="status" id="settingsStatus"></div>
      </section>

      <section class="panel">
        <h2>Последние события</h2>
        <p class="note">Свежий audit trail по backend — удобно для проверки действий и нагрузки.</p>
        <table>
          <thead>
            <tr><th>Время</th><th>Действие</th><th>Сущность</th><th>Кто</th></tr>
          </thead>
          <tbody id="auditRows"></tbody>
        </table>
      </section>
    </div>

    <section class="panel">
      <h2>Реклама и тексты</h2>
      <p class="note">Управляем рекламным блоком и теми динамическими текстами, которые приложение уже умеет подхватывать с backend.</p>
      <div class="locale-grid">
        <fieldset>
          <legend>Русский</legend>
          <label>Badge<input id="ru_ad_badge" /></label>
          <label>Заголовок рекламы<input id="ru_ad_title" /></label>
          <label>Текст рекламы<textarea id="ru_ad_body"></textarea></label>
          <label>CTA<input id="ru_ad_cta" /></label>
          <label>Текст регистрации OTP<textarea id="ru_text_helper_register_otp"></textarea></label>
          <label>Подсказка верификации<textarea id="ru_text_verification_hint"></textarea></label>
          <label>Сообщение после отправки кода<textarea id="ru_text_message_verification_sent"></textarea></label>
        </fieldset>
        <fieldset>
          <legend>O‘zbekcha</legend>
          <label>Badge<input id="uz_ad_badge" /></label>
          <label>Reklama sarlavhasi<input id="uz_ad_title" /></label>
          <label>Reklama matni<textarea id="uz_ad_body"></textarea></label>
          <label>CTA<input id="uz_ad_cta" /></label>
          <label>OTP ro‘yxatdan o‘tish matni<textarea id="uz_text_helper_register_otp"></textarea></label>
          <label>Tasdiqlash yordamchi matni<textarea id="uz_text_verification_hint"></textarea></label>
          <label>Kod yuborilgandan keyingi xabar<textarea id="uz_text_message_verification_sent"></textarea></label>
        </fieldset>
      </div>
      <div class="actions">
        <button class="primary" onclick="saveContent()">Сохранить рекламу и тексты</button>
      </div>
      <div class="status" id="contentStatus"></div>
    </section>
  </div>

  <script>
    function setStatus(id, message, isError = false) {
      const node = document.getElementById(id);
      node.textContent = message;
      node.className = isError ? 'status error' : 'status';
    }

    function normalizeErrorMessage(message) {
      const value = String(message || '').trim();
      const known = {
        autotests_already_running: 'Автотесты уже запущены',
        admin_auth_failed: 'Ошибка авторизации администратора'
      };
      if (!value) return 'Неизвестная ошибка';
      return known[value] || value;
    }

    async function requestJson(url, options = {}) {
      const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options
      });
      if (!response.ok) {
        const contentType = response.headers.get('content-type') || '';
        let message = '';
        if (contentType.includes('application/json')) {
          const payload = await response.json().catch(() => null);
          message = payload?.detail || payload?.message || '';
        }
        if (!message) {
          message = await response.text();
        }
        throw new Error(normalizeErrorMessage(message || response.statusText));
      }
      return response.json();
    }

    function escapeHtml(value) {
      return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function renderStats(stats) {
      const cards = [
        ['Пользователи', `${stats.users_total}`],
        ['Комнаты', `${stats.rooms_total}`],
        ['OTP за 24ч', `${stats.otp_last_24h}`],
        ['Ошибки логина за 24ч', `${stats.failed_logins_last_24h}`],
        ['DB, MB', `${stats.db_size_mb} / ${stats.db_soft_limit_mb}`],
        ['Outbox, MB', `${stats.outbox_size_mb} / ${stats.outbox_soft_limit_mb}`],
        ['Оплачено', `${stats.payments_paid} / ${stats.payments_total}`],
        ['Audit rows', `${stats.audit_rows}`],
      ];
      document.getElementById('statsGrid').innerHTML = cards.map(([label, value]) => `
        <div class="card">
          <small>${label}</small>
          <strong>${value}</strong>
        </div>
      `).join('');
      document.getElementById('generatedAt').textContent = `Обновлено: ${stats.generated_at}`;
    }

    function fillSettings(settings) {
      Object.entries(settings).forEach(([key, value]) => {
        const element = document.getElementById(key);
        if (element) element.value = value;
      });
    }

    function fillContent(locales) {
      ['ru', 'uz'].forEach((locale) => {
        const data = locales[locale] || { ad: {}, text: {} };
        ['badge', 'title', 'body', 'cta'].forEach((key) => {
          document.getElementById(`${locale}_ad_${key}`).value = data.ad?.[key] || '';
        });
        ['helper_register_otp', 'verification_hint', 'message_verification_sent'].forEach((key) => {
          document.getElementById(`${locale}_text_${key}`).value = data.text?.[key] || '';
        });
      });
    }

    function renderAudit(rows) {
      const tbody = document.getElementById('auditRows');
      tbody.innerHTML = rows.map((row) => `
        <tr>
          <td>${row.created_at || '—'}</td>
          <td>${row.action || '—'}</td>
          <td>${row.entity_type || '—'}</td>
          <td>${row.actor_id || 'system'}</td>
        </tr>
      `).join('');
    }

    function statusLabel(status) {
      const labels = {
        idle: 'idle',
        queued: 'queue',
        running: 'running',
        passed: 'passed',
        failed: 'failed',
        cancelled: 'stopped'
      };
      return labels[status] || status || 'idle';
    }

    function renderTestSummary(data) {
      const summary = data.summary || {};
      const suites = data.suites || {};
      const runningName = data.current_suite && suites[data.current_suite]
        ? suites[data.current_suite].label
        : '—';
      const cards = [
        ['Сводка', summary.headline || 'Нет данных'],
        ['Сейчас идет', data.is_running ? runningName : 'Ничего'],
        ['Green', `${summary.passed || 0}/${summary.total || 0}`],
        ['Failures', `${summary.failed || 0}`],
        ['Queued/Run', `${(summary.queued || 0) + (summary.running || 0)}`],
      ];
      document.getElementById('testSummary').innerHTML = cards.map(([label, value]) => `
        <div class="mini-card">
          <small>${label}</small>
          <strong>${value}</strong>
        </div>
      `).join('');
    }

    function renderTestGrid(data) {
      const suites = data.suites || {};
      const order = %TEST_SUITE_ORDER%;
      document.getElementById('testGrid').innerHTML = order.map((key) => {
        const item = suites[key] || {};
        const details = Array.isArray(item.details) && item.details.length
          ? `<ul class="detail-list">${item.details.map((detail) => `<li>${escapeHtml(detail.label || detail.class || 'Шаг')} — ${escapeHtml(detail.status || '—')}${detail.duration_sec ? ` (${detail.duration_sec}s)` : ''}</li>`).join('')}</ul>`
          : '';
        return `
          <div class="test-card">
            <div class="test-head">
              <strong>${escapeHtml(item.label || key)}</strong>
              <span class="badge badge-${escapeHtml(item.status || 'idle')}">${escapeHtml(statusLabel(item.status))}</span>
            </div>
            <p>${escapeHtml(item.description || '')}</p>
            <div class="test-meta">${escapeHtml(item.summary || 'Нет данных')}</div>
            <div class="test-meta">Старт: ${escapeHtml(item.last_started_at || '—')} · Финиш: ${escapeHtml(item.last_finished_at || '—')} · Длительность: ${item.duration_sec ?? '—'}s</div>
            <div class="compact-actions">
              <button class="secondary tiny" onclick="runSuites(['${key}'])">Запустить</button>
            </div>
            ${details}
            <pre class="logbox">${escapeHtml(item.output_tail || 'Лог появится после первого прогона.')}</pre>
          </div>
        `;
      }).join('');
    }

    async function loadTests() {
      try {
        const data = await requestJson('/admin/api/tests');
        renderTestSummary(data);
        renderTestGrid(data);
      } catch (error) {
        setStatus('testsStatus', `Не удалось загрузить сводку тестов: ${error.message}`, true);
      }
    }

    async function loadAll() {
      try {
        const [overview, settings, content] = await Promise.all([
          requestJson('/admin/api/overview'),
          requestJson('/admin/api/settings'),
          requestJson('/admin/api/content')
        ]);
        renderStats(overview.stats);
        renderAudit(overview.recent_audit || []);
        fillSettings(settings.settings || settings);
        fillContent(content.locales || content);
        await loadTests();
      } catch (error) {
        setStatus('settingsStatus', `Ошибка загрузки: ${error.message}`, true);
      }
    }

    async function saveSettings() {
      const keys = %SETTINGS_KEYS%;
      const payload = { settings: Object.fromEntries(keys.map((key) => [key, document.getElementById(key).value])) };
      try {
        await requestJson('/admin/api/settings', {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        setStatus('settingsStatus', 'Лимиты сохранены');
        await loadAll();
      } catch (error) {
        setStatus('settingsStatus', `Не удалось сохранить: ${error.message}`, true);
      }
    }

    async function saveContent() {
      const locales = {};
      ['ru', 'uz'].forEach((locale) => {
        locales[locale] = {
          ad: {
            badge: document.getElementById(`${locale}_ad_badge`).value,
            title: document.getElementById(`${locale}_ad_title`).value,
            body: document.getElementById(`${locale}_ad_body`).value,
            cta: document.getElementById(`${locale}_ad_cta`).value
          },
          text: {
            helper_register_otp: document.getElementById(`${locale}_text_helper_register_otp`).value,
            verification_hint: document.getElementById(`${locale}_text_verification_hint`).value,
            message_verification_sent: document.getElementById(`${locale}_text_message_verification_sent`).value
          }
        };
      });
      try {
        await requestJson('/admin/api/content', {
          method: 'PUT',
          body: JSON.stringify({ locales })
        });
        setStatus('contentStatus', 'Реклама и тексты сохранены');
      } catch (error) {
        setStatus('contentStatus', `Не удалось сохранить: ${error.message}`, true);
      }
    }

    async function runSuites(suites) {
      try {
        const data = await requestJson('/admin/api/tests/run', {
          method: 'POST',
          body: JSON.stringify({ suites })
        });
        setStatus('testsStatus', data.message || 'Прогон запущен');
        renderTestSummary(data.status || data);
        renderTestGrid(data.status || data);
        window.clearInterval(window.__gapTestsPoll);
        window.__gapTestsPoll = window.setInterval(loadTests, 4000);
      } catch (error) {
        setStatus('testsStatus', `Не удалось запустить: ${error.message}`, true);
      }
    }

    async function stopTests() {
      try {
        const data = await requestJson('/admin/api/tests/stop', { method: 'POST' });
        setStatus('testsStatus', data.message || 'Прогон остановлен');
        renderTestSummary(data.status || data);
        renderTestGrid(data.status || data);
      } catch (error) {
        setStatus('testsStatus', `Не удалось остановить: ${error.message}`, true);
      }
    }

    loadAll();
    window.__gapTestsPoll = window.setInterval(loadTests, 15000);
  </script>
</body>
</html>
""".replace("%SETTINGS_KEYS%", str(list(DEFAULT_SETTINGS.keys()))).replace("%TEST_SUITE_ORDER%", str(SUITE_ORDER))


@router.get("/admin", response_class=HTMLResponse)
def admin_page(_: str = Depends(require_admin)):
    return HTMLResponse(ADMIN_PAGE)


@router.get("/admin/api/overview")
def admin_overview(_: str = Depends(require_admin)):
    return collect_admin_overview()


@router.get("/admin/api/settings")
def admin_settings(_: str = Depends(require_admin)):
    return {"settings": list_settings()}


@router.put("/admin/api/settings")
def update_admin_settings(payload: AdminSettingsPayload, admin: str = Depends(require_admin)):
    upsert_settings(payload.settings, actor_id=admin)
    return {"message": "settings_saved", "settings": list_settings()}


@router.get("/admin/api/content")
def admin_content(_: str = Depends(require_admin)):
    return {"locales": list_content()}


@router.put("/admin/api/content")
def update_admin_content(payload: AdminContentPayload, admin: str = Depends(require_admin)):
    upsert_content(payload.locales, actor_id=admin)
    return {"message": "content_saved", "locales": list_content()}


@router.get("/admin/api/tests")
def admin_test_status(_: str = Depends(require_admin)):
    return load_status()


@router.post("/admin/api/tests/run")
def run_admin_tests(payload: AdminTestRunPayload, admin: str = Depends(require_admin)):
    try:
        status_data = start_background_run(payload.suites, actor_id=admin)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"message": "autotests_started", "status": status_data}


@router.post("/admin/api/tests/stop")
def stop_admin_tests(_: str = Depends(require_admin)):
    status_data = stop_background_run()
    return {"message": "autotests_stopped", "status": status_data}


@router.get("/app/config")
def public_app_config(lang: str = "ru"):
    return build_public_config(lang)
