BOOK_SUFFIXES = (".fb2.zip", ".fb2", ".epub", ".mobi", ".txt")

# Формат приходит как слово в кнопках Telegram, поэтому составной .fb2.zip
# здесь не нужен: это архивированный вариант FB2, а не отдельный формат.
FORMAT_KEYWORDS = frozenset({"fb2", "txt", "epub", "mobi"})
