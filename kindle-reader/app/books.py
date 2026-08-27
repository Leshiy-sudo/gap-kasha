import time
from datetime import datetime, timedelta, timezone

from . import config, convert, yandex_disk
from .formats import BOOK_SUFFIXES
from .paginate import paginate
from .parsers.fb2 import parse_fb2
from .parsers.txt import parse_txt
from .yandex_disk import YandexDiskError

LIST_TTL_SECONDS = 300

_list_cache: dict = {"items": None, "ts": 0.0}
_book_cache: dict[str, dict] = {}
_fb2_conversion_cache: dict[str, bytes] = {}
_last_remote_error: str | None = None
_DISPLAY_TIMEZONE = timezone(timedelta(hours=5))


def format_added_at(value: str | None) -> str:
    if not value:
        return "Дата неизвестна"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return "Дата неизвестна"
    return parsed.astimezone(_DISPLAY_TIMEZONE).strftime("%d.%m.%Y %H:%M")


async def get_book_list() -> list[dict]:
    global _last_remote_error
    now = time.time()
    if _list_cache["items"] is None or now - _list_cache["ts"] > LIST_TTL_SECONDS:
        try:
            remote_items = await yandex_disk.list_books()
        except YandexDiskError as exc:
            _last_remote_error = str(exc)
            return _list_cache["items"] or []
        except Exception:
            _last_remote_error = "Яндекс.Диск временно недоступен"
            return _list_cache["items"] or []
        _last_remote_error = None
        items = []
        for original in remote_items:
            item = dict(original)
            item["added_at_display"] = format_added_at(
                item.get("created") or item.get("modified")
            )
            items.append(item)
        _list_cache["items"] = sorted(
            items, key=lambda item: item["name"].lower()
        )
        _list_cache["ts"] = now
    return _list_cache["items"]


def last_remote_error() -> str | None:
    return _last_remote_error


def invalidate_list_cache() -> None:
    _list_cache["items"] = None


def title_from_path(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    for suffix in BOOK_SUFFIXES:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return name


async def get_book(path: str) -> dict:
    """Скачать, распарсить и разбить книгу на страницы (с кэшем в памяти процесса)."""
    cached = _book_cache.get(path)
    if cached:
        return cached

    data = await download_book(path)
    name = path.rsplit("/", 1)[-1]
    if name.lower().endswith(".txt"):
        title, paragraphs = parse_txt(data)
    else:
        fb2_data = await get_fb2_bytes(path, name, data)
        title, paragraphs = parse_fb2(fb2_data)

    result = {
        "title": title or title_from_path(path),
        "pages": paginate(paragraphs, config.CHARS_PER_PAGE),
    }
    _book_cache[path] = result
    return result


async def get_fb2_bytes(path: str, name: str, data: bytes) -> bytes:
    lower_name = name.lower()
    if not lower_name.endswith((".epub", ".mobi")):
        return data

    cached = _fb2_conversion_cache.get(path)
    if cached is not None:
        return cached

    fb2_data = await convert.convert_to_fb2(data, name)
    _fb2_conversion_cache[path] = fb2_data
    return fb2_data


async def download_book(path: str) -> bytes:
    return await yandex_disk.download_book(path)


async def delete_book(path: str) -> None:
    await yandex_disk.delete_book(path)
    _book_cache.pop(path, None)
    _fb2_conversion_cache.pop(path, None)
    invalidate_list_cache()
