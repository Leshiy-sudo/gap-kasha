import io
import xml.etree.ElementTree as ET
import zipfile

# Элементы, внутрь которых нужно заходить в поисках параграфов
_CONTAINER_TAGS = {"section", "body", "epigraph", "cite", "poem", "stanza", "annotation"}


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
