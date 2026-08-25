import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import catalog, config, local_library  # noqa: E402


class FakeButton:
    def __init__(self, text: str, url: str | None = None):
        self.text = text
        self.url = url


class FakeMessage:
    def __init__(
        self,
        message_id: int,
        *,
        text: str = "",
        buttons=None,
        filename: str | None = None,
    ):
        self.id = message_id
        self.raw_text = text
        self.buttons = buttons
        self.file = SimpleNamespace(name=filename) if filename else None
        self.edit_date = None

    async def get_buttons(self):
        return self.buttons


class FakeClient:
    def __init__(self, data: bytes = b"book-data"):
        self.data = data
        self.downloaded = []

    async def download_media(self, message, file):
        self.downloaded.append((message.id, file))
        return self.data


class ActionCodecTests(unittest.TestCase):
    def test_round_trip(self):
        codec = catalog.ActionCodec("secret")
        self.assertEqual(
            codec.decode(codec.encode_button(123, 2, 1)),
            catalog.ActionTarget(kind="button", message_id=123, row=2, column=1),
        )

    def test_command_round_trip(self):
        codec = catalog.ActionCodec("secret")
        self.assertEqual(
            codec.decode(codec.encode_command("/download175105")),
            catalog.ActionTarget(kind="command", command="/download175105"),
        )

    def test_rejects_tampered_token(self):
        codec = catalog.ActionCodec("secret")
        token = codec.encode_button(123, 2, 1)
        with self.assertRaisesRegex(catalog.CatalogError, "устарело"):
            codec.decode(token + "x")


class CatalogOutcomeTests(unittest.IsolatedAsyncioTestCase):
    async def test_exposes_callback_buttons_as_signed_actions(self):
        service = catalog.TelegramCatalog()
        message = FakeMessage(
            77,
            text="Выберите формат",
            buttons=[
                [
                    FakeButton("FB2"),
                    FakeButton("EPUB"),
                    FakeButton("MOBI"),
                    FakeButton("Сайт", "https://example.com"),
                ]
            ],
        )

        outcome = await service._build_outcome(
            FakeClient(), [message], import_documents=False
        )

        self.assertEqual(outcome.entries[0].text, "Выберите формат")
        self.assertEqual(
            [item.label for item in outcome.entries[0].actions],
            ["FB2 — добавить в библиотеку"],
        )
        self.assertEqual(
            service._actions.decode(outcome.entries[0].actions[0].token),
            catalog.ActionTarget(kind="button", message_id=77, row=0, column=0),
        )

    async def test_exposes_text_download_commands_as_book_actions(self):
        service = catalog.TelegramCatalog()
        message = FakeMessage(
            78,
            text=(
                "Найдено: 2 книги\n\n"
                "Война и мир. Том 1 - ru\n"
                "Лев Толстой\n"
                "Скачать книгу: /download175105\n\n"
                "Война и мир. Том 2 - ru\n"
                "Лев Толстой\n"
                "Скачать книгу: /download175143"
            ),
        )

        outcome = await service._build_outcome(
            FakeClient(), [message], import_documents=False
        )

        self.assertEqual(
            [action.label for action in outcome.entries[0].actions],
            [
                "Выбрать: Война и мир. Том 1 - ru",
                "Выбрать: Война и мир. Том 2 - ru",
            ],
        )
        self.assertEqual(
            service._actions.decode(outcome.entries[0].actions[0].token),
            catalog.ActionTarget(kind="command", command="/download175105"),
        )

    async def test_hides_unsupported_text_format_commands(self):
        service = catalog.TelegramCatalog()
        message = FakeMessage(
            79,
            text="/fb2175105\n/epub175105\n/mobi175105",
        )

        outcome = await service._build_outcome(
            FakeClient(), [message], import_documents=False
        )

        self.assertEqual(
            [action.label for action in outcome.entries[0].actions],
            ["FB2 — добавить в библиотеку"],
        )
        self.assertEqual(
            service._actions.decode(outcome.entries[0].actions[0].token),
            catalog.ActionTarget(kind="command", command="/fb2175105"),
        )

    async def test_downloads_and_uploads_supported_document(self):
        service = catalog.TelegramCatalog()
        client = FakeClient()
        message = FakeMessage(88, filename="Book.FB2")
        upload = AsyncMock(return_value="disk:/Книги/Book.FB2")

        with patch.object(local_library, "save_book", upload):
            outcome = await service._build_outcome(
                client, [message], import_documents=True
            )

        upload.assert_awaited_once_with(b"book-data", "Book.FB2")
        self.assertEqual(client.downloaded, [(88, bytes)])
        self.assertEqual(outcome.imported_names, ["Book.FB2"])

    async def test_reports_existing_document(self):
        service = catalog.TelegramCatalog()
        message = FakeMessage(89, filename="Book.fb2")
        upload = AsyncMock(
            side_effect=local_library.LocalLibraryConflictError("already exists")
        )

        with patch.object(local_library, "save_book", upload):
            outcome = await service._build_outcome(
                FakeClient(), [message], import_documents=True
            )

        self.assertEqual(outcome.existing_names, ["Book.fb2"])

    async def test_does_not_download_unsupported_document(self):
        service = catalog.TelegramCatalog()
        client = FakeClient()
        message = FakeMessage(90, filename="Book.epub")

        outcome = await service._build_outcome(
            client, [message], import_documents=True
        )

        self.assertEqual(client.downloaded, [])
        self.assertEqual(outcome.unsupported_names, ["Book.epub"])

    async def test_reports_storage_failure_as_catalog_error(self):
        service = catalog.TelegramCatalog()
        message = FakeMessage(91, filename="Book.fb2")
        upload = AsyncMock(side_effect=local_library.LocalLibraryError("failure"))

        with (
            patch.object(local_library, "save_book", upload),
            self.assertRaisesRegex(catalog.CatalogError, "сохранить"),
        ):
            await service._build_outcome(
                FakeClient(), [message], import_documents=True
            )


class ConfigurationTests(unittest.TestCase):
    def test_reports_missing_api_credentials(self):
        service = catalog.TelegramCatalog()
        with (
            patch.object(config, "TELEGRAM_API_ID", 0),
            patch.object(config, "TELEGRAM_API_HASH", ""),
        ):
            self.assertIn("не настроен", service.configuration_error())


if __name__ == "__main__":
    unittest.main()
