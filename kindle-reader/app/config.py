import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]
YANDEX_BOOKS_PATH = os.environ.get("YANDEX_BOOKS_PATH", "/Книги")
SECRET_KEY = os.environ["SECRET_KEY"]
PASSWORD_HASH = os.environ["PASSWORD_HASH"]
PASSWORD_SALT = os.environ["PASSWORD_SALT"]
CHARS_PER_PAGE = int(os.environ.get("CHARS_PER_PAGE", "1600"))


def _parse_user_ids(raw_value: str) -> frozenset[int]:
    user_ids: set[int] = set()
    for value in raw_value.split(","):
        value = value.strip()
        if value:
            user_ids.add(int(value))
    return frozenset(user_ids)


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_ALLOWED_USER_IDS = _parse_user_ids(
    os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "")
)
TELEGRAM_MAX_FILE_SIZE_BYTES = int(
    os.environ.get("TELEGRAM_MAX_FILE_SIZE_MB", "20")
) * 1024 * 1024
TELEGRAM_POLL_TIMEOUT_SECONDS = int(
    os.environ.get("TELEGRAM_POLL_TIMEOUT_SECONDS", "45")
)
KINDLE_READER_PUBLIC_URL = os.environ.get(
    "KINDLE_READER_PUBLIC_URL", "https://kindlereader.duckdns.org/"
).rstrip("/")

# Ставь false только для локальной разработки по http://127.0.0.1 —
# на проде за HTTPS должно быть true, иначе браузер cookie не примет.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
