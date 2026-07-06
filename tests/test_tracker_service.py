"""Tests for the job application tracker service."""

import pytest

import services.tracker_service as tracker_module
from services.tracker_service import (
    STATUSES,
    GCSTrackerBackend,
    TrackerService,
    extract_job_meta,
)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("GCS_BUCKET", raising=False)
    monkeypatch.setattr(tracker_module, "_backend", None)
    monkeypatch.setattr(tracker_module, "_backend_key", None)


def _add(**overrides):
    defaults = dict(
        company="Nimbus Analytics",
        job_title="Senior Backend Engineer",
        status="Applied",
        ats_score=82,
        job_description="Job Title: Senior Backend Engineer\nCompany: Nimbus Analytics\nPython role.",
        cv_markdown="# Alex Rivera\nMy CV v1",
        cover_letter="Dear team",
        owner="local",
    )
    defaults.update(overrides)
    return TrackerService.add_application(**defaults)


def test_add_and_list_with_cv_version():
    record_id = _add()
    assert record_id is not None

    records = TrackerService.list_applications()
    assert len(records) == 1
    record = records[0]
    assert record.company == "Nimbus Analytics"
    assert record.status == "Applied"
    assert record.ats_score == 82
    assert record.cv_markdown == "# Alex Rivera\nMy CV v1"
    assert record.cover_letter == "Dear team"
    assert "Python role" in record.job_snippet


def test_status_and_notes_update():
    record_id = _add()
    assert TrackerService.update_application(record_id, status="Interviewing", notes="Phone screen Friday")

    record = TrackerService.get_application(record_id)
    assert record.status == "Interviewing"
    assert record.notes == "Phone screen Friday"


def test_invalid_status_rejected_on_add_and_update():
    record_id = _add(status="NotAStatus")
    assert TrackerService.get_application(record_id).status == "Applied"

    assert not TrackerService.update_application(record_id, status="AlsoNotAStatus")
    assert TrackerService.get_application(record_id).status == "Applied"


def test_owner_isolation():
    _add(owner="alice")
    _add(owner="bob", company="Other Corp")

    assert [r.company for r in TrackerService.list_applications(owner="alice")] == ["Nimbus Analytics"]
    assert [r.company for r in TrackerService.list_applications(owner="bob")] == ["Other Corp"]


def test_delete():
    record_id = _add()
    assert TrackerService.delete_application(record_id)
    assert TrackerService.list_applications() == []


def test_stats():
    _add(status="Applied")
    _add(status="Interviewing")
    _add(status="Offer", ats_score=90)
    _add(status="Rejected", ats_score=60)
    _add(status="Saved", ats_score=None)

    stats = TrackerService.stats(TrackerService.list_applications())
    assert stats.total == 5
    assert stats.active == 2  # Applied + Interviewing
    assert stats.interviews == 1
    assert stats.offers == 1
    # 3 of 4 submitted applications got a response
    assert stats.response_rate == pytest.approx(3 / 4)
    assert stats.by_status["Saved"] == 1


def test_stats_empty():
    stats = TrackerService.stats([])
    assert stats.total == 0
    assert stats.response_rate is None
    assert stats.avg_ats is None


def test_csv_export():
    _add()
    csv_text = TrackerService.to_csv(TrackerService.list_applications())
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("id,created_at")
    assert "Nimbus Analytics" in lines[1]
    # Full CV body is not leaked into the summary export
    assert "My CV v1" not in csv_text


def test_extract_job_meta():
    title, company = extract_job_meta("Job Title: Staff Engineer\nCompany: Acme\nDetails...")
    assert title == "Staff Engineer"
    assert company == "Acme"

    title, company = extract_job_meta("Just a plain description")
    assert title == "" and company == ""


class FakeBlob:
    def __init__(self, store, name):
        self._store, self.name = store, name

    def upload_from_string(self, data, content_type=None):
        self._store[self.name] = data

    def download_as_text(self):
        return self._store[self.name]

    def exists(self):
        return self.name in self._store

    def delete(self):
        del self._store[self.name]


class FakeBucket:
    def __init__(self):
        self.store = {}

    def blob(self, name):
        return FakeBlob(self.store, name)

    def list_blobs(self, prefix=""):
        return [FakeBlob(self.store, n) for n in sorted(self.store) if n.startswith(prefix)]


def test_gcs_backend_roundtrip():
    backend = GCSTrackerBackend("fake", bucket=FakeBucket())
    record = {
        "created_at": "2026-07-06 10:00 UTC",
        "updated_at": "2026-07-06 10:00 UTC",
        "company": "Acme",
        "job_title": "Engineer",
        "status": "Applied",
        "ats_score": 70,
        "job_snippet": "snippet",
        "cv_markdown": "# CV",
        "cover_letter": "",
        "notes": "",
    }
    record_id = backend.add(record, owner="a")

    loaded = backend.get(record_id, owner="a")
    assert loaded.company == "Acme"
    assert backend.get(record_id, owner="b") is None

    backend.update(record_id, "a", {"status": "Offer"})
    assert backend.get(record_id, "a").status == "Offer"

    backend.delete(record_id, "a")
    assert backend.list("a") == []


def test_statuses_are_stable():
    # UI and stored data rely on these exact values
    assert STATUSES == ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]


def test_add_and_delete_timeline_events():
    record_id = _add()
    assert TrackerService.add_event(record_id, "Interview", "System design round, went well.")
    assert TrackerService.add_event(record_id, "Feedback", "Positive signal from the panel.")

    record = TrackerService.get_application(record_id)
    assert len(record.events) == 2
    assert record.events[0]["type"] == "Interview"
    assert record.events[1]["content"] == "Positive signal from the panel."
    assert all(e["id"] and e["created_at"] for e in record.events)

    assert TrackerService.delete_event(record_id, record.events[0]["id"])
    record = TrackerService.get_application(record_id)
    assert [e["type"] for e in record.events] == ["Feedback"]


def test_event_validation():
    record_id = _add()
    assert not TrackerService.add_event(record_id, "NotAType", "content")
    assert not TrackerService.add_event(record_id, "Interview", "   ")
    assert TrackerService.get_application(record_id).events == []


def test_status_change_logged_in_timeline():
    record_id = _add(status="Applied")
    TrackerService.update_application(record_id, status="Interviewing")

    record = TrackerService.get_application(record_id)
    assert record.status == "Interviewing"
    assert len(record.events) == 1
    assert record.events[0]["type"] == "Status change"
    assert record.events[0]["content"] == "Applied → Interviewing"

    # Saving the same status again does not spam the timeline
    TrackerService.update_application(record_id, status="Interviewing")
    assert len(TrackerService.get_application(record_id).events) == 1


def test_events_survive_gcs_roundtrip():
    backend = GCSTrackerBackend("fake", bucket=FakeBucket())
    record = {
        "created_at": "2026-07-06 10:00 UTC",
        "updated_at": "2026-07-06 10:00 UTC",
        "company": "Acme",
        "job_title": "Engineer",
        "status": "Applied",
        "ats_score": 70,
        "job_snippet": "",
        "cv_markdown": "",
        "cover_letter": "",
        "notes": "",
        "events": [{"id": 1, "created_at": "2026-07-06 10:05 UTC", "type": "Note", "content": "hello"}],
    }
    record_id = backend.add(record, owner="a")
    loaded = backend.get(record_id, owner="a")
    assert loaded.events[0]["content"] == "hello"


def test_sqlite_migration_adds_events_column(tmp_path, monkeypatch):
    import sqlite3

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Simulate a pre-timeline database (no events column)
    conn = sqlite3.connect(tmp_path / "history.db")
    conn.execute("""CREATE TABLE applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL DEFAULT 'local',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            company TEXT NOT NULL DEFAULT '', job_title TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Applied', ats_score INTEGER,
            job_snippet TEXT NOT NULL DEFAULT '', cv_markdown TEXT NOT NULL DEFAULT '',
            cover_letter TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT ''
        )""")
    conn.execute(
        "INSERT INTO applications (owner, created_at, updated_at, company, job_title, status) "
        "VALUES ('local', 'x', 'x', 'OldCo', 'Old Role', 'Applied')"
    )
    conn.commit()
    conn.close()

    records = TrackerService.list_applications()
    assert records[0].company == "OldCo"
    assert records[0].events == []
    assert TrackerService.add_event(records[0].id, "Note", "post-migration entry")


def test_stale_applications_detection():
    from datetime import datetime, timedelta, timezone

    from services.tracker_service import STALE_AFTER_DAYS, ApplicationRecord

    now = datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc)

    def make(status, days_ago, record_id):
        stamp = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M UTC")
        return ApplicationRecord(
            id=record_id,
            created_at=stamp,
            updated_at=stamp,
            company=f"C{record_id}",
            job_title="Role",
            status=status,
            ats_score=None,
        )

    records = [
        make("Applied", 12, 1),  # stale
        make("Interviewing", 8, 2),  # stale
        make("Applied", 2, 3),  # fresh
        make("Rejected", 30, 4),  # closed - never nagged
        make("Saved", 30, 5),  # not submitted - never nagged
    ]

    stale = TrackerService.stale_applications(records, now=now)
    assert [(r.id, days) for r, days in stale] == [(1, 12), (2, 8)]
    assert STALE_AFTER_DAYS == 7


def test_follow_up_draft_contains_details():
    from services.tracker_service import ApplicationRecord

    record = ApplicationRecord(
        id=1,
        created_at="2026-06-20 10:00 UTC",
        updated_at="2026-06-20 10:00 UTC",
        company="Acme",
        job_title="Platform Engineer",
        status="Applied",
        ats_score=None,
    )
    draft = TrackerService.follow_up_draft(record)
    assert "Platform Engineer" in draft
    assert "Acme" in draft
    assert "2026-06-20" in draft


def test_format_timeline_oldest_first():
    from services.tracker_service import ApplicationRecord, format_timeline

    record = ApplicationRecord(
        id=1,
        created_at="x",
        updated_at="x",
        company="",
        job_title="",
        status="Applied",
        ats_score=None,
        events=[
            {"id": 2, "created_at": "2026-07-02 10:00 UTC", "type": "Interview", "content": "second"},
            {"id": 1, "created_at": "2026-07-01 10:00 UTC", "type": "Recruiter call", "content": "first"},
        ],
    )
    text = format_timeline(record)
    assert text.index("first") < text.index("second")
    assert "[2026-07-01 10:00 UTC] Recruiter call: first" in text
