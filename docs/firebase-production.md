# Firebase Production Setup

## Что уже подготовлено в проекте

- Android-клиент уже содержит FCM service.
- Добавлены зависимости Firebase Messaging и Firebase Analytics.
- Приложение умеет:
  - запрашивать `POST_NOTIFICATIONS` на Android 13+;
  - получать FCM token;
  - отправлять token на backend в `POST /devices/fcm-token`.

## Что нужно положить в проект

1. Открыть Firebase Console.
2. Выбрать production-проект Firebase.
3. Добавить Android app с package name:

   `com.gapkassa`

4. Скачать `google-services.json`.
5. Положить файл сюда:

   `/Users/user/Documents/автоматизация/gap-kassa/app/google-services.json`

## Что включить в Firebase Console

- Cloud Messaging
- Analytics

Опционально для следующего этапа:

- Crashlytics
- App Distribution
- Performance Monitoring

## Что проверить после добавления файла

1. `./gradlew assembleDebug`
2. `./gradlew bundleRelease`
3. Логин в приложение
4. Получение FCM token
5. Наличие строки в backend-таблице `device_tokens`

## Backend

Backend уже готов принимать device token:

- `POST /devices/fcm-token`

И хранит их в таблице:

- `device_tokens`

## Важно

Без настоящего `google-services.json` production Firebase нельзя считать полностью завершённым: кодовая база готова, но привязка к реальному Firebase-проекту зависит от файла конфигурации из Firebase Console.
