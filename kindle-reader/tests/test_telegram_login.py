import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import telegram_login


class TelegramLoginConfigurationTests(unittest.TestCase):
    def test_prompts_and_saves_missing_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            env_path = Path(temporary) / ".env"
            env_path.write_text("YANDEX_TOKEN=test\n", encoding="utf-8")
            with (
                patch.object(telegram_login, "ENV_PATH", env_path),
                patch.object(telegram_login, "PROJECT_DIR", Path(temporary)),
                patch.dict(
                    os.environ,
                    {
                        "TELEGRAM_API_ID": "",
                        "TELEGRAM_API_HASH": "",
                        "TELEGRAM_SESSION_PATH": "",
                    },
                ),
                patch("builtins.input", return_value="123456"),
                patch.object(
                    telegram_login.getpass,
                    "getpass",
                    return_value="a" * 32,
                ),
            ):
                api_id, api_hash, session_path = telegram_login._credentials()

            self.assertEqual(api_id, 123456)
            self.assertEqual(api_hash, "a" * 32)
            self.assertEqual(session_path, Path(temporary) / "data/telegram_catalog")
            saved = env_path.read_text(encoding="utf-8")
            self.assertIn("TELEGRAM_API_ID=123456", saved)
            self.assertIn(f"TELEGRAM_API_HASH={'a' * 32}", saved)

    def test_rejects_invalid_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            env_path = Path(temporary) / ".env"
            env_path.write_text("YANDEX_TOKEN=test\n", encoding="utf-8")
            with (
                patch.object(telegram_login, "ENV_PATH", env_path),
                patch.dict(
                    os.environ,
                    {"TELEGRAM_API_ID": "", "TELEGRAM_API_HASH": ""},
                ),
                patch("builtins.input", return_value="123456"),
                patch.object(
                    telegram_login.getpass,
                    "getpass",
                    return_value="not-a-hash",
                ),
                self.assertRaisesRegex(SystemExit, "32"),
            ):
                telegram_login._credentials()


if __name__ == "__main__":
    unittest.main()
