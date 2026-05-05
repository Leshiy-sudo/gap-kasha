# Google Auth Production Setup

## Что уже реализовано в проекте

- Android-клиент использует Credential Manager и кнопку `Sign in with Google`.
- Backend принимает `POST /auth/google` и проверяет Google ID token.
- Для локальной разработки есть mock-путь `mock-google:*`, который должен быть выключен в production.

Ключевые файлы:

- `/Users/user/Documents/автоматизация/gap-kassa/app/src/main/java/com/gapkassa/auth/GoogleAuthManager.kt`
- `/Users/user/Documents/автоматизация/gap-kassa/app/src/main/java/com/gapkassa/viewmodel/AuthViewModel.kt`
- `/Users/user/Documents/автоматизация/gap-kassa/local-backend/main.py`
- `/Users/user/Documents/автоматизация/gap-kassa/local-backend/google_auth.py`

## Что нужно настроить в Google Cloud / Google Auth Platform

1. Открыть проект Google Cloud для GapKassa или создать новый.
2. Включить Google Auth Platform / Sign in with Google для проекта.
3. Настроить бренд:
   - app name: `Gap Kassa`
   - support email
   - homepage URL
   - privacy policy URL
4. Если приложение будет доступно внешним пользователям, пройти brand verification.
5. Создать OAuth client типа `Web application`.
   - Именно его client ID используется как `WEB_CLIENT_ID` / `serverClientId`.
6. Если в вашей конфигурации консоль просит Android client:
   - package name: `com.gapkassa`
   - добавить SHA-1 и SHA-256 для debug/release сертификатов.

Важно:

- Backend валидирует `aud` через `GOOGLE_WEB_CLIENT_ID`, поэтому Android и backend должны использовать один и тот же Web Client ID.
- Для backend Google рекомендует проверять ID token на сервере и использовать `sub` как стабильный внешний идентификатор пользователя.

## Что нужно настроить в backend

Production `.env`:

```bash
GOOGLE_WEB_CLIENT_ID=replace-with-web-client-id.apps.googleusercontent.com
GOOGLE_AUTH_ALLOW_MOCK=false
JWT_SECRET=replace-with-long-random-secret
JWT_ISSUER=gapkassa-prod
DB_PATH=/data/app.db
CORS_ORIGINS=https://your-app-domain.example
```

Проверки:

- `GOOGLE_AUTH_ALLOW_MOCK=false`
- `APP_ENV` не `local`
- backend запущен с установленным `google-auth`

Smoke check:

```bash
cd /Users/user/Documents/автоматизация/gap-kassa
python3 local-backend/tools/api_smoke.py
```

## Что нужно настроить в Android

Для сборки приложения нужно передать тот же Web Client ID:

```bash
export GAPKASSA_GOOGLE_WEB_CLIENT_ID=replace-with-web-client-id.apps.googleusercontent.com
```

или через `~/.gradle/gradle.properties`:

```properties
GAPKASSA_GOOGLE_WEB_CLIENT_ID=replace-with-web-client-id.apps.googleusercontent.com
```

Debug/mock переменные:

- `GAPKASSA_GOOGLE_MOCK_EMAIL`
- `GAPKASSA_GOOGLE_MOCK_NAME`
- `GAPKASSA_GOOGLE_MOCK_SUBJECT`

В production они не используются.

## Release checklist

1. Указать production `GOOGLE_WEB_CLIENT_ID` на backend.
2. Указать тот же `GAPKASSA_GOOGLE_WEB_CLIENT_ID` для Android release build.
3. Выключить mock:
   - backend: `GOOGLE_AUTH_ALLOW_MOCK=false`
   - app release build уже собирается с `GOOGLE_AUTH_ALLOW_MOCK=false`
4. Проверить `CORS_ORIGINS`.
5. Проверить privacy policy URL и support email.
6. Собрать release:

```bash
cd /Users/user/Documents/автоматизация/gap-kassa
./gradlew bundleRelease
```

7. На физическом Android-устройстве проверить:
   - вход через Google;
   - возврат в приложение после выбора аккаунта;
   - создание backend-сессии;
   - `GET /me`;
   - logout и повторный login;
   - повторную установку приложения и вход.

## Что проверить в базе

После первого успешного входа через Google у пользователя должны быть:

- `users.auth_provider = 'google'`
- `users.google_sub` заполнен
- `users.email_verified = 1`

Также должен появиться аудит:

- `auth.google.login`

## Известные ограничения

- Реальный Google login нельзя полноценно проверить без живого Web Client ID из Google Cloud.
- Для эмуляторного QA mock flow остаётся полезным и быстрым способом проверить end-to-end логику приложения и backend-сессии.

## Официальные источники

- [About Sign in with Google](https://developer.android.com/identity/sign-in/credential-manager-siwg?hl=en)
- [Implement Sign in with Google](https://developer.android.com/identity/sign-in/credential-manager-siwg-implementation)
- [Credential Manager releases](https://developer.android.com/jetpack/androidx/releases/credentials?hl=en)
- [Verify the Google ID token on your server side](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token?hl=en)
- [Brand verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification)
