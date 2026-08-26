import base64
import binascii
import io
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass

# Элементы, внутрь которых нужно заходить в поисках параграфов
_CONTAINER_TAGS = {"section", "body", "epigraph", "cite", "poem", "stanza", "annotation"}


@dataclass(frozen=True)
class FB2Metadata:
    title: str | None
    author: str | None
    cover_bytes: bytes | None


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _walk(element: ET.Element, paragraphs: list[tuple[str, bool]]) -> None:
    for child in element:
        local = _local_name(child.tag)
        if local == "p":
            text = "".join(child.itertext()).strip()
            if text:
                paragraphs.append((text, False))
        elif local == "title":
            text = "".join(child.itertext()).strip()
            if text:
                paragraphs.append((text, True))
        elif local == "empty-line":
            paragraphs.append(("", False))
        elif local in _CONTAINER_TAGS:
            _walk(child, paragraphs)


def unwrap_zip(data: bytes) -> bytes:
    """Если это .fb2.zip — вернуть содержимое .fb2 изнутри, иначе данные как есть."""
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith(".fb2")]
            if not names:
                names = archive.namelist()
            if not names:
                raise zipfile.BadZipFile("Архив .fb2.zip не содержит файлов")
            return archive.read(names[0])
    return data


def parse_fb2(data: bytes) -> tuple[str | None, list[tuple[str, bool]]]:
    """Вернуть (заголовок, параграфы) из содержимого .fb2 или .fb2.zip."""
    data = unwrap_zip(data)
    root = ET.fromstring(data)

    title = None
    for element in root.iter():
        if _local_name(element.tag) == "book-title":
            title = "".join(element.itertext()).strip()
            break

    bodies = [child for child in root if _local_name(child.tag) == "body"]
    main_bodies = [b for b in bodies if b.attrib.get("name") != "notes"] or bodies

    paragraphs: list[tuple[str, bool]] = []
    for body in main_bodies:
        _walk(body, paragraphs)

    return title, paragraphs


def _href(element: ET.Element) -> str | None:
    for key, value in element.attrib.items():
        if key.endswith("href"):
            return value
    return None


def _author_name(author_element: ET.Element) -> str | None:
    parts = []
    for child in author_element:
        if _local_name(child.tag) in ("first-name", "middle-name", "last-name", "nickname"):
            text = "".join(child.itertext()).strip()
            if text:
                parts.append(text)
    return " ".join(parts) or None


def _leading_cover_binary_id(root: ET.Element) -> str | None:
    """Распознать первую одиночную картинку как обложку после конвертации."""
    bodies = [child for child in root if _local_name(child.tag) == "body"]
    main_bodies = [body for body in bodies if body.attrib.get("name") != "notes"] or bodies
    if not main_bodies:
        return None

    node = main_bodies[0]
    while True:
        first = next(
            (child for child in node if _local_name(child.tag) in ("section", "p")),
            None,
        )
        if first is None:
            return None
        if _local_name(first.tag) == "section":
            node = first
            continue
        if "".join(first.itertext()).strip():
            return None
        image = next(
            (child for child in first if _local_name(child.tag) == "image"), None
        )
        if image is None:
            return None
        href = _href(image)
        return href.lstrip("#") if href else None


def parse_fb2_metadata(data: bytes) -> FB2Metadata:
    """Извлечь название, автора и обложку из FB2/FB2.ZIP."""
    root = ET.fromstring(unwrap_zip(data))

    binaries: dict[str, bytes] = {}
    for element in root:
        if _local_name(element.tag) != "binary":
            continue
        binary_id = element.attrib.get("id")
        if not binary_id or not element.text:
            continue
        try:
            binaries[binary_id] = base64.b64decode(element.text, validate=False)
        except (ValueError, binascii.Error):
            continue

    title: str | None = None
    author: str | None = None
    cover_bytes: bytes | None = None
    for element in root.iter():
        if _local_name(element.tag) != "title-info":
            continue
        for child in element:
            local = _local_name(child.tag)
            if local == "book-title" and title is None:
                title = "".join(child.itertext()).strip() or None
            elif local == "author" and author is None:
                author = _author_name(child)
            elif local == "coverpage" and cover_bytes is None:
                image = next(
                    (item for item in child if _local_name(item.tag) == "image"),
                    None,
                )
                href = _href(image) if image is not None else None
                if href:
                    cover_bytes = binaries.get(href.lstrip("#"))
        break

    if cover_bytes is None:
        binary_id = _leading_cover_binary_id(root)
        if binary_id:
            cover_bytes = binaries.get(binary_id)

    return FB2Metadata(title=title, author=author, cover_bytes=cover_bytes)
