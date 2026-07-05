"""Tests for the approval-based auth service."""

import pytest

import services.auth_service as auth_module
from services.auth_service import STATUS_APPROVED, STATUS_PENDING, AuthService, auth_enabled, valid_email


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("GCS_BUCKET", raising=False)
    monkeypatch.setattr(auth_module, "_backend", None)
    monkeypatch.setattr(auth_module, "_backend_key", None)


def test_auth_enabled(monkeypatch):
    monkeypatch.delenv("AUTH_MODE", raising=False)
    assert not auth_enabled()
    monkeypatch.setenv("AUTH_MODE", "approval")
    assert auth_enabled()


def test_valid_email():
    assert valid_email("a@b.co")
    assert not valid_email("not-an-email")
    assert not valid_email("")


def test_request_login_approval_flow():
    code = AuthService.request_access("User@Example.com")
    assert code and len(code) == 8

    # Pending user can't get in yet, but the code matches
    assert AuthService.login("user@example.com", code) == STATUS_PENDING
    assert AuthService.login("user@example.com", "wrong") is None
    assert AuthService.login("other@example.com", code) is None

    assert AuthService.approve("user@example.com")
    assert AuthService.login("user@example.com", code) == STATUS_APPROVED


def test_request_is_idempotent():
    first = AuthService.request_access("dup@example.com")
    second = AuthService.request_access("dup@example.com")
    assert first == second
    assert len(AuthService.list_users()) == 1


def test_invalid_email_rejected():
    assert AuthService.request_access("nope") is None


def test_list_pending_and_reject():
    AuthService.request_access("a@example.com")
    AuthService.request_access("b@example.com")
    AuthService.approve("a@example.com")

    pending = AuthService.list_pending()
    assert [u.email for u in pending] == ["b@example.com"]

    assert AuthService.reject("b@example.com")
    assert AuthService.list_pending() == []
    assert AuthService.login("b@example.com", "anything") is None


def test_approve_unknown_user_fails():
    assert not AuthService.approve("ghost@example.com")
