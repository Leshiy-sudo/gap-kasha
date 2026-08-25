# Kindle Reader

Минимальная читалка книг с Яндекс.Диска для браузера Kindle: список книг → чтение постранично.
Без регистрации — вход по одному паролю.

## Установка

```bash
cd kindle-reader
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка

1. Скопируй `.env.example` в `.env`.
2. Впиши `YANDEX_TOKEN` (см. основной README проекта / инструкцию, которую прислал бот).
3. Проверь `YANDEX_BOOKS_PATH` — путь к папке с книгами на Диске (например `/Книги`).
4. Сгенерируй ключ сессии:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Впиши результат в `SECRET_KEY`.
5. Сгенерируй пароль для входа:
   ```bash
   python scripts/hash_password.py "мой-пароль"
   ```
   Впиши выведенные `PASSWORD_HASH` и `PASSWORD_SALT` в `.env`.

## Запуск

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Открой `http://<адрес-компьютера>:8000` — сначала с компьютера, потом с Kindle (тот же Wi-Fi).

## Поддерживаемые форматы

`.txt`, `.fb2`, `.fb2.zip`. EPUB и PDF пока не поддерживаются.

## Поиск книг через браузер

Страница `/catalog` отправляет запрос книжному Telegram-боту через отдельный
пользовательский Telegram-аккаунт. Ответы и кнопки бота отображаются прямо в
браузере Kindle. Полученный FB2, FB2.ZIP или TXT автоматически сохраняется в
`YANDEX_BOOKS_PATH` и появляется в библиотеке.

1. Создай отдельный Telegram-аккаунт и один раз нажми **Start** у
   `@flibustafreebookbot`.
2. На `https://my.telegram.org` открой **API Development tools** и создай
   приложение. Запиши `api_id` и `api_hash` в `.env`:
   ```dotenv
   TELEGRAM_API_ID=123456
   TELEGRAM_API_HASH=...
   TELEGRAM_SESSION_PATH=data/telegram_catalog
   TELEGRAM_SOURCE_BOT=flibustafreebookbot
   ```
3. Выполни интерактивный вход:
   ```bash
   python scripts/telegram_login.py
   ```
   Telegram попросит номер, код подтверждения и, если включён, облачный пароль.

Файл `data/telegram_catalog.session` даёт доступ к аккаунту. Он исключён из Git;
не копируй его в переписку и не публикуй.

Используй интеграцию только для материалов, которые имеешь право получать и
читать.

## Старый импорт пересылкой через Telegram

Telegram-мост принимает книгу, которую пользователь вручную переслал из
книжного бота, и загружает её в ту же папку `YANDEX_BOOKS_PATH`. Это запасной
вариант; для поиска прямо на сайте используй раздел выше.

1. Создай собственного бота через `@BotFather`.
2. Добавь в `.env`:
   ```dotenv
   TELEGRAM_BOT_TOKEN=токен-от-BotFather
   TELEGRAM_ALLOWED_USER_IDS=123456789
   KINDLE_READER_PUBLIC_URL=https://kindlereader.duckdns.org/
   ```
   `TELEGRAM_ALLOWED_USER_IDS` — числовые ID пользователей через запятую.
3. Локальный запуск:
   ```bash
   python -m app.telegram_bot
   ```
4. На VPS установи `deploy/kindle-telegram-bot.service` в
   `/etc/systemd/system/`, перечитай конфигурацию systemd и включи службу.

После этого перешли боту документ FB2, FB2.ZIP или TXT. Бот принимает файлы
только от разрешённых ID, не перезаписывает существующие книги и сохраняет
позицию Telegram long polling в `data/telegram_offset.txt`.

Проверка тестов:

```bash
python -m unittest discover -s tests -v
```

## Известные упрощения (сделано осознанно, для минимального объёма)

- Список книг и разобранные страницы кэшируются только в памяти процесса — перезапуск сервера сбрасывает кэш (это нормально, файлы просто перечитаются с Диска).
- Нет ограничения на число попыток входа — если планируешь открыть доступ наружу (не только по локальной сети), стоит добавить rate-limit или отдельно закрыть доступ через Tailscale.
- Размер шрифта не настраивается из интерфейса — если Kindle-браузер поддерживает зум, используй его; либо поменяй `CHARS_PER_PAGE` и стили в `app/static/style.css`.
