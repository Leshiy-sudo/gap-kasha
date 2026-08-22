import re

ENCODINGS = ("utf-8-sig", "utf-8", "cp1251", "latin-1")


def parse_txt(data: bytes) -> tuple[str | None, list[tuple[str, bool]]]:
    """Вернуть (заголовок, параграфы). Заголовка у txt нет — берётся из имени файла."""
    text = None
    for encoding in ENCODINGS:
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = data.decode("utf-8", errors="replace")

    blocks = re.split(r"\n\s*\n", text.strip())
    if len(blocks) <= 1:
        blocks = text.split("\n")

    paragraphs = [(block.strip(), False) for block in blocks if block.strip()]
    return None, paragraphs
