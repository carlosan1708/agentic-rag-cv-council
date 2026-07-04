"""Persistence of past analyses.

Two backends, selected automatically:
- GCS  - when the GCS_BUCKET env var is set (hosted deployments, e.g. Cloud Run,
  where the local filesystem is ephemeral). Records are JSON objects under
  history/{owner}/{id}.json.
- SQLite - otherwise (local use), stored under DATA_DIR.

Records are scoped by "owner". Locally the owner is the constant "local" so
history persists across restarts. On shared/hosted deployments set
HISTORY_SCOPE=session so each browser session only sees its own records.
"""

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from logger import logger

DEFAULT_OWNER = "local"

_FIELDS = ("id", "created_at", "job_snippet", "ats_score", "board_report", "minimal_changes", "final_cv", "cover_letter")


@dataclass
class AnalysisRecord:
    id: int
    created_at: str
    job_snippet: str
    ats_score: Optional[int]
    board_report: str
    minimal_changes: str
    final_cv: str
    cover_letter: str


def session_scoped() -> bool:
    """True when each browser session should only see its own history."""
    return os.getenv("HISTORY_SCOPE", "shared").lower() == "session"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


class SQLiteHistoryBackend:
    """Local persistence under DATA_DIR (default: ./data)."""

    def _connect(self) -> sqlite3.Connection:
        data_dir = Path(os.getenv("DATA_DIR", "data"))
        data_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(data_dir / "history.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL DEFAULT 'local',
                created_at TEXT NOT NULL,
                job_snippet TEXT NOT NULL DEFAULT '',
                ats_score INTEGER,
                board_report TEXT NOT NULL DEFAULT '',
                minimal_changes TEXT NOT NULL DEFAULT '',
                final_cv TEXT NOT NULL DEFAULT '',
                cover_letter TEXT NOT NULL DEFAULT ''
            )
            """)
        return conn

    def save(self, record: dict, owner: str) -> Optional[int]:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO analyses (owner, created_at, job_snippet, ats_score, board_report, "
                "minimal_changes, final_cv, cover_letter) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    owner,
                    record["created_at"],
                    record["job_snippet"],
                    record["ats_score"],
                    record["board_report"],
                    record["minimal_changes"],
                    record["final_cv"],
                    record["cover_letter"],
                ),
            )
            return cursor.lastrowid

    def list(self, owner: str, limit: int) -> List[AnalysisRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_FIELDS)} FROM analyses WHERE owner = ? ORDER BY id DESC LIMIT ?",
                (owner, limit),
            ).fetchall()
        return [AnalysisRecord(*row) for row in rows]

    def get(self, record_id: int, owner: str) -> Optional[AnalysisRecord]:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {', '.join(_FIELDS)} FROM analyses WHERE id = ? AND owner = ?",
                (record_id, owner),
            ).fetchone()
        return AnalysisRecord(*row) if row else None

    def delete(self, record_id: int, owner: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM analyses WHERE id = ? AND owner = ?", (record_id, owner))

    def delete_all(self, owner: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM analyses WHERE owner = ?", (owner,))


class GCSHistoryBackend:
    """Google Cloud Storage persistence: history/{owner}/{id}.json in GCS_BUCKET.

    Uses Application Default Credentials (automatic on Cloud Run; locally use
    `gcloud auth application-default login`).
    """

    def __init__(self, bucket_name: str, bucket=None):
        if bucket is None:
            from google.cloud import storage

            bucket = storage.Client().bucket(bucket_name)
        self._bucket = bucket

    @staticmethod
    def _blob_path(owner: str, record_id: int) -> str:
        return f"history/{owner}/{record_id}.json"

    def save(self, record: dict, owner: str) -> Optional[int]:
        record_id = time.time_ns()  # epoch ns: sortable ints, unique in practice
        while self._bucket.blob(self._blob_path(owner, record_id)).exists():
            record_id += 1
        record = dict(record, id=record_id)
        blob = self._bucket.blob(self._blob_path(owner, record_id))
        blob.upload_from_string(json.dumps(record), content_type="application/json")
        return record_id

    def _ids(self, owner: str) -> List[int]:
        prefix = f"history/{owner}/"
        ids = []
        for blob in self._bucket.list_blobs(prefix=prefix):
            stem = blob.name[len(prefix) :].removesuffix(".json")
            if stem.isdigit():
                ids.append(int(stem))
        return sorted(ids, reverse=True)

    def list(self, owner: str, limit: int) -> List[AnalysisRecord]:
        return [r for r in (self.get(i, owner) for i in self._ids(owner)[:limit]) if r]

    def get(self, record_id: int, owner: str) -> Optional[AnalysisRecord]:
        blob = self._bucket.blob(self._blob_path(owner, record_id))
        if not blob.exists():
            return None
        data = json.loads(blob.download_as_text())
        return AnalysisRecord(**{f: data.get(f) for f in _FIELDS})

    def delete(self, record_id: int, owner: str) -> None:
        blob = self._bucket.blob(self._blob_path(owner, record_id))
        if blob.exists():
            blob.delete()

    def delete_all(self, owner: str) -> None:
        for blob in list(self._bucket.list_blobs(prefix=f"history/{owner}/")):
            blob.delete()


_backend = None
_backend_key = None


def _get_backend():
    """Returns the active backend, rebuilding it if the env configuration changed."""
    global _backend, _backend_key
    key = (os.getenv("GCS_BUCKET", ""), os.getenv("DATA_DIR", ""))
    if _backend is None or key != _backend_key:
        bucket_name = key[0]
        if bucket_name:
            logger.info(f"History backend: GCS bucket '{bucket_name}'")
            _backend = GCSHistoryBackend(bucket_name)
        else:
            _backend = SQLiteHistoryBackend()
        _backend_key = key
    return _backend


class HistoryService:
    @staticmethod
    def save_analysis(
        job_description: str,
        board_report: str,
        minimal_changes: str,
        final_cv: str,
        cover_letter: str = "",
        ats_score: Optional[int] = None,
        owner: str = DEFAULT_OWNER,
    ) -> Optional[int]:
        """Persists a completed analysis. Returns the new record id, or None on failure."""
        try:
            record = {
                "created_at": _now(),
                "job_snippet": " ".join(job_description.split())[:160],
                "ats_score": ats_score,
                "board_report": board_report,
                "minimal_changes": minimal_changes,
                "final_cv": final_cv,
                "cover_letter": cover_letter,
            }
            record_id = _get_backend().save(record, owner)
            logger.info(f"Saved analysis #{record_id} to history.")
            return record_id
        except Exception as e:
            logger.error(f"Failed to save analysis to history: {e}")
            return None

    @staticmethod
    def list_analyses(limit: int = 20, owner: str = DEFAULT_OWNER) -> List[AnalysisRecord]:
        try:
            return _get_backend().list(owner, limit)
        except Exception as e:
            logger.error(f"Failed to list analyses: {e}")
            return []

    @staticmethod
    def get_analysis(record_id: int, owner: str = DEFAULT_OWNER) -> Optional[AnalysisRecord]:
        try:
            return _get_backend().get(record_id, owner)
        except Exception as e:
            logger.error(f"Failed to load analysis #{record_id}: {e}")
            return None

    @staticmethod
    def delete_analysis(record_id: int, owner: str = DEFAULT_OWNER) -> bool:
        try:
            _get_backend().delete(record_id, owner)
            logger.info(f"Deleted analysis #{record_id} from history.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete analysis #{record_id}: {e}")
            return False

    @staticmethod
    def delete_all(owner: str = DEFAULT_OWNER) -> bool:
        """One-click 'delete my data'."""
        try:
            _get_backend().delete_all(owner)
            logger.info("Deleted all analyses from history.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete history: {e}")
            return False
