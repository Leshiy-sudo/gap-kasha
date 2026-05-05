# GapKassa Backend

Backend для Google auth + хранения данных + аудит‑лога. По умолчанию хранит данные в SQLite.
Legacy email OTP контур сохранён для совместимости и внутренних сценариев, но основная мобильная авторизация теперь идёт через `POST /auth/google`.

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
GOOGLE_AUTH_ALLOW_MOCK=true \
uvicorn main:app --reload --port 8080
```

Проверка:
```bash
curl http://localhost:8080/health
```

## Google auth

Основной мобильный вход:

- `POST /auth/google` { `id_token`, `nonce?` }

Production-путь:

- укажите `GOOGLE_WEB_CLIENT_ID` для backend;
- Android-клиент получает Google ID token через Credential Manager;
- backend валидирует токен и выпускает собственные `access_token` / `refresh_token`.

Локальный/dev/mock путь:

- при `APP_ENV=local` mock Google auth включён автоматически;
- можно отправлять `id_token`, начинающийся с `mock-google:`.

Пример mock payload:

```json
{
  "id_token": "mock-google:{\"email\":\"uiqa@example.com\",\"sub\":\"android-ui-test\",\"name\":\"Uiqa\",\"email_verified\":true}"
}
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

Для email-репортов клиентских падений задайте:

```bash
CLIENT_ERROR_REPORT_EMAILS=talgat19940914@gmail.com
CLIENT_ERROR_STACKTRACE_MAX_LEN=12000
```

## Основные эндпоинты

- `POST /auth/google` { id_token, nonce? }
- `POST /client-errors` { kind, report_id, message, ... }
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

## Docker / облако

Есть базовый `Dockerfile` и `.env.example`.

Локальный запуск контейнера:

```bash
cd /Users/user/Documents/автоматизация/gap-kassa/local-backend
cp .env.example .env
docker build -t gapkassa-backend .
docker run --env-file .env -p 8080:8080 -v "$PWD/data:/data" gapkassa-backend
```

Важно:

- Текущая база по умолчанию — SQLite.
- Для быстрого облачного MVP backend можно запускать на одном VM/VPS с постоянным диском и `DB_PATH=/data/app.db`.
- Для Cloud Run/горизонтального масштабирования SQLite не подходит: перед таким деплоем нужно мигрировать backend на управляемую БД вроде Postgres / Cloud SQL.

## Админ‑панель

После запуска backend доступна web‑панель:

- `GET /admin`
- Basic Auth через `ADMIN_USERNAME` и `ADMIN_PASSWORD`

Что уже можно делать из панели:

- менять лимиты OTP / логина / длины полей / лимиты участников;
- смотреть размеры базы и outbox как мягкие пороги по памяти/нагрузке;
- включать/выключать рекламный блок и менять ссылку;
- редактировать тексты рекламы и динамические тексты приложения для `ru` и `uz`.

Публичная конфигурация для приложения:

- `GET /app/config?lang=ru`
- `GET /app/config?lang=uz`

## Legal URL

Публичные страницы для Google Play и пользователей:

- `GET /legal/privacy-policy`
- `GET /legal/delete-account`
- `POST /legal/delete-account/request`

Удаление аккаунта из приложения:

- `DELETE /me`
