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


async def convert_book(data: bytes, source_name: str, target_ext: str) -> bytes:
    """Прогнать книгу через ebook-convert (Calibre) в формат target_ext ('mobi'/'azw3')."""
    if source_name.lower().endswith(".txt"):
        source_ext = ".txt"
    else:
        data = unwrap_zip(data)
        source_ext = ".fb2"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src = tmp / f"book{source_ext}"
        dst = tmp / f"book.{target_ext}"
        src.write_bytes(data)

        proc = await asyncio.create_subprocess_exec(
            "ebook-convert",
            str(src),
            str(dst),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0 or not dst.exists():
            message = stderr.decode("utf-8", errors="replace").strip()
            raise ConversionError(message[-2000:] or "ebook-convert завершился с ошибкой")

        return dst.read_bytes()
