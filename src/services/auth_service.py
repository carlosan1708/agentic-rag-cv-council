"""Approval-based access control.

Enabled with AUTH_MODE=approval. Flow:
1. A visitor requests access with their email and receives an access code.
2. An admin (holder of ADMIN_CODE) approves or rejects the request in-app.
3. Once approved, the visitor logs in with email + access code.

Users are stored next to the analysis history: SQLite locally, GCS objects
(auth/users/{email}.json) when GCS_BUCKET is set.
"""

import json
import os
import re
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from logger import logger

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class UserRecord:
    email: str
    access_code: str
    status: str
    created_at: str


def auth_enabled() -> bool:
    return os.getenv("AUTH_MODE", "open").lower() == "approval"


def admin_code() -> str:
    return os.getenv("ADMIN_CODE", "")


def valid_email(email: str) -> bool:
    return bool(_EMAIL_PATTERN.match(email or ""))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _normalize(email: str) -> str:
    return (email or "").strip().lower()


class SQLiteAuthBackend:
    def _connect(self) -> sqlite3.Connection:
        data_dir = Path(os.getenv("DATA_DIR", "data"))
        data_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(data_dir / "history.db")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                access_code TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
        return conn

    def get(self, email: str) -> Optional[UserRecord]:
        with self._connect() as conn:
            row = conn.execute("SELECT email, access_code, status, created_at FROM users WHERE email = ?", (email,)).fetchone()
        return UserRecord(*row) if row else None

    def put(self, user: UserRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO users (email, access_code, status, created_at) VALUES (?, ?, ?, ?)",
                (user.email, user.access_code, user.status, user.created_at),
            )

    def delete(self, email: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM users WHERE email = ?", (email,))

    def list_all(self) -> List[UserRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT email, access_code, status, created_at FROM users ORDER BY created_at").fetchall()
        return [UserRecord(*row) for row in rows]


class GCSAuthBackend:
    def __init__(self, bucket_name: str, bucket=None):
        if bucket is None:
            from google.cloud import storage

            bucket = storage.Client().bucket(bucket_name)
        self._bucket = bucket

    @staticmethod
    def _blob_path(email: str) -> str:
        return f"auth/users/{email}.json"

    def get(self, email: str) -> Optional[UserRecord]:
        blob = self._bucket.blob(self._blob_path(email))
        if not blob.exists():
            return None
        return UserRecord(**json.loads(blob.download_as_text()))

    def put(self, user: UserRecord) -> None:
        blob = self._bucket.blob(self._blob_path(user.email))
        blob.upload_from_string(json.dumps(user.__dict__), content_type="application/json")

    def delete(self, email: str) -> None:
        blob = self._bucket.blob(self._blob_path(email))
        if blob.exists():
            blob.delete()

    def list_all(self) -> List[UserRecord]:
        users = []
        for blob in self._bucket.list_blobs(prefix="auth/users/"):
            try:
                users.append(UserRecord(**json.loads(blob.download_as_text())))
            except Exception:
                continue
        return sorted(users, key=lambda u: u.created_at)


_backend = None
_backend_key = None


def _get_backend():
    global _backend, _backend_key
    key = (os.getenv("GCS_BUCKET", ""), os.getenv("DATA_DIR", ""))
    if _backend is None or key != _backend_key:
        _backend = GCSAuthBackend(key[0]) if key[0] else SQLiteAuthBackend()
        _backend_key = key
    return _backend


class AuthService:
    @staticmethod
    def request_access(email: str) -> Optional[str]:
        """Registers a pending access request. Returns the access code, or the
        existing code if the email already requested access."""
        email = _normalize(email)
        if not valid_email(email):
            return None
        try:
            backend = _get_backend()
            existing = backend.get(email)
            if existing:
                return existing.access_code
            user = UserRecord(
                email=email,
                access_code=secrets.token_hex(4),
                status=STATUS_PENDING,
                created_at=_now(),
            )
            backend.put(user)
            logger.info(f"Access requested for {email}")
            return user.access_code
        except Exception as e:
            logger.error(f"Failed to request access: {e}")
            return None

    @staticmethod
    def login(email: str, access_code: str) -> Optional[str]:
        """Returns the user's status if email+code match ('approved' means logged in)."""
        email = _normalize(email)
        try:
            user = _get_backend().get(email)
        except Exception as e:
            logger.error(f"Login lookup failed: {e}")
            return None
        if not user or not secrets.compare_digest(user.access_code, (access_code or "").strip()):
            return None
        return user.status

    @staticmethod
    def list_pending() -> List[UserRecord]:
        try:
            return [u for u in _get_backend().list_all() if u.status == STATUS_PENDING]
        except Exception as e:
            logger.error(f"Failed to list pending users: {e}")
            return []

    @staticmethod
    def list_users() -> List[UserRecord]:
        try:
            return _get_backend().list_all()
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []

    @staticmethod
    def approve(email: str) -> bool:
        email = _normalize(email)
        try:
            backend = _get_backend()
            user = backend.get(email)
            if not user:
                return False
            user.status = STATUS_APPROVED
            backend.put(user)
            logger.info(f"Approved access for {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to approve {email}: {e}")
            return False

    @staticmethod
    def reject(email: str) -> bool:
        email = _normalize(email)
        try:
            _get_backend().delete(email)
            logger.info(f"Rejected/removed access for {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to reject {email}: {e}")
            return False
