"""Tests for the GCS history backend (using an in-memory fake bucket) and backend selection."""

import pytest

import services.history_service as history_module
from services.history_service import GCSHistoryBackend, HistoryService, SQLiteHistoryBackend, session_scoped


class FakeBlob:
    def __init__(self, store: dict, name: str):
        self._store = store
        self.name = name

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
        return [FakeBlob(self.store, name) for name in sorted(self.store) if name.startswith(prefix)]


@pytest.fixture
def backend():
    return GCSHistoryBackend("fake-bucket", bucket=FakeBucket())


def _record(**overrides):
    record = {
        "created_at": "2026-07-04 12:00 UTC",
        "job_snippet": "Senior Python Engineer",
        "ats_score": 70,
        "board_report": "report",
        "minimal_changes": "changes",
        "final_cv": "# CV",
        "cover_letter": "",
    }
    record.update(overrides)
    return record


def test_save_and_get(backend):
    record_id = backend.save(_record(), owner="alice")
    loaded = backend.get(record_id, owner="alice")
    assert loaded.id == record_id
    assert loaded.job_snippet == "Senior Python Engineer"
    assert loaded.ats_score == 70


def test_owner_isolation(backend):
    backend.save(_record(job_snippet="alice job"), owner="alice")
    backend.save(_record(job_snippet="bob job"), owner="bob")

    alice_records = backend.list("alice", limit=10)
    assert [r.job_snippet for r in alice_records] == ["alice job"]
    assert backend.get(alice_records[0].id, owner="bob") is None


def test_list_newest_first_and_limit(backend):
    first = backend.save(_record(), owner="a")
    second = backend.save(_record(), owner="a")
    third = backend.save(_record(), owner="a")
    assert first < second < third  # epoch-ms ids are monotonic

    ids = [r.id for r in backend.list("a", limit=2)]
    assert ids == sorted([second, third], reverse=True)


def test_delete_and_delete_all(backend):
    record_id = backend.save(_record(), owner="a")
    backend.save(_record(), owner="a")

    backend.delete(record_id, owner="a")
    assert backend.get(record_id, owner="a") is None
    assert len(backend.list("a", limit=10)) == 1

    backend.delete_all("a")
    assert backend.list("a", limit=10) == []


def test_backend_selection(monkeypatch, tmp_path):
    monkeypatch.setattr(history_module, "_backend", None)
    monkeypatch.setattr(history_module, "_backend_key", None)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("GCS_BUCKET", raising=False)
    assert isinstance(history_module._get_backend(), SQLiteHistoryBackend)

    monkeypatch.setenv("GCS_BUCKET", "some-bucket")
    monkeypatch.setattr(GCSHistoryBackend, "__init__", lambda self, name, bucket=None: None)
    assert isinstance(history_module._get_backend(), GCSHistoryBackend)


def test_session_scoped(monkeypatch):
    monkeypatch.delenv("HISTORY_SCOPE", raising=False)
    assert not session_scoped()
    monkeypatch.setenv("HISTORY_SCOPE", "session")
    assert session_scoped()


def test_service_uses_owner(monkeypatch, tmp_path):
    monkeypatch.setattr(history_module, "_backend", None)
    monkeypatch.setattr(history_module, "_backend_key", None)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("GCS_BUCKET", raising=False)

    HistoryService.save_analysis("job for A", "", "", "", owner="a")
    HistoryService.save_analysis("job for B", "", "", "", owner="b")

    assert [r.job_snippet for r in HistoryService.list_analyses(owner="a")] == ["job for A"]
    assert [r.job_snippet for r in HistoryService.list_analyses(owner="b")] == ["job for B"]
