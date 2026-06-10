"""Auth store factory."""

from __future__ import annotations

from .errors import AuthError
from .mock_store import MockAuthStore, get_auth_store, reset_auth_store

__all__ = [
    "AuthError",
    "MockAuthStore",
    "get_auth_store",
    "reset_auth_store",
    "auth_backend_name",
]


def auth_backend_name() -> str:
    return "mock"
