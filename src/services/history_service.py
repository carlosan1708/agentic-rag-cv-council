"""Local persistence of past analyses (SQLite, anonymous, stored under DATA_DIR)."""

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from logger import logger


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


def _db_path() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "history.db"


class HistoryService:
    @staticmethod
    def _connect() -> sqlite3.Connection:
        conn = sqlite3.connect(_db_path())
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    @staticmethod
    def save_analysis(
        job_description: str,
        board_report: str,
        minimal_changes: str,
        final_cv: str,
        cover_letter: str = "",
        ats_score: Optional[int] = None,
    ) -> Optional[int]:
        """Persists a completed analysis. Returns the new record id, or None on failure."""
        try:
            snippet = " ".join(job_description.split())[:160]
            with HistoryService._connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO analyses (created_at, job_snippet, ats_score, board_report, "
                    "minimal_changes, final_cv, cover_letter) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                        snippet,
                        ats_score,
                        board_report,
                        minimal_changes,
                        final_cv,
                        cover_letter,
                    ),
                )
                logger.info(f"Saved analysis #{cursor.lastrowid} to history.")
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save analysis to history: {e}")
            return None

    @staticmethod
    def list_analyses(limit: int = 20) -> List[AnalysisRecord]:
        try:
            with HistoryService._connect() as conn:
                rows = conn.execute(
                    "SELECT id, created_at, job_snippet, ats_score, board_report, minimal_changes, "
                    "final_cv, cover_letter FROM analyses ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [AnalysisRecord(*row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to list analyses: {e}")
            return []

    @staticmethod
    def get_analysis(record_id: int) -> Optional[AnalysisRecord]:
        try:
            with HistoryService._connect() as conn:
                row = conn.execute(
                    "SELECT id, created_at, job_snippet, ats_score, board_report, minimal_changes, "
                    "final_cv, cover_letter FROM analyses WHERE id = ?",
                    (record_id,),
                ).fetchone()
            return AnalysisRecord(*row) if row else None
        except Exception as e:
            logger.error(f"Failed to load analysis #{record_id}: {e}")
            return None

    @staticmethod
    def delete_analysis(record_id: int) -> bool:
        try:
            with HistoryService._connect() as conn:
                conn.execute("DELETE FROM analyses WHERE id = ?", (record_id,))
            logger.info(f"Deleted analysis #{record_id} from history.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete analysis #{record_id}: {e}")
            return False

    @staticmethod
    def delete_all() -> bool:
        """One-click 'delete my data'."""
        try:
            with HistoryService._connect() as conn:
                conn.execute("DELETE FROM analyses")
            logger.info("Deleted all analyses from history.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete history: {e}")
            return False
