import asyncio
import logging
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
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
    local_library,
    progress,
)
from .yandex_disk import YandexDiskError

_MIME_TYPES = {
    ".fb2": "application/x-fictionbook+xml",
    ".zip": "application/zip",
    ".txt": "text/plain; charset=utf-8",
}

FONT_SIZE_COOKIE = "font_size"
DEFAULT_FONT_SIZE = 2
MIN_FONT_SIZE = 1
MAX_FONT_SIZE = 5

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger("kindle_reader.web")
_background_tasks: set[asyncio.Task] = set()


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
async def library(request: Request):
    if redirect := _require_auth(request):
        return redirect

    error = None
    items = []
    try:
        items = await books.get_book_list()
    except YandexDiskError as exc:
        error = str(exc)

    saved_pages = progress.get_all()

    return templates.TemplateResponse(
        request, "library.html", {"items": items, "error": error, "saved_pages": saved_pages}
    )


@app.get("/refresh")
async def refresh(request: Request):
    if redirect := _require_auth(request):
        return redirect
    books.invalidate_list_cache()
    return RedirectResponse("/", status_code=303)


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
    except (YandexDiskError, local_library.LocalLibraryError) as exc:
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
    except (YandexDiskError, local_library.LocalLibraryError) as exc:
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
