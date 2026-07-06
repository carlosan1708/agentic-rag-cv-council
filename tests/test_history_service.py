"""Tests for the local analysis history persistence."""

import pytest

from services.history_service import HistoryService


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


def test_save_and_list():
    record_id = HistoryService.save_analysis(
        job_description="Senior Python Engineer at Acme",
        board_report="Report body",
        minimal_changes="Changes body",
        final_cv="# CV",
        cover_letter="Dear team",
        ats_score=72,
    )
    assert record_id is not None

    records = HistoryService.list_analyses()
    assert len(records) == 1
    assert records[0].job_snippet.startswith("Senior Python Engineer")
    assert records[0].ats_score == 72
    assert records[0].cover_letter == "Dear team"


def test_get_and_delete():
    record_id = HistoryService.save_analysis("job", "r", "m", "cv")
    assert HistoryService.get_analysis(record_id).final_cv == "cv"

    assert HistoryService.delete_analysis(record_id)
    assert HistoryService.get_analysis(record_id) is None


def test_delete_all():
    HistoryService.save_analysis("a", "", "", "")
    HistoryService.save_analysis("b", "", "", "")
    assert HistoryService.delete_all()
    assert HistoryService.list_analyses() == []


def test_list_order_newest_first():
    first = HistoryService.save_analysis("first", "", "", "")
    second = HistoryService.save_analysis("second", "", "", "")
    records = HistoryService.list_analyses()
    assert [r.id for r in records] == [second, first]
