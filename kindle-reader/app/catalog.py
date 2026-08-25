from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from telethon import TelegramClient
from telethon.errors import RPCError

from . import config, local_library
from .telegram_bot import normalize_book_filename

logger = logging.getLogger("kindle_reader.catalog")
logging.getLogger("telethon").setLevel(logging.WARNING)

_KNOWN_FORMATS = ("fb2", "txt", "epub", "mobi", "pdf", "html", "rtf")
_SUPPORTED_FORMATS = {"fb2", "txt"}


class CatalogError(RuntimeError):
    pass


class CatalogNotConfigured(CatalogError):
    pass


class CatalogNotAuthorized(CatalogError):
    pass


class CatalogTimeout(CatalogError):
    pass


@dataclass(frozen=True)
class CatalogAction:
    label: str
    token: str


@dataclass(frozen=True)
class CatalogEntry:
    text: str
    actions: list[CatalogAction] = field(default_factory=list)
    document_name: str | None = None


@dataclass(frozen=True)
class CatalogOutcome:
    entries: list[CatalogEntry]
    imported_names: list[str] = field(default_factory=list)
    existing_names: list[str] = field(default_factory=list)
    unsupported_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ActionTarget:
    kind: str
    message_id: int = 0
    row: int = 0
    column: int = 0
    command: str = ""


class ActionCodec:
    def __init__(self, secret_key: str):
        self._serializer = URLSafeTimedSerializer(
            secret_key, salt="kindle-reader-catalog-action"
        )

    def encode_button(self, message_id: int, row: int, column: int) -> str:
        return self._serializer.dumps(
            {
                "kind": "button",
                "message_id": message_id,
                "row": row,
                "column": column,
            }
        )

    def encode_command(self, command: str) -> str:
        return self._serializer.dumps({"kind": "command", "command": command})

    def decode(self, token: str) -> ActionTarget:
        try:
            payload = self._serializer.loads(
                token, max_age=config.TELEGRAM_ACTION_MAX_AGE_SECONDS
            )
        except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError) as exc:
            raise CatalogError("Действие устарело. Повторите поиск.") from exc

        try:
            kind = str(payload["kind"])
            if kind == "button":
                target = ActionTarget(
                    kind=kind,
                    message_id=int(payload["message_id"]),
                    row=int(payload["row"]),
                    column=int(payload["column"]),
                )
                if target.message_id <= 0 or target.row < 0 or target.column < 0:
                    raise ValueError
                return target
            if kind == "command":
                command = str(payload["command"])
                if not re.fullmatch(r"/[A-Za-z][A-Za-z0-9_]{0,63}", command):
                    raise ValueError
                return ActionTarget(kind=kind, command=command)
        except (KeyError, TypeError, ValueError) as exc:
            raise CatalogError("Некорректное действие каталога") from exc
        raise CatalogError("Некорректное действие каталога")


class TelegramCatalog:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._actions = ActionCodec(config.SECRET_KEY)

    @staticmethod
    def _session_file() -> Path:
        path = config.TELEGRAM_SESSION_PATH
        return path if path.suffix == ".session" else path.with_suffix(".session")

    def configuration_error(self) -> str | None:
        if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
            return "Telegram API ещё не настроен"
        if not config.TELEGRAM_SOURCE_BOT:
            return "Telegram-бот каталога не указан"
        if not self._session_file().exists():
            return "Telegram-аккаунт ещё не авторизован"
        return None

    def _make_client(self) -> TelegramClient:
        config.TELEGRAM_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        return TelegramClient(
            str(config.TELEGRAM_SESSION_PATH),
            config.TELEGRAM_API_ID,
            config.TELEGRAM_API_HASH,
            device_model="Kindle Reader",
            app_version="1.0",
            lang_code="ru",
            system_lang_code="ru",
            request_retries=3,
            connection_retries=3,
            auto_reconnect=False,
        )

    async def search(self, query: str) -> CatalogOutcome:
        query = " ".join(query.split())
        if not query:
            raise CatalogError("Введите название книги или имя автора")
        if len(query) > 120:
            raise CatalogError("Запрос слишком длинный")

        async with self._lock:
            return await self._with_client(self._search, query)

    async def activate(self, token: str) -> CatalogOutcome:
        target = self._actions.decode(token)
        async with self._lock:
            if target.kind == "command":
                return await self._with_client(
                    self._send_command, target.command
                )
            return await self._with_client(
                self._activate_button,
                target.message_id,
                target.row,
                target.column,
            )

    async def _with_client(self, operation: Any, *args: Any) -> CatalogOutcome:
        configuration_error = self.configuration_error()
        if configuration_error:
            raise CatalogNotConfigured(configuration_error)

        client = self._make_client()
        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise CatalogNotAuthorized("Telegram-сессия требует повторного входа")
            source = await client.get_entity(config.TELEGRAM_SOURCE_BOT)
            return await operation(client, source, *args)
        except CatalogError:
            raise
        except RPCError:
            logger.exception("Telegram catalog RPC failure")
            raise CatalogError("Telegram временно отклонил запрос") from None
        except (OSError, asyncio.TimeoutError):
            logger.exception("Telegram catalog connection failure")
            raise CatalogError("Не удалось связаться с Telegram") from None
        finally:
            await client.disconnect()

    async def _search(
        self, client: TelegramClient, source: Any, query: str
    ) -> CatalogOutcome:
        sent = await client.send_message(source, query)
        messages = await self._wait_for_changes(client, source, after_id=sent.id)
        return await self._build_outcome(client, messages, import_documents=True)

    async def _send_command(
        self, client: TelegramClient, source: Any, command: str
    ) -> CatalogOutcome:
        sent = await client.send_message(source, command)
        messages = await self._wait_for_changes(client, source, after_id=sent.id)
        return await self._build_outcome(client, messages, import_documents=True)

    async def _activate_button(
        self,
        client: TelegramClient,
        source: Any,
        message_id: int,
        row: int,
        column: int,
    ) -> CatalogOutcome:
        message = await client.get_messages(source, ids=message_id)
        if message is None:
            raise CatalogError("Ответ каталога больше недоступен. Повторите поиск.")

        buttons = message.buttons or await message.get_buttons()
        if not buttons or row >= len(buttons) or column >= len(buttons[row]):
            raise CatalogError("Кнопка каталога больше недоступна. Повторите поиск.")
        button = buttons[row][column]
        if getattr(button, "url", None):
            raise CatalogError("Внешние ссылки каталога не открываются автоматически")

        latest = await client.get_messages(source, limit=1)
        after_id = latest[0].id if latest else message.id
        fingerprint = self._fingerprint(message)
        await message.click(row, column)
        messages = await self._wait_for_changes(
            client,
            source,
            after_id=after_id,
            watched_id=message.id,
            watched_fingerprint=fingerprint,
        )
        return await self._build_outcome(client, messages, import_documents=True)

    async def _wait_for_changes(
        self,
        client: TelegramClient,
        source: Any,
        *,
        after_id: int,
        watched_id: int | None = None,
        watched_fingerprint: tuple[Any, ...] | None = None,
    ) -> list[Any]:
        deadline = time.monotonic() + config.TELEGRAM_CATALOG_TIMEOUT_SECONDS
        changed_at: float | None = None
        collected: dict[int, Any] = {}

        while time.monotonic() < deadline:
            recent = await client.get_messages(source, limit=30)
            for message in recent:
                if not message.out and message.id > after_id:
                    collected[message.id] = message

            if watched_id is not None:
                watched = next(
                    (message for message in recent if message.id == watched_id), None
                )
                if watched is not None and self._fingerprint(watched) != watched_fingerprint:
                    collected[watched.id] = watched

            if collected:
                if changed_at is None:
                    changed_at = time.monotonic()
                elif time.monotonic() - changed_at >= 0.8:
                    return [collected[key] for key in sorted(collected)]
            await asyncio.sleep(0.4)

        if collected:
            return [collected[key] for key in sorted(collected)]
        raise CatalogTimeout("Каталог не ответил вовремя. Попробуйте ещё раз.")

    @staticmethod
    def _fingerprint(message: Any) -> tuple[Any, ...]:
        rows = message.buttons or []
        labels = tuple(
            tuple(str(getattr(button, "text", "")) for button in row) for row in rows
        )
        return message.raw_text, message.edit_date, labels

    @staticmethod
    def _format_name(value: str) -> str | None:
        candidate = value.strip().lower().lstrip("/.")
        match = re.fullmatch(
            rf"({'|'.join(_KNOWN_FORMATS)})(?:[_-]?\d+)?", candidate
        )
        return match.group(1) if match else None

    async def _build_outcome(
        self,
        client: TelegramClient,
        messages: list[Any],
        *,
        import_documents: bool,
    ) -> CatalogOutcome:
        entries: list[CatalogEntry] = []
        imported_names: list[str] = []
        existing_names: list[str] = []
        unsupported_names: list[str] = []

        for message in messages:
            document_name = getattr(getattr(message, "file", None), "name", None)
            if document_name and import_documents:
                try:
                    safe_name = normalize_book_filename(document_name)
                except ValueError:
                    unsupported_names.append(document_name)
                else:
                    data = await client.download_media(message, file=bytes)
                    if not isinstance(data, bytes):
                        raise CatalogError("Telegram не передал содержимое книги")
                    if len(data) > config.TELEGRAM_MAX_FILE_SIZE_BYTES:
                        raise CatalogError("Полученная книга слишком большая")
                    try:
                        await local_library.save_book(data, safe_name)
                    except local_library.LocalLibraryConflictError:
                        existing_names.append(safe_name)
                    except local_library.LocalLibraryError:
                        logger.exception("Failed to save catalog document")
                        raise CatalogError(
                            "Не удалось сохранить книгу в библиотеку"
                        ) from None
                    else:
                        imported_names.append(safe_name)

            actions: list[CatalogAction] = []
            rows = message.buttons or await message.get_buttons() or []
            for row_index, row_buttons in enumerate(rows):
                for column_index, button in enumerate(row_buttons):
                    label = " ".join(str(getattr(button, "text", "")).split())
                    if not label or getattr(button, "url", None):
                        continue
                    format_name = self._format_name(label)
                    if format_name and format_name not in _SUPPORTED_FORMATS:
                        continue
                    if format_name:
                        label = f"{format_name.upper()} — добавить в библиотеку"
                    actions.append(
                        CatalogAction(
                            label=label[:100],
                            token=self._actions.encode_button(
                                message.id, row_index, column_index
                            ),
                        )
                    )

            text = (message.raw_text or "").strip()
            actions.extend(self._command_actions(text))
            if text or actions or document_name:
                entries.append(
                    CatalogEntry(
                        text=text,
                        actions=actions,
                        document_name=document_name,
                    )
                )

        return CatalogOutcome(
            entries=entries,
            imported_names=imported_names,
            existing_names=existing_names,
            unsupported_names=unsupported_names,
        )

    def _command_actions(self, text: str) -> list[CatalogAction]:
        """Превращает команды из текста бота в понятные кнопки выбора."""
        actions: list[CatalogAction] = []
        block_lines: list[str] = []
        seen: set[str] = set()

        for raw_line in text.splitlines():
            line = raw_line.strip()
            commands = re.findall(r"(?<![\w/])/[A-Za-z][A-Za-z0-9_]{0,63}", line)
            for command in commands:
                if command in seen:
                    continue
                seen.add(command)
                format_name = self._format_name(command)
                if format_name and format_name not in _SUPPORTED_FORMATS:
                    continue
                title = next(
                    (
                        candidate
                        for candidate in block_lines
                        if candidate and not candidate.lower().startswith("найдено:")
                    ),
                    command,
                )
                if format_name:
                    label = f"{format_name.upper()} — добавить в библиотеку"
                else:
                    label = f"Выбрать: {title}" if title != command else command
                actions.append(
                    CatalogAction(
                        label=label[:100],
                        token=self._actions.encode_command(command),
                    )
                )
                block_lines = []
            if not commands:
                block_lines.append(line)
        return actions


telegram_catalog = TelegramCatalog()
