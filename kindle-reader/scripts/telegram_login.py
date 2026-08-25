"""Интерактивно создаёт защищённую Telethon-сессию для веб-каталога."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from telethon import TelegramClient  # noqa: E402

from app import config  # noqa: E402


async def main() -> None:
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        raise SystemExit(
            "Сначала заполните TELEGRAM_API_ID и TELEGRAM_API_HASH в .env"
        )

    config.TELEGRAM_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(
        str(config.TELEGRAM_SESSION_PATH),
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH,
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
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
