"""Auth store factory — lidb catalog (default) or JSON mock for offline dev."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .errors import AuthError
from .mock_store import MockAuthStore, reset_auth_store as _reset_mock

if TYPE_CHECKING:
    from .lidb_store import LidbAuthStore

_store: MockAuthStore | None = None


def _mock_mode() -> bool:
    backend = os.environ.get("LI_AUTH_BACKEND", "auto").strip().lower()
    if backend == "mock":
        return True
    if backend == "lidb":
        return False
    # auto: follow registry mock flag unless lidb catalog already exists
    if os.environ.get("LI_REGISTRY_MOCK", "").lower() in ("1", "true", "yes"):
        return True
    data_dir = os.environ.get("LI_DATA_DIR", "")
    if data_dir:
        from pathlib import Path

        from .lidb_snapshot import catalog_path

        if catalog_path(data_dir).is_file():
            return False
    return os.environ.get("LI_AUTH_BACKEND", "auto").lower() == "mock"


def auth_backend_name() -> str:
    return "mock" if _mock_mode() else "lidb"


def get_auth_store() -> MockAuthStore:
    global _store
    if _store is not None:
        return _store
    if _mock_mode():
        from .mock_store import get_auth_store as get_mock

        _store = get_mock()
    else:
        from .lidb_store import LidbAuthStore

        _store = LidbAuthStore.open()
    return _store


def reset_auth_store() -> None:
    global _store
    _store = None
    _reset_mock()


__all__ = [
    "AuthError",
    "MockAuthStore",
    "get_auth_store",
    "reset_auth_store",
    "auth_backend_name",
]
