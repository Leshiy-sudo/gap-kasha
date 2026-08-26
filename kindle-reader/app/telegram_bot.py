from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from . import config, yandex_disk
from .formats import BOOK_SUFFIXES as SUPPORTED_BOOK_SUFFIXES

OFFSET_PATH = Path(__file__).resolve().parent.parent / "data" / "telegram_offset.txt"

logger = logging.getLogger("kindle_reader.telegram")


class TelegramBotError(RuntimeError):
    pass


def normalize_book_filename(raw_name: str) -> str:
    """Оставить безопасное имя файла и убедиться, что формат поддерживается."""
    name = raw_name.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(char for char in name if char >= " " and char != "\x7f").strip()
    if not name or name in {".", ".."}:
        raise ValueError("У документа нет корректного имени файла")

    lower_name = name.lower()
    suffix = next(
        (candidate for candidate in SUPPORTED_BOOK_SUFFIXES if lower_name.endswith(candidate)),
        None,
    )
    if suffix is None:
        raise ValueError("Поддерживаются только FB2, FB2.ZIP, EPUB, MOBI и TXT")

    max_length = 180
    if len(name) > max_length:
        stem_length = max_length - len(suffix)
        name = name[:stem_length].rstrip() + name[-len(suffix) :]
    return name


class OffsetStore:
    def __init__(self, path: Path = OFFSET_PATH):
        self.path = path

    def load(self) -> int | None:
        try:
            return int(self.path.read_text(encoding="ascii").strip())
        except (FileNotFoundError, ValueError):
            return None

    def save(self, offset: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(str(offset), encoding="ascii")
        temporary.replace(self.path)


class TelegramClient:
    def __init__(self, token: str, poll_timeout: int):
        self._token = token
        self._poll_timeout = poll_timeout
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(float(poll_timeout + 15), connect=10.0),
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def _call(self, method: str, payload: dict[str, Any]) -> Any:
        url = f"https://api.telegram.org/bot{self._token}/{method}"
        try:
            response = await self._http.post(url, json=payload)
        except httpx.HTTPError:
            raise TelegramBotError(f"Telegram API недоступен ({method})") from None

        try:
            body = response.json()
        except ValueError as exc:
            raise TelegramBotError(
                f"Telegram API вернул некорректный ответ ({method})"
            ) from exc

        if response.status_code != 200 or not body.get("ok"):
            description = str(body.get("description", "ошибка Telegram"))[:300]
            raise TelegramBotError(f"{method}: {description}")
        return body.get("result")

    async def get_updates(self, offset: int | None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": self._poll_timeout,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset
        result = await self._call("getUpdates", payload)
        return result if isinstance(result, list) else []

    async def send_message(self, chat_id: int, text: str) -> None:
        await self._call("sendMessage", {"chat_id": chat_id, "text": text})

    async def download_file(self, file_id: str) -> bytes:
        file_info = await self._call("getFile", {"file_id": file_id})
        file_path = file_info.get("file_path") if isinstance(file_info, dict) else None
        if not file_path:
            raise TelegramBotError("Telegram не вернул путь к документу")

        url = f"https://api.telegram.org/file/bot{self._token}/{file_path}"
        try:
            response = await self._http.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            raise TelegramBotError("Не удалось скачать документ из Telegram") from None
        return response.content


async def handle_update(
    client: Any,
    update: dict[str, Any],
    *,
    allowed_user_ids: frozenset[int],
    max_file_size: int,
    reader_url: str,
) -> None:
    message = update.get("message")
    if not isinstance(message, dict):
        return

    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    sender_id = sender.get("id")
    if not isinstance(chat_id, int) or chat.get("type") != "private":
        return
    if sender_id not in allowed_user_ids:
        await client.send_message(chat_id, "Доступ к загрузке книг закрыт.")
        return

    text = str(message.get("text", "")).strip()
    command = text.split(maxsplit=1)[0].split("@", 1)[0].lower() if text else ""
    if command in {"/start", "/help"}:
        await client.send_message(
            chat_id,
            "Перешлите сюда документ из книжного бота. "
            "Поддерживаются FB2, FB2.ZIP, EPUB, MOBI и TXT размером до "
            f"{max_file_size // (1024 * 1024)} МБ.",
        )
        return

    document = message.get("document")
    if not isinstance(document, dict):
        await client.send_message(
            chat_id, "Нужен документ FB2, FB2.ZIP, EPUB, MOBI или TXT."
        )
        return

    try:
        filename = normalize_book_filename(str(document.get("file_name", "")))
    except ValueError as exc:
        await client.send_message(chat_id, str(exc))
        return

    declared_size = document.get("file_size")
    if isinstance(declared_size, int) and declared_size > max_file_size:
        await client.send_message(chat_id, "Файл слишком большой для загрузки.")
        return

    file_id = document.get("file_id")
    if not isinstance(file_id, str) or not file_id:
        await client.send_message(chat_id, "Telegram не передал идентификатор документа.")
        return

    await client.send_message(chat_id, f"Загружаю «{filename}»…")
    try:
        data = await client.download_file(file_id)
        if len(data) > max_file_size:
            await client.send_message(chat_id, "Файл слишком большой для загрузки.")
            return
        await yandex_disk.upload_book(data, filename)
    except yandex_disk.YandexDiskConflictError:
        await client.send_message(chat_id, f"«{filename}» уже есть в библиотеке.")
        return
    except (TelegramBotError, yandex_disk.YandexDiskError):
        logger.exception("Failed to import Telegram document for user %s", sender_id)
        await client.send_message(
            chat_id, "Не удалось добавить книгу. Попробуйте ещё раз позже."
        )
        return

    await client.send_message(
        chat_id,
        f"«{filename}» добавлена в библиотеку.\n"
        f"Откройте {reader_url} и нажмите «Обновить список».",
    )


async def run_bot() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не настроен")
    if not config.TELEGRAM_ALLOWED_USER_IDS:
        raise RuntimeError("TELEGRAM_ALLOWED_USER_IDS не настроен")

    client = TelegramClient(
        config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_POLL_TIMEOUT_SECONDS
    )
    offset_store = OffsetStore()
    offset = offset_store.load()
    logger.info("Telegram book importer started")

    try:
        while True:
            try:
                updates = await client.get_updates(offset)
            except TelegramBotError:
                logger.exception("Telegram polling failed")
                await asyncio.sleep(3)
                continue

            for update in updates:
                update_id = update.get("update_id")
                try:
                    await handle_update(
                        client,
                        update,
                        allowed_user_ids=config.TELEGRAM_ALLOWED_USER_IDS,
                        max_file_size=config.TELEGRAM_MAX_FILE_SIZE_BYTES,
                        reader_url=config.KINDLE_READER_PUBLIC_URL,
                    )
                except Exception:
                    logger.exception("Unexpected Telegram update error")
                finally:
                    if isinstance(update_id, int):
                        offset = update_id + 1
                        offset_store.save(offset)
    finally:
        await client.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
