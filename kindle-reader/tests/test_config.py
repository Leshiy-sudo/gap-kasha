import os
import unittest

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import config  # noqa: E402


class TelegramSourceConfigTests(unittest.TestCase):
    def test_default_catalog_bot_is_configured(self):
        self.assertEqual(
            config.DEFAULT_TELEGRAM_SOURCE_BOT,
            "flibustafreebookbot",
        )

    def test_catalog_bot_name_has_no_telegram_prefix(self):
        self.assertNotEqual(config.TELEGRAM_SOURCE_BOT, "")
        self.assertNotIn("@", config.TELEGRAM_SOURCE_BOT)
        self.assertNotIn("t.me/", config.TELEGRAM_SOURCE_BOT)


if __name__ == "__main__":
    unittest.main()
