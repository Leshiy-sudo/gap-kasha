Paragraph = tuple[str, bool]
Page = list[Paragraph]


def paginate(paragraphs: list[Paragraph], chars_per_page: int) -> list[Page]:
    """Разбить параграфы на страницы примерно по chars_per_page символов,
    не разрывая параграфы, кроме случаев, когда параграф сам больше страницы."""
    pages: list[Page] = []
    current: Page = []
    current_len = 0

    for text, is_heading in paragraphs:
        length = len(text) + 1

        if current and current_len + length > chars_per_page:
            pages.append(current)
            current, current_len = [], 0

        if length > chars_per_page:
            start = 0
            while start < len(text):
                if current:
                    pages.append(current)
                    current, current_len = [], 0
                chunk = text[start : start + chars_per_page]
                pages.append([(chunk, is_heading)])
                start += chars_per_page
            continue

        current.append((text, is_heading))
        current_len += length

    if current:
        pages.append(current)

    return pages or [[]]
