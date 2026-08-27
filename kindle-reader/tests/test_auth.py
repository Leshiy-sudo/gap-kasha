import json
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import auth  # noqa: E402
from app.pwhash import hash_password  # noqa: E402


class MultiUserAuthTests(unittest.TestCase):
    def setUp(self):
        self.salt_one = bytes.fromhex("01" * 16)
        self.salt_two = bytes.fromhex("02" * 16)
        users = {
            "talgat": {
                "name": "Талгат",
                "salt": self.salt_one.hex(),
                "hash": hash_password("first-password", self.salt_one),
            },
            "igor": {
                "name": "Игорь",
                "salt": self.salt_two.hex(),
                "hash": hash_password("second-password", self.salt_two),
            },
        }
        self.config_patch = patch.object(auth.config, "AUTH_USERS_JSON", json.dumps(users))
        self.config_patch.start()
        auth.configured_users.cache_clear()
        self.addCleanup(self.config_patch.stop)
        self.addCleanup(auth.configured_users.cache_clear)

    def test_each_user_has_own_password(self):
        self.assertTrue(auth.verify_password("talgat", "first-password"))
        self.assertTrue(auth.verify_password("igor", "second-password"))
        self.assertFalse(auth.verify_password("talgat", "second-password"))
        self.assertFalse(auth.verify_password("igor", "first-password"))

    def test_session_identifies_user(self):
        request = Mock()
        request.cookies = {auth.COOKIE_NAME: auth.make_session_cookie("igor")}
        self.assertEqual(auth.current_user_id(request), "igor")
        self.assertEqual(auth.current_user_name(request), "Игорь")

    def test_old_session_is_assigned_to_default_user(self):
        request = Mock()
        request.cookies = {auth.COOKIE_NAME: auth._serializer.dumps({"auth": True})}
        self.assertEqual(auth.current_user_id(request), "talgat")


if __name__ == "__main__":
    unittest.main()
