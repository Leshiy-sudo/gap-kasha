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

# Ставь false только для локальной разработки по http://127.0.0.1 —
# на проде за HTTPS должно быть true, иначе браузер cookie не примет.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
