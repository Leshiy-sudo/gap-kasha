import time

from . import config, local_library, yandex_disk
from .paginate import paginate
from .parsers.fb2 import parse_fb2
from .parsers.txt import parse_txt

LIST_TTL_SECONDS = 300

_list_cache: dict = {"items": None, "ts": 0.0}
_book_cache: dict[str, dict] = {}


async def get_book_list() -> list[dict]:
    now = time.time()
    if _list_cache["items"] is None or now - _list_cache["ts"] > LIST_TTL_SECONDS:
        remote_items = await yandex_disk.list_books()
        local_items = await local_library.list_books()
        _list_cache["items"] = sorted(
            remote_items + local_items, key=lambda item: item["name"].lower()
        )
        _list_cache["ts"] = now
    return _list_cache["items"]


def invalidate_list_cache() -> None:
    _list_cache["items"] = None


def _title_from_path(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    for suffix in (".fb2.zip", ".fb2", ".txt"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return name


async def get_book(path: str) -> dict:
    """Скачать, распарсить и разбить книгу на страницы (с кэшем в памяти процесса)."""
    cached = _book_cache.get(path)
    if cached:
        return cached

    data = await download_book(path)
    if path.lower().endswith(".txt"):
        title, paragraphs = parse_txt(data)
    else:
        title, paragraphs = parse_fb2(data)

    result = {
        "title": title or _title_from_path(path),
        "pages": paginate(paragraphs, config.CHARS_PER_PAGE),
    }
    _book_cache[path] = result
    return result


async def download_book(path: str) -> bytes:
    if path.startswith(local_library.PATH_PREFIX):
        return await local_library.download_book(path)
    return await yandex_disk.download_book(path)
