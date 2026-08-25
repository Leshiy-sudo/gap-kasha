from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from . import catalog, config

_JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,64}$")


@dataclass(frozen=True)
class CatalogJob:
    id: str
    kind: str
    status: str
    query: str
    created_at: float
    updated_at: float
    outcome: catalog.CatalogOutcome | None = None
    error: str | None = None

    @property
    def progress_message(self) -> str:
        if self.kind == "search":
            return "Идёт поиск книг в Telegram…"
        return "Каталог получает и сохраняет книгу…"


class CatalogJobStore:
    def __init__(self, directory: Path | None = None):
        self._directory = directory

    @property
    def directory(self) -> Path:
        return self._directory or config.CATALOG_JOBS_PATH

    def _ensure_directory(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.directory.chmod(0o700)

    def _path(self, job_id: str) -> Path:
        if not _JOB_ID_PATTERN.fullmatch(job_id):
            raise ValueError("Некорректный номер операции")
        return self.directory / f"{job_id}.json"

    @staticmethod
    def _outcome_to_dict(outcome: catalog.CatalogOutcome) -> dict:
        return {
            "entries": [
                {
                    "text": entry.text,
                    "document_name": entry.document_name,
                    "actions": [
                        {"label": action.label, "token": action.token}
                        for action in entry.actions
                    ],
                }
                for entry in outcome.entries
            ],
            "imported_names": outcome.imported_names,
            "existing_names": outcome.existing_names,
            "unsupported_names": outcome.unsupported_names,
        }

    @staticmethod
    def _outcome_from_dict(value: dict | None) -> catalog.CatalogOutcome | None:
        if value is None:
            return None
        return catalog.CatalogOutcome(
            entries=[
                catalog.CatalogEntry(
                    text=str(entry.get("text", "")),
                    document_name=entry.get("document_name"),
                    actions=[
                        catalog.CatalogAction(
                            label=str(action["label"]), token=str(action["token"])
                        )
                        for action in entry.get("actions", [])
                    ],
                )
                for entry in value.get("entries", [])
            ],
            imported_names=[str(name) for name in value.get("imported_names", [])],
            existing_names=[str(name) for name in value.get("existing_names", [])],
            unsupported_names=[
                str(name) for name in value.get("unsupported_names", [])
            ],
        )

    def _write(self, job: CatalogJob) -> None:
        self._ensure_directory()
        path = self._path(job.id)
        temporary = path.with_suffix(".tmp")
        payload = {
            "id": job.id,
            "kind": job.kind,
            "status": job.status,
            "query": job.query,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "outcome": (
                self._outcome_to_dict(job.outcome) if job.outcome is not None else None
            ),
            "error": job.error,
        }
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        temporary.chmod(0o600)
        temporary.replace(path)
        path.chmod(0o600)

    def create(self, kind: str, *, query: str = "") -> CatalogJob:
        self.cleanup()
        now = time.time()
        job = CatalogJob(
            id=secrets.token_urlsafe(18),
            kind=kind,
            status="working",
            query=query,
            created_at=now,
            updated_at=now,
        )
        self._write(job)
        return job

    def finish(
        self,
        job_id: str,
        *,
        outcome: catalog.CatalogOutcome | None = None,
        error: str | None = None,
    ) -> CatalogJob:
        current = self.get(job_id)
        if current is None:
            raise ValueError("Операция не найдена")
        job = CatalogJob(
            id=current.id,
            kind=current.kind,
            status="error" if error else "done",
            query=current.query,
            created_at=current.created_at,
            updated_at=time.time(),
            outcome=outcome,
            error=error,
        )
        self._write(job)
        return job

    def get(self, job_id: str) -> CatalogJob | None:
        try:
            path = self._path(job_id)
            payload = json.loads(path.read_text(encoding="utf-8"))
            return CatalogJob(
                id=str(payload["id"]),
                kind=str(payload["kind"]),
                status=str(payload["status"]),
                query=str(payload.get("query", "")),
                created_at=float(payload["created_at"]),
                updated_at=float(payload["updated_at"]),
                outcome=self._outcome_from_dict(payload.get("outcome")),
                error=payload.get("error"),
            )
        except (FileNotFoundError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def cleanup(self) -> None:
        self._ensure_directory()
        cutoff = time.time() - config.CATALOG_JOB_TTL_SECONDS
        for path in self.directory.glob("*.json"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                continue


catalog_jobs = CatalogJobStore()
