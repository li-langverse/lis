"""Registry store backed by lidb liorm.execute (PH-DB-4 gap #2)."""

from __future__ import annotations

import os
from typing import Any, Protocol

from .errors import RegistryError
from .lidb_import import (
    LidbImportError,
    import_liorm,
    liorm_execute_subprocess,
    use_liorm_subprocess,
)
from .liorm_mock import MockRegistryStore, PackageVersion
from .plans import (
    PLAN_GET_VERSION,
    PLAN_LIST_PACKAGES,
    PLAN_PUBLISH_VERSION,
    PLAN_YANK_VERSION,
    ensure_registry_plans,
)


class RegistryStore(Protocol):
    def list_packages(
        self,
        *,
        name: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_yanked: bool = False,
    ) -> dict[str, Any]: ...

    def get_package_version(self, name: str, version: str) -> dict[str, Any]: ...

    def publish(self, name: str, body: dict[str, Any], *, token: str | None) -> dict[str, Any]: ...

    def yank(self, name: str, version: str, reason: str, *, token: str | None) -> dict[str, Any]: ...


def _run_plan(plan_id: str, params: dict[str, Any]) -> dict[str, Any]:
    if use_liorm_subprocess():
        return liorm_execute_subprocess(plan_id, params)
    execute, _, _, ParameterMismatch, UnknownPlan = import_liorm()
    try:
        result = execute(plan_id, params)
    except ParameterMismatch as exc:
        raise RegistryError("bad_request", str(exc), status=400) from exc
    except UnknownPlan as exc:
        raise RegistryError("internal_error", str(exc), status=500) from exc
    return {"plan_id": result.plan_id, "rows": result.rows}


class LiormRegistryStore:
    """
    Registry API via liorm plans; persists through JSON until lidb engine returns rows.

    Each mutating/read path calls `execute` for param binding + audit, then applies
    the same semantics as the PH-DB-4 mock store on local state (WP1 engine swap).
    """

    backend = "liorm"

    def __init__(self, backing: MockRegistryStore) -> None:
        self._backing = backing
        ensure_registry_plans()

    @classmethod
    def open(cls, data_dir: str | os.PathLike[str] | None = None) -> LiormRegistryStore:
        ensure_registry_plans()
        return cls(MockRegistryStore.open(data_dir))

    @property
    def engine_stub(self) -> bool:
        return True

    def list_packages(
        self,
        *,
        name: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_yanked: bool = False,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        _run_plan(
            PLAN_LIST_PACKAGES,
            {
                "name": name,
                "include_yanked": include_yanked,
                "limit": limit,
                "offset": offset,
            },
        )
        return self._backing.list_packages(
            name=name,
            limit=limit,
            offset=offset,
            include_yanked=include_yanked,
        )

    def get_package_version(self, name: str, version: str) -> dict[str, Any]:
        _run_plan(PLAN_GET_VERSION, {"name": name, "version": version})
        return self._backing.get_package_version(name, version)

    def publish(self, name: str, body: dict[str, Any], *, token: str | None) -> dict[str, Any]:
        if not token:
            raise RegistryError("unauthorized", "missing bearer token", status=401)
        version = body.get("version") or ""
        _run_plan(
            PLAN_PUBLISH_VERSION,
            {
                "package_id": body.get("pkg_id") or "00000000-0000-0000-0000-000000000001",
                "version": version,
                "tree_digest": body.get("tree_digest") or "",
                "proof_digest": body.get("proof_digest") or "",
                "coverage_pct": float(body.get("coverage_pct") or 0),
                "publisher_id": body.get("publisher_key_id") or "00000000-0000-0000-0000-000000000002",
            },
        )
        return self._backing.publish(name, body, token=token)

    def yank(self, name: str, version: str, reason: str, *, token: str | None) -> dict[str, Any]:
        if not token:
            raise RegistryError("unauthorized", "missing bearer token", status=401)
        _run_plan(
            PLAN_YANK_VERSION,
            {
                "package_version_id": "00000000-0000-0000-0000-000000000003",
                "reason": reason,
                "yanked_by": "00000000-0000-0000-0000-000000000002",
            },
        )
        return self._backing.yank(name, version, reason, token=token)


def open_liorm_store(data_dir: str | os.PathLike[str] | None = None) -> LiormRegistryStore:
    try:
        return LiormRegistryStore.open(data_dir)
    except LidbImportError:
        raise
