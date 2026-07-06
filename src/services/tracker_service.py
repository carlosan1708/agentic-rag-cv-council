"""Job application tracker: which jobs you applied to, with the exact CV version used.

Storage follows the history/auth pattern: SQLite locally, GCS objects
(applications/{owner}/{id}.json) when GCS_BUCKET is set. Records are scoped by
the same owner id as the analysis history.
"""

import json
import os
import re
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from logger import logger

STATUSES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]

# Statuses that count as "the application is still in play"
ACTIVE_STATUSES = {"Applied", "Interviewing"}
# Statuses that mean the company responded
RESPONDED_STATUSES = {"Interviewing", "Offer", "Rejected"}

STATUS_ICONS = {
    "Saved": "📝",
    "Applied": "📮",
    "Interviewing": "🎤",
    "Offer": "🏆",
    "Rejected": "❌",
}

# Timeline entry types for information gathered during the application process
EVENT_TYPES = ["Note", "Interview", "Recruiter call", "Assessment", "Feedback", "Follow-up", "Offer details"]

EVENT_ICONS = {
    "Note": "🗒️",
    "Interview": "🎤",
    "Recruiter call": "📞",
    "Assessment": "🧪",
    "Feedback": "💬",
    "Follow-up": "✉️",
    "Offer details": "🏆",
    "Status change": "🔁",
}

_FIELDS = (
    "id",
    "created_at",
    "updated_at",
    "company",
    "job_title",
    "status",
    "ats_score",
    "job_snippet",
    "cv_markdown",
    "cover_letter",
    "notes",
    "events",
)


@dataclass
class ApplicationRecord:
    id: int
    created_at: str
    updated_at: str
    company: str
    job_title: str
    status: str
    ats_score: Optional[int]
    job_snippet: str = ""
    cv_markdown: str = ""
    cover_letter: str = ""
    notes: str = ""
    events: list = field(default_factory=list)  # timeline: [{id, created_at, type, content}]


@dataclass
class TrackerStats:
    total: int = 0
    active: int = 0
    interviews: int = 0
    offers: int = 0
    response_rate: Optional[float] = None  # 0.0 - 1.0, None when nothing applied yet
    avg_ats: Optional[float] = None
    by_status: dict = field(default_factory=dict)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


STALE_AFTER_DAYS = 7

FOLLOW_UP_TEMPLATE = """Subject: Following up on my {job_title} application

Hi {company} team,

I applied for the {job_title} position on {applied_date} and wanted to check in on the status of
my application. I remain very interested in the role and would be happy to provide any additional
information that would help.

Thank you for your time!

Best regards"""


def format_timeline(record: "ApplicationRecord") -> str:
    """Plain-text timeline (oldest first) for prompts and exports."""
    lines = []
    for event in sorted(record.events, key=lambda e: e.get("id", 0)):
        lines.append(f"- [{event.get('created_at', '')}] {event.get('type', 'Note')}: {event.get('content', '')}")
    return "\n".join(lines)


def extract_job_meta(job_description: str) -> Tuple[str, str]:
    """Best-effort (title, company) extraction from a job description.

    Scraped postings (JSON-LD) start with 'Job Title: ...' / 'Company: ...' lines.
    """
    title_match = re.search(r"^job title:\s*(.+)$", job_description or "", re.IGNORECASE | re.MULTILINE)
    company_match = re.search(r"^company:\s*(.+)$", job_description or "", re.IGNORECASE | re.MULTILINE)
    return (
        title_match.group(1).strip() if title_match else "",
        company_match.group(1).strip() if company_match else "",
    )


class SQLiteTrackerBackend:
    def _connect(self) -> sqlite3.Connection:
        data_dir = Path(os.getenv("DATA_DIR", "data"))
        data_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(data_dir / "history.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL DEFAULT 'local',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                company TEXT NOT NULL DEFAULT '',
                job_title TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Applied',
                ats_score INTEGER,
                job_snippet TEXT NOT NULL DEFAULT '',
                cv_markdown TEXT NOT NULL DEFAULT '',
                cover_letter TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                events TEXT NOT NULL DEFAULT '[]'
            )
            """)
        # Migration for databases created before the timeline feature
        try:
            conn.execute("ALTER TABLE applications ADD COLUMN events TEXT NOT NULL DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass  # column already exists
        return conn

    @staticmethod
    def _to_record(row) -> ApplicationRecord:
        values = list(row)
        try:
            values[-1] = json.loads(values[-1] or "[]")
        except (json.JSONDecodeError, TypeError):
            values[-1] = []
        return ApplicationRecord(*values)

    def add(self, record: dict, owner: str) -> Optional[int]:
        columns = [f for f in _FIELDS if f != "id"]
        record = dict(record, events=json.dumps(record.get("events") or []))
        with self._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO applications (owner, {', '.join(columns)}) " f"VALUES (?, {', '.join('?' for _ in columns)})",
                (owner, *[record[f] for f in columns]),
            )
            return cursor.lastrowid

    def list(self, owner: str) -> List[ApplicationRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {', '.join(_FIELDS)} FROM applications WHERE owner = ? ORDER BY id DESC",
                (owner,),
            ).fetchall()
        return [self._to_record(row) for row in rows]

    def get(self, record_id: int, owner: str) -> Optional[ApplicationRecord]:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {', '.join(_FIELDS)} FROM applications WHERE id = ? AND owner = ?",
                (record_id, owner),
            ).fetchone()
        return self._to_record(row) if row else None

    def update(self, record_id: int, owner: str, fields: dict) -> None:
        if "events" in fields and isinstance(fields["events"], list):
            fields = dict(fields, events=json.dumps(fields["events"]))
        assignments = ", ".join(f"{name} = ?" for name in fields)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE applications SET {assignments} WHERE id = ? AND owner = ?",
                (*fields.values(), record_id, owner),
            )

    def delete(self, record_id: int, owner: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM applications WHERE id = ? AND owner = ?", (record_id, owner))


class GCSTrackerBackend:
    def __init__(self, bucket_name: str, bucket=None):
        if bucket is None:
            from google.cloud import storage

            bucket = storage.Client().bucket(bucket_name)
        self._bucket = bucket

    @staticmethod
    def _blob_path(owner: str, record_id: int) -> str:
        return f"applications/{owner}/{record_id}.json"

    def add(self, record: dict, owner: str) -> Optional[int]:
        record_id = time.time_ns()
        while self._bucket.blob(self._blob_path(owner, record_id)).exists():
            record_id += 1
        record = dict(record, id=record_id)
        blob = self._bucket.blob(self._blob_path(owner, record_id))
        blob.upload_from_string(json.dumps(record), content_type="application/json")
        return record_id

    def _ids(self, owner: str) -> List[int]:
        prefix = f"applications/{owner}/"
        ids = []
        for blob in self._bucket.list_blobs(prefix=prefix):
            stem = blob.name[len(prefix) :].removesuffix(".json")
            if stem.isdigit():
                ids.append(int(stem))
        return sorted(ids, reverse=True)

    def list(self, owner: str) -> List[ApplicationRecord]:
        return [r for r in (self.get(i, owner) for i in self._ids(owner)) if r]

    def get(self, record_id: int, owner: str) -> Optional[ApplicationRecord]:
        blob = self._bucket.blob(self._blob_path(owner, record_id))
        if not blob.exists():
            return None
        data = json.loads(blob.download_as_text())
        data["events"] = data.get("events") or []
        return ApplicationRecord(**{f: data.get(f) for f in _FIELDS})

    def update(self, record_id: int, owner: str, fields: dict) -> None:
        record = self.get(record_id, owner)
        if not record:
            return
        data = asdict(record)
        data.update(fields)
        blob = self._bucket.blob(self._blob_path(owner, record_id))
        blob.upload_from_string(json.dumps(data), content_type="application/json")

    def delete(self, record_id: int, owner: str) -> None:
        blob = self._bucket.blob(self._blob_path(owner, record_id))
        if blob.exists():
            blob.delete()


_backend = None
_backend_key = None


def _get_backend():
    global _backend, _backend_key
    key = (os.getenv("GCS_BUCKET", ""), os.getenv("DATA_DIR", ""))
    if _backend is None or key != _backend_key:
        _backend = GCSTrackerBackend(key[0]) if key[0] else SQLiteTrackerBackend()
        _backend_key = key
    return _backend


class TrackerService:
    @staticmethod
    def add_application(
        company: str,
        job_title: str,
        status: str = "Applied",
        ats_score: Optional[int] = None,
        job_description: str = "",
        cv_markdown: str = "",
        cover_letter: str = "",
        notes: str = "",
        owner: str = "local",
    ) -> Optional[int]:
        """Tracks a new application, storing the exact CV version used to apply."""
        try:
            now = _now()
            record = {
                "created_at": now,
                "updated_at": now,
                "company": company.strip(),
                "job_title": job_title.strip(),
                "status": status if status in STATUSES else "Applied",
                "ats_score": ats_score,
                "job_snippet": " ".join((job_description or "").split())[:400],
                "cv_markdown": cv_markdown,
                "cover_letter": cover_letter,
                "notes": notes,
                "events": [],
            }
            record_id = _get_backend().add(record, owner)
            logger.info(f"Tracked application #{record_id} ({company} - {job_title})")
            return record_id
        except Exception as e:
            logger.error(f"Failed to track application: {e}")
            return None

    @staticmethod
    def list_applications(owner: str = "local") -> List[ApplicationRecord]:
        try:
            return _get_backend().list(owner)
        except Exception as e:
            logger.error(f"Failed to list applications: {e}")
            return []

    @staticmethod
    def get_application(record_id: int, owner: str = "local") -> Optional[ApplicationRecord]:
        try:
            return _get_backend().get(record_id, owner)
        except Exception as e:
            logger.error(f"Failed to load application #{record_id}: {e}")
            return None

    @staticmethod
    def update_application(record_id: int, owner: str = "local", **fields) -> bool:
        """Updates mutable fields (status, notes, company, job_title)."""
        allowed = {k: v for k, v in fields.items() if k in ("status", "notes", "company", "job_title")}
        if "status" in allowed and allowed["status"] not in STATUSES:
            del allowed["status"]
        if not allowed:
            return False
        allowed["updated_at"] = _now()
        try:
            backend = _get_backend()
            # Status changes are recorded in the application's timeline
            if "status" in allowed:
                record = backend.get(record_id, owner)
                if record and record.status != allowed["status"]:
                    events = list(record.events)
                    events.append(
                        {
                            "id": time.time_ns(),
                            "created_at": allowed["updated_at"],
                            "type": "Status change",
                            "content": f"{record.status} → {allowed['status']}",
                        }
                    )
                    allowed["events"] = events
            backend.update(record_id, owner, allowed)
            return True
        except Exception as e:
            logger.error(f"Failed to update application #{record_id}: {e}")
            return False

    @staticmethod
    def add_event(record_id: int, entry_type: str, content: str, owner: str = "local") -> bool:
        """Appends a timeline entry (interview notes, recruiter call, feedback, ...)."""
        if entry_type not in EVENT_TYPES or not (content or "").strip():
            return False
        try:
            backend = _get_backend()
            record = backend.get(record_id, owner)
            if not record:
                return False
            events = list(record.events)
            events.append(
                {
                    "id": time.time_ns(),
                    "created_at": _now(),
                    "type": entry_type,
                    "content": content.strip(),
                }
            )
            backend.update(record_id, owner, {"events": events, "updated_at": _now()})
            logger.info(f"Added {entry_type!r} timeline entry to application #{record_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add event to application #{record_id}: {e}")
            return False

    @staticmethod
    def delete_event(record_id: int, event_id: int, owner: str = "local") -> bool:
        """Removes a timeline entry from an application."""
        try:
            backend = _get_backend()
            record = backend.get(record_id, owner)
            if not record:
                return False
            events = [e for e in record.events if e.get("id") != event_id]
            backend.update(record_id, owner, {"events": events, "updated_at": _now()})
            return True
        except Exception as e:
            logger.error(f"Failed to delete event from application #{record_id}: {e}")
            return False

    @staticmethod
    def delete_application(record_id: int, owner: str = "local") -> bool:
        try:
            _get_backend().delete(record_id, owner)
            logger.info(f"Deleted application #{record_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete application #{record_id}: {e}")
            return False

    @staticmethod
    def stats(records: List[ApplicationRecord]) -> TrackerStats:
        """Dashboard aggregates over a list of applications."""
        by_status = {status: 0 for status in STATUSES}
        for record in records:
            if record.status in by_status:
                by_status[record.status] += 1

        submitted = sum(count for status, count in by_status.items() if status != "Saved")
        responded = sum(by_status[status] for status in RESPONDED_STATUSES)
        scores = [r.ats_score for r in records if r.ats_score is not None]

        return TrackerStats(
            total=len(records),
            active=sum(by_status[status] for status in ACTIVE_STATUSES),
            interviews=by_status["Interviewing"],
            offers=by_status["Offer"],
            response_rate=(responded / submitted) if submitted else None,
            avg_ats=(sum(scores) / len(scores)) if scores else None,
            by_status=by_status,
        )

    @staticmethod
    def stale_applications(
        records: List[ApplicationRecord], days: int = STALE_AFTER_DAYS, now: Optional[datetime] = None
    ) -> List[Tuple[ApplicationRecord, int]]:
        """Active applications with no activity for `days` -> [(record, days_stale)], oldest first."""
        now = now or datetime.now(timezone.utc)
        stale = []
        for record in records:
            if record.status not in ACTIVE_STATUSES:
                continue
            try:
                updated = datetime.strptime(record.updated_at, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            days_stale = (now - updated).days
            if days_stale >= days:
                stale.append((record, days_stale))
        return sorted(stale, key=lambda pair: -pair[1])

    @staticmethod
    def follow_up_draft(record: ApplicationRecord) -> str:
        """Deterministic follow-up email draft for a stale application."""
        return FOLLOW_UP_TEMPLATE.format(
            job_title=record.job_title or "open",
            company=record.company or "there",
            applied_date=record.created_at.split(" ")[0],
        )

    @staticmethod
    def to_csv(records: List[ApplicationRecord]) -> str:
        """Summary CSV export (without the full CV/cover-letter bodies)."""
        import csv
        import io

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["id", "created_at", "updated_at", "company", "job_title", "status", "ats_score", "notes", "activities"]
        )
        for r in records:
            writer.writerow(
                [r.id, r.created_at, r.updated_at, r.company, r.job_title, r.status, r.ats_score, r.notes, len(r.events)]
            )
        return buffer.getvalue()
