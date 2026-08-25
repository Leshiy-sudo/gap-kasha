import httpx

from . import config

API_BASE = "https://cloud-api.yandex.net/v1/disk"
BOOK_EXTENSIONS = (".fb2", ".fb2.zip", ".txt")


class YandexDiskError(RuntimeError):
    pass


class YandexDiskConflictError(YandexDiskError):
    pass


def _headers() -> dict:
    return {"Authorization": f"OAuth {config.YANDEX_TOKEN}"}


async def list_books() -> list[dict]:
    """Список книг в папке YANDEX_BOOKS_PATH, отсортированный по имени."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{API_BASE}/resources",
            headers=_headers(),
            params={
                "path": config.YANDEX_BOOKS_PATH,
                "limit": 1000,
                "fields": "_embedded.items.name,_embedded.items.path,_embedded.items.type,_embedded.items.size",
            },
        )
    if resp.status_code != 200:
        raise YandexDiskError(f"Яндекс.Диск вернул {resp.status_code}: {resp.text}")

    items = resp.json().get("_embedded", {}).get("items", [])
    books = [
        item
        for item in items
        if item.get("type") == "file" and item["name"].lower().endswith(BOOK_EXTENSIONS)
    ]
    books.sort(key=lambda item: item["name"].lower())
    return books


async def download_book(path: str) -> bytes:
    """Скачать содержимое файла по его пути на Яндекс.Диске."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(
            f"{API_BASE}/resources/download",
            headers=_headers(),
            params={"path": path},
        )
        if resp.status_code != 200:
            raise YandexDiskError(f"Не удалось получить ссылку на файл: {resp.status_code}")

        href = resp.json()["href"]
        file_resp = await client.get(href)
        if file_resp.status_code != 200:
            raise YandexDiskError(f"Не удалось скачать файл: {file_resp.status_code}")

        return file_resp.content


async def upload_book(data: bytes, name: str, *, overwrite: bool = False) -> str:
    """Загрузить книгу в папку YANDEX_BOOKS_PATH и вернуть её disk-путь."""
    directory = config.YANDEX_BOOKS_PATH.rstrip("/")
    path = f"{directory}/{name}" if directory else f"/{name}"

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(
            f"{API_BASE}/resources/upload",
            headers=_headers(),
            params={"path": path, "overwrite": str(overwrite).lower()},
        )
        if resp.status_code == 409:
            raise YandexDiskConflictError("Файл с таким именем уже существует")
        if resp.status_code != 200:
            raise YandexDiskError(
                f"Не удалось получить ссылку загрузки: {resp.status_code}"
            )

        href = resp.json().get("href")
        if not href:
            raise YandexDiskError("Яндекс.Диск не вернул ссылку загрузки")

        upload_resp = await client.put(href, content=data)
        if upload_resp.status_code not in (201, 202):
            raise YandexDiskError(
                f"Не удалось загрузить файл: {upload_resp.status_code}"
            )

    return f"disk:{path}"
