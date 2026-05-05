# GapKassa VPS Deploy

## Что это даёт

- reproducible deploy backend на один VPS через Docker Compose;
- постоянное хранение SQLite базы и outbox в volumes;
- backend слушает только `127.0.0.1:8080`, чтобы наружу его отдавал nginx/Caddy;
- подходит для текущей архитектуры с одним инстансом и SQLite.

Файл запуска:

- `/Users/user/Documents/автоматизация/gap-kassa/docker-compose.prod.yml`

## Что должно быть на VPS

- Ubuntu/Debian VPS с установленными `git`, `docker`, `docker compose`;
- DNS/реверс-прокси для домена API;
- SSH доступ к серверу;
- один backend-инстанс.

## Первый запуск

```bash
git clone git@github.com:Leshiy-sudo/gap-kasha.git
cd gap-kasha
cp local-backend/.env.example local-backend/.env
```

Заполнить в `local-backend/.env` как минимум:

- `APP_ENV=production`
- `JWT_SECRET`
- `JWT_ISSUER`
- `GOOGLE_WEB_CLIENT_ID`
- `GOOGLE_AUTH_ALLOW_MOCK=false`
- `CORS_ORIGINS`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SMTP_USER`
- `SMTP_PASS`
- `SMTP_FROM`
- `CLIENT_ERROR_REPORT_EMAILS=talgat19940914@gmail.com`

Потом:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:8080/health
```

## Обновление на проде

```bash
cd gap-kasha
git pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:8080/health
```

Полезные команды:

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml exec backend python -m pytest tests -q
docker compose -f docker-compose.prod.yml restart backend
```

## Nginx пример

Если backend должен жить за `https://api.example.com`, прокси должен вести на `127.0.0.1:8080`.

Минимальная идея:

```nginx
server {
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Что важно для Android release

После того как появится реальный production URL API:

```bash
GAPKASSA_RELEASE_API_URL=https://api.example.com/ ./gradlew assembleRelease
```

Сейчас release build по умолчанию всё ещё использует заглушку:

- `/Users/user/Documents/автоматизация/gap-kassa/app/build.gradle.kts`

## Ограничения

- SQLite подходит только для одного VPS/инстанса;
- для масштабирования нужен переход на Postgres;
- Google login в production требует рабочий публичный API URL и корректный `GOOGLE_WEB_CLIENT_ID`.
