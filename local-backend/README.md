# GapKassa Local Backend

Локальный backend для OTP + хранения данных + аудит‑лога. Хранит данные в SQLite и пишет письма в `outbox/`.
При наличии SMTP‑настроек будет отправлять реальные письма.

## Быстрый старт

```bash
cd /Users/user/Documents/автоматизация/gap-kassa/local-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# запуск
APP_ENV=local \
JWT_SECRET=dev-secret-change-me \
OTP_PEPPER=dev-otp-pepper \
uvicorn main:app --reload --port 8080
```

Проверка:
```bash
curl http://localhost:8080/health
```

## Где искать код из письма

Каждый OTP сохраняется в `outbox/` как текстовый файл.

## SMTP (опционально)

Создайте файл `.env` рядом с `main.py`:

```bash
SMTP_HOST=smtp.yandex.com
SMTP_PORT=465
SMTP_USER=example@yandex.com
SMTP_PASS=app_password
SMTP_FROM=GapKassa <example@yandex.com>
SMTP_TLS=false
```

Если SMTP не задан, письма будут только в `outbox/`.

## Основные эндпоинты

- `POST /auth/request-otp` { email }
- `POST /auth/verify-otp` { email, code }
- `POST /auth/refresh` { refresh_token }
- `GET /me`
- `PATCH /me` { name?, phone? }
- `POST /rooms` { name, description? }
- `PATCH /rooms/{id}` { name?, description? }
- `GET /rooms`

## Где лежит база

`local-backend/data/app.db`
