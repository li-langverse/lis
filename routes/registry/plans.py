"""Register registry liorm plans from profiles/registry-min.toml (PH-DB-4)."""

from __future__ import annotations

from typing import Any

from .lidb_import import import_liorm

_PLANS_READY = False

# Plan IDs match [modules.liorm_plans] in profiles/registry-min.toml
PLAN_LIST_PACKAGES = "registry.list_packages"
PLAN_GET_VERSION = "registry.get_version"
PLAN_PUBLISH_VERSION = "registry.publish_version"
PLAN_YANK_VERSION = "registry.yank_version"


def _registry_plans() -> list[dict[str, Any]]:
    return [
        {
            "name": "list_packages",
            "plan_id": PLAN_LIST_PACKAGES,
            "sql": (
                "SELECT pv.version, pv.tree_digest, pv.proof_digest, pv.coverage_pct, "
                "pv.published_at, pv.yanked, p.name "
                "FROM public.package_versions pv "
                "JOIN public.packages p ON p.id = pv.package_id "
                "WHERE ($1::text IS NULL OR p.name = $1::text) "
                "AND ($2::boolean OR pv.yanked = false) "
                "ORDER BY p.name, pv.version LIMIT $3 OFFSET $4"
            ),
            "param_schema": {
                "name": "text",
                "include_yanked": "boolean",
                "limit": "int",
                "offset": "int",
            },
        },
        {
            "name": "get_version",
            "plan_id": PLAN_GET_VERSION,
            "sql": (
                "SELECT pv.version, pv.tree_digest, pv.proof_digest, pv.coverage_pct, "
                "pv.published_at, pv.yanked, p.name "
                "FROM public.package_versions pv "
                "JOIN public.packages p ON p.id = pv.package_id "
                "WHERE p.name = $1 AND pv.version = $2"
            ),
            "param_schema": {"name": "text", "version": "text"},
        },
        {
            "name": "publish_version",
            "plan_id": PLAN_PUBLISH_VERSION,
            "sql": (
                "INSERT INTO public.package_versions "
                "(package_id, version, tree_digest, proof_digest, coverage_pct, publisher_id) "
                "VALUES ($1, $2, $3, $4, $5, $6)"
            ),
            "param_schema": {
                "package_id": "uuid",
                "version": "text",
                "tree_digest": "text",
                "proof_digest": "text",
                "coverage_pct": "float",
                "publisher_id": "uuid",
            },
        },
        {
            "name": "yank_version",
            "plan_id": PLAN_YANK_VERSION,
            "sql": (
                "INSERT INTO public.yanks (package_version_id, reason, yanked_by) "
                "VALUES ($1, $2, $3)"
            ),
            "param_schema": {
                "package_version_id": "uuid",
                "reason": "text",
                "yanked_by": "uuid",
            },
        },
    ]


def ensure_registry_plans(*, force: bool = False) -> None:
    global _PLANS_READY
    if _PLANS_READY and not force:
        return
    execute, register_plan, clear_plans, _, _ = import_liorm()
    if force:
        clear_plans()
    for spec in _registry_plans():
        register_plan(
            spec["name"],
            plan_id=spec["plan_id"],
            ir={"source": "lis.registry", "op": spec["name"]},
            sql=spec["sql"],
            param_schema=spec["param_schema"],
        )
    _PLANS_READY = True


def reset_registry_plans() -> None:
    """Test helper — clear plan registry and allow re-register."""
    global _PLANS_READY
    try:
        _, _, clear_plans, _, _ = import_liorm()
        clear_plans()
    except Exception:
        pass
    _PLANS_READY = False
