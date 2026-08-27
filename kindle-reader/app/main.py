import asyncio
import hashlib
import logging
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote, urlencode

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import (
    auth,
    books,
    catalog,
    catalog_jobs,
    config,
    convert,
    library_meta,
    metadata,
    progress,
)
from .yandex_disk import YandexDiskError

_MIME_TYPES = {
    ".fb2": "application/x-fictionbook+xml",
    ".zip": "application/zip",
    ".txt": "text/plain; charset=utf-8",
    ".epub": "application/epub+zip",
    ".mobi": "application/x-mobipocket-ebook",
}

FONT_SIZE_COOKIE = "font_size"
DEFAULT_FONT_SIZE = 2
MIN_FONT_SIZE = 1
MAX_FONT_SIZE = 5
LIBRARY_PAGE_SIZE = 10

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("kindle_reader.web")
_background_tasks: set[asyncio.Task] = set()


def _asset_version(filename: str) -> int:
    try:
        return int(os.path.getmtime(Path("app/static") / filename))
    except OSError:
        return 0


templates.env.globals["asset_version"] = _asset_version


def _safe_next(path: str) -> str:
    """Не даём редиректить после логина на внешний адрес (open redirect)."""
    if path.startswith("/") and not path.startswith("//") and not path.startswith("/\\"):
        return path
    return "/"


def _require_auth(request: Request) -> RedirectResponse | None:
    if not auth.is_authenticated(request):
        original_path = request.url.path
        if request.url.query:
            original_path += f"?{request.url.query}"
        return RedirectResponse(f"/login?next={quote(original_path)}", status_code=303)
    return None


def _paginate_items(
    items: list[dict], requested_page: int
) -> tuple[list[dict], int, int]:
    total_pages = max(1, (len(items) + LIBRARY_PAGE_SIZE - 1) // LIBRARY_PAGE_SIZE)
    page = max(1, min(requested_page, total_pages))
    start = (page - 1) * LIBRARY_PAGE_SIZE
    return items[start : start + LIBRARY_PAGE_SIZE], page, total_pages


def _pagination_window(page: int, total_pages: int) -> list[int | None]:
    visible = {1, total_pages}
    visible.update(range(max(1, page - 2), min(total_pages, page + 2) + 1))
    result: list[int | None] = []
    previous = 0
    for number in sorted(visible):
        if previous and number - previous > 1:
            result.append(None)
        result.append(number)
        previous = number
    return result


def _book_name(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _library_url(
    *,
    page: int = 1,
    q: str = "",
    author: str = "",
    deleted: str = "",
) -> str:
    params: dict[str, str | int] = {}
    if page > 1:
        params["page"] = page
    if q:
        params["q"] = q
    if author:
        params["author"] = author
    if deleted:
        params["deleted"] = deleted
    return f"/?{urlencode(params)}" if params else "/"


def _enrich_items(items: list[dict]) -> list[dict]:
    meta_map = metadata.book_metadata.get_all()
    override_map = library_meta.get_all()
    enriched = []
    for item in items:
        meta = meta_map.get(item["path"])
        override = override_map.get(item["path"])
        enriched.append(
            {
                **item,
                "title": (
                    (override.title if override else None)
                    or
                    (meta.title if meta else None)
                    or books.title_from_path(item["path"])
                ),
                "author": (override.author if override else None)
                or (meta.author if meta else None),
                "has_cover": (override.has_custom_cover if override else False)
                or (meta.has_cover if meta else False),
                "series": override.series if override else None,
                "series_index": override.series_index if override else None,
                "status": override.status if override else None,
            }
        )
    return enriched


COVER_PALETTE = [
    ("#6b2a2a", "#a84a3a"),
    ("#7a3630", "#b5573f"),
    ("#2f4858", "#6c91a3"),
    ("#35502f", "#6f8f57"),
    ("#3a3350", "#6c5f95"),
    ("#4a3620", "#8a6a3f"),
    ("#294a4a", "#4f8080"),
]
SIDEBAR_PAGE_SIZE = 10
_STATUS_OPTIONS = [
    (key, library_meta.STATUS_LABELS[key])
    for key in (None, *library_meta.STATUS_CHOICES)
]
MAX_COVER_UPLOAD_BYTES = 10 * 1024 * 1024


def _cover_gradient(path: str) -> str:
    digest = hashlib.sha1(path.encode("utf-8")).hexdigest()
    first, second = COVER_PALETTE[int(digest, 16) % len(COVER_PALETTE)]
    return f"linear-gradient(160deg, {first}, {second})"


def _is_kindle(request: Request) -> bool:
    user_agent = request.headers.get("user-agent", "").lower()
    return "kindle" in user_agent or "silk/" in user_agent


def _visible_count(pairs: list, shown: int, selected_name: str) -> int:
    shown = max(shown, SIDEBAR_PAGE_SIZE)
    if selected_name:
        index = next(
            (i for i, (name, _) in enumerate(pairs) if name == selected_name),
            None,
        )
        if index is not None and index >= shown:
            shown = ((index // SIDEBAR_PAGE_SIZE) + 1) * SIDEBAR_PAGE_SIZE
    return min(shown, len(pairs))


def _back_url(back: str) -> str:
    return f"/?{back}" if back else "/"


async def _known_book_path(path: str) -> bool:
    return any(item["path"] == path for item in await books.get_book_list())


@app.get("/login")
async def login_form(request: Request):
    if auth.is_authenticated(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@app.post("/login")
async def login_submit(request: Request, password: str = Form(...), next: str = Form("/")):
    if not auth.verify_password(password):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Неверный пароль"}, status_code=401
        )
    response = RedirectResponse(_safe_next(next), status_code=303)
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_session_cookie(),
        httponly=True,
        samesite="lax",
        secure=config.COOKIE_SECURE,
        max_age=auth.MAX_AGE_SECONDS,
    )
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.COOKIE_NAME)
    return response


@app.get("/")
async def library(
    request: Request,
    page: int = 1,
    q: str = "",
    author: str = "",
    series: str = "",
    status: str = "",
    panel: str = "open",
    authors_shown: int = SIDEBAR_PAGE_SIZE,
    series_shown: int = SIDEBAR_PAGE_SIZE,
    deleted: str | None = None,
):
    if redirect := _require_auth(request):
        return redirect

    items = await books.get_book_list()
    error = books.last_remote_error()
    source_total = len(items)

    enriched = _enrich_items(items)
    query = " ".join(q.split()).lower()
    if query:
        enriched = [
            item
            for item in enriched
            if query in item["title"].lower()
            or query in (item["author"] or "").lower()
            or query in item["name"].lower()
        ]

    all_count = len(enriched)
    authors: dict[str, int] = {}
    series_counts: dict[str, int] = {}
    for item in enriched:
        if item["author"]:
            authors[item["author"]] = authors.get(item["author"], 0) + 1
        if item["series"]:
            series_counts[item["series"]] = series_counts.get(item["series"], 0) + 1

    if series:
        enriched = [item for item in enriched if item["series"] == series]
        enriched.sort(
            key=lambda item: (
                item["series_index"] is None,
                item["series_index"] or 0,
            )
        )
    elif author:
        enriched = [item for item in enriched if item["author"] == author]
    elif status:
        enriched = [item for item in enriched if item["status"] == status]

    total_items = len(enriched)
    page_items, page, total_pages = _paginate_items(enriched, page)
    metadata.book_metadata.kick(page_items)
    saved_pages = progress.get_all()

    kindle = _is_kindle(request)
    if not kindle:
        for item in page_items:
            if not item["has_cover"]:
                item["cover_gradient"] = _cover_gradient(item["path"])

    authors_sorted = sorted(authors.items(), key=lambda pair: pair[0].lower())
    series_sorted = sorted(
        series_counts.items(), key=lambda pair: pair[0].lower()
    )
    authors_visible_count = _visible_count(authors_sorted, authors_shown, author)
    series_visible_count = _visible_count(series_sorted, series_shown, series)

    return templates.TemplateResponse(
        request,
        "library.html" if kindle else "library_modern.html",
        {
            "items": page_items,
            "error": error,
            "deleted": deleted,
            "saved_pages": saved_pages,
            "q": q,
            "author": author,
            "series": series,
            "status": status,
            "panel_open": panel != "closed",
            "authors": authors_sorted,
            "series_list": series_sorted,
            "authors_visible": authors_sorted[:authors_visible_count],
            "series_visible": series_sorted[:series_visible_count],
            "authors_shown": authors_visible_count,
            "series_shown": series_visible_count,
            "authors_more": min(
                SIDEBAR_PAGE_SIZE, len(authors_sorted) - authors_visible_count
            ),
            "series_more": min(
                SIDEBAR_PAGE_SIZE, len(series_sorted) - series_visible_count
            ),
            "back_qs": str(request.url.query),
            "status_options": _STATUS_OPTIONS,
            "status_labels": library_meta.STATUS_LABELS,
            "all_count": all_count,
            "page": page,
            "total_pages": total_pages,
            "total_items": total_items,
            "source_total": source_total,
            "pagination": _pagination_window(page, total_pages),
            "enrichment_running": metadata.book_metadata.is_running(),
            "auto_refresh": metadata.book_metadata.is_running() and not kindle,
        },
    )


@app.get("/refresh")
async def refresh(
    request: Request,
    page: int = 1,
    q: str = "",
    author: str = "",
    back: str = "",
):
    if redirect := _require_auth(request):
        return redirect
    books.invalidate_list_cache()
    target = _back_url(back) if back else _library_url(
        page=max(1, page), q=q, author=author
    )
    return RedirectResponse(target, status_code=303)


@app.get("/cover")
async def cover(request: Request, path: str):
    if redirect := _require_auth(request):
        return redirect

    file_path = library_meta.custom_cover_path(path)
    if not file_path.is_file():
        meta = metadata.book_metadata.get(path)
        file_path = metadata.book_metadata.cover_path(path)
        if meta is None or not meta.has_cover or not file_path.is_file():
            return Response(status_code=404)
    if not file_path.is_file():
        return Response(status_code=404)
    try:
        content = await asyncio.to_thread(file_path.read_bytes)
    except OSError:
        return Response(status_code=404)
    return Response(
        content=content,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )


def _edit_context(path: str, back: str) -> dict:
    meta = metadata.book_metadata.get(path)
    override = library_meta.get(path)
    return {
        "path": path,
        "back": back,
        "title": (override.title if override else None)
        or (meta.title if meta else None)
        or books.title_from_path(path),
        "author": (override.author if override else None)
        or (meta.author if meta else None)
        or "",
        "series": (override.series if override else None) or "",
        "series_index": override.series_index if override else None,
        "status": override.status if override else None,
        "status_options": _STATUS_OPTIONS,
        "has_preview": (override.has_custom_cover if override else False)
        or (meta.has_cover if meta else False),
    }


@app.get("/edit")
async def edit_form(request: Request, path: str, back: str = ""):
    if redirect := _require_auth(request):
        return redirect
    if not await _known_book_path(path):
        return Response("Книга не найдена", status_code=404)
    return templates.TemplateResponse(
        request,
        "edit_book.html",
        {"error": None, **_edit_context(path, back)},
    )


@app.post("/edit")
async def edit_submit(
    request: Request,
    path: str = Form(...),
    title: str = Form(""),
    author: str = Form(""),
    series: str = Form(""),
    series_index: str = Form(""),
    status: str = Form(""),
    back: str = Form(""),
    cover: UploadFile | None = File(None),
):
    if redirect := _require_auth(request):
        return redirect
    if not await _known_book_path(path):
        return Response("Книга не найдена", status_code=404)

    parsed_index: int | None = None
    if series.strip() and series_index.strip():
        try:
            parsed_index = max(1, int(series_index.strip()))
        except ValueError:
            parsed_index = None

    status_value = status if status in library_meta.STATUS_CHOICES else None
    library_meta.set_override(
        path,
        title=title.strip() or None,
        author=author.strip() or None,
        series=series.strip() or None,
        series_index=parsed_index,
        status=status_value,
    )

    cover_error = None
    if cover is not None and cover.filename:
        data = await cover.read(MAX_COVER_UPLOAD_BYTES + 1)
        if len(data) > MAX_COVER_UPLOAD_BYTES:
            cover_error = "Файл обложки больше 10 МБ — выберите файл поменьше"
        elif data and not library_meta.save_custom_cover(path, data):
            cover_error = "Не удалось сохранить обложку — файл не похож на картинку"

    books.invalidate_book_cache(path)
    if cover_error:
        return templates.TemplateResponse(
            request,
            "edit_book.html",
            {"error": cover_error, **_edit_context(path, back)},
        )
    return RedirectResponse(_back_url(back), status_code=303)


@app.get("/delete")
async def delete_confirm(
    request: Request,
    path: str,
    page: int = 1,
    q: str = "",
    author: str = "",
):
    if redirect := _require_auth(request):
        return redirect
    return templates.TemplateResponse(
        request,
        "delete.html",
        {
            "path": path,
            "name": _book_name(path),
            "page": max(1, page),
            "q": q,
            "author": author,
            "is_local": False,
            "error": None,
        },
    )


@app.post("/delete")
async def delete_submit(
    request: Request,
    path: str = Form(...),
    page: int = Form(1),
    q: str = Form(""),
    author: str = Form(""),
):
    if redirect := _require_auth(request):
        return redirect

    name = _book_name(path)
    try:
        await books.delete_book(path)
        progress.delete(path)
        metadata.book_metadata.delete(path)
        library_meta.delete_override(path)
    except YandexDiskError as exc:
        return templates.TemplateResponse(
            request,
            "delete.html",
            {
                "path": path,
                "name": name,
                "page": max(1, page),
                "q": q,
                "author": author,
                "is_local": False,
                "error": str(exc),
            },
            status_code=502,
        )

    return RedirectResponse(
        _library_url(
            page=max(1, page), q=q, author=author, deleted=name
        ),
        status_code=303,
    )


def _catalog_context(
    *,
    query: str = "",
    outcome: catalog.CatalogOutcome | None = None,
    error: str | None = None,
    job: catalog_jobs.CatalogJob | None = None,
) -> dict:
    return {
        "query": query,
        "outcome": outcome,
        "error": error,
        "job": job,
        "configuration_error": catalog.telegram_catalog.configuration_error(),
    }


@app.get("/catalog")
async def catalog_page(request: Request, job: str | None = None):
    if redirect := _require_auth(request):
        return redirect
    current_job = catalog_jobs.catalog_jobs.get(job) if job else None
    error = None
    if job and current_job is None:
        error = "Ход операции не найден. Повторите поиск."
    return templates.TemplateResponse(
        request,
        "catalog.html",
        _catalog_context(
            query=current_job.query if current_job else "",
            outcome=current_job.outcome if current_job else None,
            error=current_job.error if current_job else error,
            job=current_job,
        ),
    )


def _start_catalog_task(coroutine) -> None:
    task = asyncio.create_task(coroutine)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _run_catalog_job(job_id: str, operation) -> None:
    try:
        outcome = await operation()
        if outcome.imported_names:
            books.invalidate_list_cache()
        catalog_jobs.catalog_jobs.finish(job_id, outcome=outcome)
    except catalog.CatalogError as exc:
        catalog_jobs.catalog_jobs.finish(job_id, error=str(exc))
    except Exception:
        logger.exception("Unexpected catalog background failure")
        catalog_jobs.catalog_jobs.finish(
            job_id, error="Не удалось завершить операцию каталога"
        )


@app.post("/catalog/search")
async def catalog_search(request: Request, query: str = Form(...)):
    if redirect := _require_auth(request):
        return redirect

    job = catalog_jobs.catalog_jobs.create("search", query=query)
    _start_catalog_task(
        _run_catalog_job(job.id, lambda: catalog.telegram_catalog.search(query))
    )
    return RedirectResponse(f"/catalog?job={quote(job.id)}", status_code=303)


@app.post("/catalog/action")
async def catalog_action(request: Request, token: str = Form(...)):
    if redirect := _require_auth(request):
        return redirect

    job = catalog_jobs.catalog_jobs.create("action")
    _start_catalog_task(
        _run_catalog_job(job.id, lambda: catalog.telegram_catalog.activate(token))
    )
    return RedirectResponse(f"/catalog?job={quote(job.id)}", status_code=303)


@app.get("/download")
async def download(request: Request, path: str, fmt: str | None = None):
    if redirect := _require_auth(request):
        return redirect

    try:
        data = await books.download_book(path)
    except YandexDiskError as exc:
        return Response(f"Не удалось скачать файл: {exc}", status_code=502)

    name = path.rsplit("/", 1)[-1]
    base_name = name.rsplit(".", 1)[0] if "." in name else name

    if fmt in convert.TARGET_MIME_TYPES:
        try:
            data = await convert.convert_book(data, name, fmt)
        except convert.ConversionError as exc:
            return Response(f"Не удалось сконвертировать книгу: {exc}", status_code=502)
        ext = f".{fmt}"
        mime = convert.TARGET_MIME_TYPES[fmt]
        download_name = base_name + ext
    else:
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        mime = _MIME_TYPES.get(ext, "application/octet-stream")
        download_name = name

    encoded_name = quote(download_name)

    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": (
                f'attachment; filename="book{ext}"; filename*=UTF-8\'\'{encoded_name}'
            )
        },
    )


@app.get("/read")
async def read(request: Request, path: str, page: int | None = None, fs: int | None = None):
    if redirect := _require_auth(request):
        return redirect

    error = None
    book = None
    try:
        book = await books.get_book(path)
    except (
        YandexDiskError,
        convert.ConversionError,
        zipfile.BadZipFile,
        ET.ParseError,
    ) as exc:
        error = str(exc)

    if error:
        return templates.TemplateResponse(request, "reader.html", {"error": error})

    total = len(book["pages"])
    if page is None:
        page = progress.get_page(path) or 1
    page = max(1, min(page, total))
    progress.set_page(path, page)

    cookie_fs = request.cookies.get(FONT_SIZE_COOKIE)
    font_size = fs if fs is not None else int(cookie_fs) if cookie_fs else DEFAULT_FONT_SIZE
    font_size = max(MIN_FONT_SIZE, min(font_size, MAX_FONT_SIZE))

    response = templates.TemplateResponse(
        request,
        "reader.html",
        {
            "error": None,
            "title": book["title"],
            "path": path,
            "page": page,
            "total": total,
            "font_size": font_size,
            "min_font_size": MIN_FONT_SIZE,
            "max_font_size": MAX_FONT_SIZE,
            "paragraphs": book["pages"][page - 1],
        },
    )
    if fs is not None:
        response.set_cookie(
            FONT_SIZE_COOKIE,
            str(font_size),
            httponly=True,
            samesite="lax",
            secure=config.COOKIE_SECURE,
            max_age=auth.MAX_AGE_SECONDS,
        )
    return response
