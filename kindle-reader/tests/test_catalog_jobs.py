import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("YANDEX_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PASSWORD_HASH", "test-hash")
os.environ.setdefault("PASSWORD_SALT", "00" * 16)

from app import catalog, catalog_jobs  # noqa: E402


class CatalogJobStoreTests(unittest.TestCase):
    def test_working_job_survives_store_reload(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            first = catalog_jobs.CatalogJobStore(directory)
            created = first.create("search", query="Толстой")

            second = catalog_jobs.CatalogJobStore(directory)
            restored = second.get(created.id)

        self.assertIsNotNone(restored)
        self.assertEqual(restored.status, "working")
        self.assertEqual(restored.query, "Толстой")

    def test_finished_outcome_survives_store_reload(self):
        outcome = catalog.CatalogOutcome(
            entries=[
                catalog.CatalogEntry(
                    text="Результат",
                    actions=[catalog.CatalogAction(label="Выбрать", token="signed")],
                )
            ],
            imported_names=["Book.fb2"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            store = catalog_jobs.CatalogJobStore(directory)
            created = store.create("action")
            store.finish(created.id, outcome=outcome)

            restored = catalog_jobs.CatalogJobStore(directory).get(created.id)

        self.assertEqual(restored.status, "done")
        self.assertEqual(restored.outcome.imported_names, ["Book.fb2"])
        self.assertEqual(restored.outcome.entries[0].actions[0].token, "signed")

    def test_error_survives_store_reload(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = catalog_jobs.CatalogJobStore(Path(temporary))
            created = store.create("search")
            store.finish(created.id, error="Ошибка каталога")
            restored = store.get(created.id)

        self.assertEqual(restored.status, "error")
        self.assertEqual(restored.error, "Ошибка каталога")

    def test_rejects_invalid_job_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = catalog_jobs.CatalogJobStore(Path(temporary))
            self.assertIsNone(store.get("../../secret"))


if __name__ == "__main__":
    unittest.main()
