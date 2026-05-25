"""Registry store factory — liorm default, mock when LI_REGISTRY_MOCK=1."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .errors import RegistryError
from .liorm_mock import MockRegistryStore, get_registry_store as get_mock_store
from .lidb_import import LidbImportError
from .liorm_store import LiormRegistryStore, open_liorm_store

if TYPE_CHECKING:
    from .liorm_store import RegistryStore

_store: RegistryStore | None = None


def _mock_mode() -> bool:
    return os.environ.get("LI_REGISTRY_MOCK", "").lower() in ("1", "true", "yes")


def get_registry_store() -> RegistryStore:
    global _store
    if _store is not None:
        return _store
    if _mock_mode():
        _store = get_mock_store()
        return _store
    try:
        _store = open_liorm_store()
    except LidbImportError as exc:
        raise RuntimeError(
            f"{exc}. Set LI_REGISTRY_MOCK=1 for offline/mock registry or LIDB_ROOT to lidb checkout."
        ) from exc
    return _store


def reset_registry_store() -> None:
    """Test helper: drop cached store and liorm plans."""
    global _store
    _store = None
    from .liorm_mock import reset_registry_store as reset_mock
    from .plans import reset_registry_plans

    reset_mock()
    reset_registry_plans()


def registry_backend_name() -> str:
    if _mock_mode():
        return "mock"
    return "liorm"


__all__ = [
    "RegistryError",
    "MockRegistryStore",
    "LiormRegistryStore",
    "get_registry_store",
    "reset_registry_store",
    "registry_backend_name",
]
