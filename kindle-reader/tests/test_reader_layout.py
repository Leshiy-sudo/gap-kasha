import os
import unittest

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import main  # noqa: E402


class ReaderLayoutTests(unittest.TestCase):
    def test_renders_compact_single_toolbar(self):
        template = main.templates.get_template("reader.html")
        html = template.render(
            request=None,
            error=None,
            title="Книга",
            path="local:/Book.fb2",
            page=2,
            total=10,
            font_size=2,
            min_font_size=1,
            max_font_size=5,
            paragraphs=[("Текст", False)],
        )

        self.assertEqual(html.count('class="reader-toolbar"'), 1)
        self.assertIn("← Книги", html)
        self.assertIn(">Скачать</a>", html)
        self.assertIn(">Kindle</a>", html)
        self.assertIn('class="reader-nav-bottom"', html)
        self.assertNotIn("Скачать (Kindle)", html)


if __name__ == "__main__":
    unittest.main()
