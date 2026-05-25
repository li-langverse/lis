"""Resolve and import lidb liorm (PH-DB-4 gap #2)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class LidbImportError(RuntimeError):
    """lidb liorm is not importable (missing checkout or WP2 branch)."""


def resolve_lidb_root() -> Path | None:
    """Return first existing lidb repo root, or None."""
    env = os.environ.get("LIDB_ROOT", "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env))
    lis_root = Path(__file__).resolve().parents[2]
    candidates.append(lis_root.parent / "lidb")
    candidates.append(lis_root / "vendor" / "lidb")
    for path in candidates:
        if (path / "liorm" / "execute.py").is_file():
            return path.resolve()
    return None


def ensure_lidb_on_path() -> Path:
    root = resolve_lidb_root()
    if root is None:
        raise LidbImportError(
            "lidb liorm not found: set LIDB_ROOT to a checkout with liorm/execute.py "
            "(e.g. li-langverse/lidb feat/ph-db-2-liorm-impl)"
        )
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    return root


def import_liorm() -> tuple[Any, Any, Any, Any, Any]:
    """Return execute, register_plan, clear_plans, ParameterMismatch, UnknownPlan."""
    ensure_lidb_on_path()
    from liorm.errors import ParameterMismatch, UnknownPlan
    from liorm.execute import clear_plans, execute, register_plan

    return execute, register_plan, clear_plans, ParameterMismatch, UnknownPlan


def liorm_execute_subprocess(plan_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Run liorm.execute in a child interpreter."""
    root = ensure_lidb_on_path()
    lis_root = Path(__file__).resolve().parents[2]
    script = r"""
import json, os, sys
sys.path.insert(0, os.environ["LIDB_ROOT"])
sys.path.insert(0, os.environ["LIS_ROOT"])
from routes.registry.plans import ensure_registry_plans
from liorm.execute import execute
ensure_registry_plans()
req = json.loads(sys.stdin.read())
r = execute(req["plan_id"], req["params"])
print(json.dumps({"plan_id": r.plan_id, "rows": r.rows}))
"""
    env = os.environ.copy()
    env["LIDB_ROOT"] = str(root)
    env["LIS_ROOT"] = str(lis_root)
    proc = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps({"plan_id": plan_id, "params": params}),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise LidbImportError(f"liorm subprocess failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def use_liorm_subprocess() -> bool:
    return os.environ.get("LI_LIDB_LIORM_SUBPROCESS", "").lower() in ("1", "true", "yes")
