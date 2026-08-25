import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

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

_telegram_api_id_value = os.environ.get("TELEGRAM_API_ID", "").strip()
TELEGRAM_API_ID = int(_telegram_api_id_value) if _telegram_api_id_value else 0
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "").strip()
_telegram_session_value = os.environ.get(
    "TELEGRAM_SESSION_PATH", "data/telegram_catalog"
)
TELEGRAM_SESSION_PATH = Path(_telegram_session_value)
if not TELEGRAM_SESSION_PATH.is_absolute():
    TELEGRAM_SESSION_PATH = PROJECT_DIR / TELEGRAM_SESSION_PATH
TELEGRAM_SOURCE_BOT = os.environ.get(
    "TELEGRAM_SOURCE_BOT", "flibustafreebookbot"
).strip().lstrip("@")
TELEGRAM_CATALOG_TIMEOUT_SECONDS = int(
    os.environ.get("TELEGRAM_CATALOG_TIMEOUT_SECONDS", "25")
)
TELEGRAM_ACTION_MAX_AGE_SECONDS = int(
    os.environ.get("TELEGRAM_ACTION_MAX_AGE_SECONDS", "600")
)
_local_books_value = os.environ.get("LOCAL_BOOKS_PATH", "data/imported_books")
LOCAL_BOOKS_PATH = Path(_local_books_value)
if not LOCAL_BOOKS_PATH.is_absolute():
    LOCAL_BOOKS_PATH = PROJECT_DIR / LOCAL_BOOKS_PATH

# Ставь false только для локальной разработки по http://127.0.0.1 —
# на проде за HTTPS должно быть true, иначе браузер cookie не примет.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
