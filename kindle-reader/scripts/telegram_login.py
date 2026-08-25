"""Интерактивно создаёт защищённую Telethon-сессию для веб-каталога."""

from __future__ import annotations

import asyncio
import getpass
import os
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import dotenv_values, set_key  # noqa: E402
from telethon import TelegramClient  # noqa: E402


ENV_PATH = PROJECT_DIR / ".env"


def _credentials() -> tuple[int, str, Path]:
    values = dotenv_values(ENV_PATH)
    api_id_text = str(
        os.environ.get("TELEGRAM_API_ID") or values.get("TELEGRAM_API_ID") or ""
    ).strip()
    api_hash = str(
        os.environ.get("TELEGRAM_API_HASH") or values.get("TELEGRAM_API_HASH") or ""
    ).strip()

    if not api_id_text:
        api_id_text = input("Telegram API ID: ").strip()
    if not api_id_text.isdigit() or int(api_id_text) <= 0:
        raise SystemExit("API ID должен состоять из цифр")

    if not api_hash:
        api_hash = getpass.getpass("Telegram API HASH (ввод скрыт): ").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{32}", api_hash):
        raise SystemExit("API HASH должен содержать 32 шестнадцатеричных символа")

    if not ENV_PATH.exists():
        raise SystemExit(f"Файл настроек не найден: {ENV_PATH}")
    set_key(ENV_PATH, "TELEGRAM_API_ID", api_id_text, quote_mode="never")
    set_key(ENV_PATH, "TELEGRAM_API_HASH", api_hash, quote_mode="never")

    session_text = str(
        os.environ.get("TELEGRAM_SESSION_PATH")
        or values.get("TELEGRAM_SESSION_PATH")
        or "data/telegram_catalog"
    ).strip()
    session_path = Path(session_text)
    if not session_path.is_absolute():
        session_path = PROJECT_DIR / session_path
    return int(api_id_text), api_hash, session_path


async def main() -> None:
    api_id, api_hash, session_path = _credentials()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(
        str(session_path),
        api_id,
        api_hash,
        device_model="Kindle Reader setup",
        app_version="1.0",
        lang_code="ru",
        system_lang_code="ru",
    )
    try:
        await client.start()
        me = await client.get_me()
        username = f"@{me.username}" if me.username else "без username"
        print(f"Telegram подключён: ID {me.id}, {username}")
        print("Теперь сообщите в Codex: готово")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
