"""Сгенерировать PASSWORD_HASH и PASSWORD_SALT для .env.

Использование:
    python scripts/hash_password.py "мой-пароль"
"""

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pwhash import hash_password  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print('Использование: python scripts/hash_password.py "мой-пароль"')
        raise SystemExit(1)

    password = sys.argv[1]
    salt = secrets.token_bytes(16)
    digest = hash_password(password, salt)

    print(f"PASSWORD_HASH={digest}")
    print(f"PASSWORD_SALT={salt.hex()}")


if __name__ == "__main__":
    main()
