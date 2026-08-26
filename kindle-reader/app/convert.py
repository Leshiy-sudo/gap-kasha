import asyncio
import tempfile
from pathlib import Path

from .parsers.fb2 import unwrap_zip

TARGET_MIME_TYPES = {
    "mobi": "application/x-mobipocket-ebook",
    "azw3": "application/vnd.amazon.ebook",
}


class ConversionError(RuntimeError):
    pass


def _source_extension(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".txt"):
        return ".txt"
    if lower.endswith(".epub"):
        return ".epub"
    if lower.endswith(".mobi"):
        return ".mobi"
    return ".fb2"


async def convert_book(data: bytes, source_name: str, target_ext: str) -> bytes:
    """Прогнать книгу через ebook-convert (Calibre) в формат target_ext ('mobi'/'azw3')."""
    source_ext = _source_extension(source_name)
    if source_ext == ".fb2":
        data = unwrap_zip(data)
    return await _run_convert(data, source_ext, target_ext)


async def convert_to_fb2(data: bytes, source_name: str) -> bytes:
    """Конвертировать EPUB/MOBI в FB2 для чтения в браузере."""
    return await _run_convert(data, _source_extension(source_name), "fb2")


async def _run_convert(data: bytes, source_ext: str, target_ext: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src = tmp / f"book{source_ext}"
        dst = tmp / f"book.{target_ext}"
        src.write_bytes(data)

        try:
            proc = await asyncio.create_subprocess_exec(
                "ebook-convert",
                str(src),
                str(dst),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise ConversionError("Calibre (ebook-convert) не установлен") from exc

        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.communicate()
            raise ConversionError("Конвертация книги заняла слишком много времени") from exc

        if proc.returncode != 0 or not dst.exists():
            message = stderr.decode("utf-8", errors="replace").strip()
            raise ConversionError(message[-2000:] or "ebook-convert завершился с ошибкой")

        return dst.read_bytes()
