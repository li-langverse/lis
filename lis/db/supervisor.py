"""PH-DB-3 embedded lidb supervisor — start, migrate, status, stop."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lis.db.paths import (
    configure_lidb_env,
    ensure_embed,
    heap_catalog_path,
    profile_path,
    require_lidb_repo,
    resolve_data_dir,
    resolve_profile_name,
    state_path,
)
from lis.db.profile import Profile, load_profile

STATUS_PROTOCOL_VERSION = "1"


def _import_lidb_stack(lidb_repo: Path) -> None:
    root = str(lidb_repo)
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_profile(profile_name: str) -> Profile:
    return load_profile(profile_path(profile_name))


class DbSupervisor:
    """Supervise in-process lidb embed for a named profile."""

    def __init__(
        self,
        *,
        data_dir: Path | None = None,
        profile_name: str | None = None,
    ) -> None:
        self.data_dir = data_dir or resolve_data_dir()
        self.profile_name = resolve_profile_name(profile_name)
        self.profile = _load_profile(self.profile_name)
        self.lidb_repo = require_lidb_repo()

    def _prepare_env(self) -> Path:
        embed = ensure_embed(self.lidb_repo)
        configure_lidb_env(lidb_repo=self.lidb_repo, data_dir=self.data_dir, embed=embed)
        _import_lidb_stack(self.lidb_repo)
        return embed

    def migrate(self) -> bool:
        """Open data dir and apply lidb migrations."""
        self._prepare_env()
        from liorm import embed_engine

        embed_engine.reset_session_for_tests()
        session = embed_engine.EmbeddedSession(self.data_dir)
        ok = session.open_and_migrate()
        session.close()
        return ok

    def register_plans(self) -> int:
        """Compile profile liq sources and register liorm plans."""
        from liq.compiler import compile
        from liorm.execute import clear_plans, register_plan

        clear_plans()
        count = 0
        for spec in self.profile.plans:
            plan = compile(spec.liq)
            register_plan(
                spec.name,
                plan_id=plan.plan_id,
                ir=plan.ir,
                sql=plan.sql,
                param_schema=plan.param_schema,
            )
            count += 1
        return count

    def _build_checks(
        self,
        *,
        migrated: bool,
        engine_ok: bool,
        plans: int | None,
    ) -> dict[str, str]:
        checks: dict[str, str] = {
            "catalog": "ok" if migrated else "missing",
            "engine": "ok" if engine_ok else "failed",
        }
        if plans is not None:
            checks["plans"] = "ok" if plans > 0 else "empty"
        return checks

    def _hosting_fields(self) -> dict[str, Any]:
        if self.profile.hosting is None:
            return {}
        return {
            "service": self.profile.hosting.service,
            "readiness_requires": list(self.profile.hosting.readiness_requires),
            "liveness_interval_sec": self.profile.hosting.liveness_interval_sec,
        }

    def _evaluate_ready(self, checks: dict[str, str], *, plans: int | None) -> bool:
        requires = (
            list(self.profile.hosting.readiness_requires)
            if self.profile.hosting
            else ["catalog", "engine", "plans"]
        )
        for name in requires:
            if name == "plans":
                if plans is None or plans <= 0:
                    return False
                continue
            if name == "tcp_listen":
                if checks.get("tcp_listen") != "ok":
                    return False
                continue
            if checks.get(name) != "ok":
                return False
        return True

    def start(self) -> dict[str, Any]:
        """Migrate, register plans, persist ready state (no TCP for embed profiles)."""
        embed = self._prepare_env()
        from liorm import embed_engine

        embed_engine.reset_session_for_tests()
        session = embed_engine.EmbeddedSession(self.data_dir)
        if not session.open_and_migrate():
            raise RuntimeError("lidb open/migrate failed")
        plans = self.register_plans()
        engine_ok = embed_engine.probe_engine_ready()
        if not engine_ok:
            raise RuntimeError("embedded engine probe failed after migrate")
        session.close()

        tcp_listen = False
        if self.profile.tcp_port and self.profile.embed_mode != "in_process":
            raise NotImplementedError(
                f"tcp listen on port {self.profile.tcp_port} not implemented "
                f"(profile={self.profile.name}, embed_mode={self.profile.embed_mode})"
            )

        migrated = heap_catalog_path(self.data_dir).is_file()
        checks = self._build_checks(migrated=migrated, engine_ok=engine_ok, plans=plans)
        checks["tcp_listen"] = "ok" if tcp_listen else "off"
        ready = self._evaluate_ready(checks, plans=plans)

        state = {
            "protocol_version": STATUS_PROTOCOL_VERSION,
            "live": True,
            "ready": ready,
            "profile": self.profile.name,
            "data_dir": str(self.data_dir),
            "lidb_repo": str(self.lidb_repo),
            "catalog": str(heap_catalog_path(self.data_dir)),
            "migration": self.profile.migration,
            "verticals": self.profile.verticals,
            "migrated": migrated,
            "engine": "lidb_embed",
            "embed_binary": str(embed),
            "plans_registered": plans,
            "checks": checks,
            "tcp_listen": tcp_listen,
            "tcp_port": self.profile.tcp_port,
            "embed_mode": self.profile.embed_mode,
            "started_at": datetime.now(timezone.utc).isoformat(),
            **self._hosting_fields(),
        }
        path = state_path(self.data_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        os.environ["LI_PROFILE"] = self.profile.name
        return state

    def status(self) -> dict[str, Any]:
        """Return health JSON; probe engine when state file exists."""
        path = state_path(self.data_dir)
        stored: dict[str, Any] = {}
        if path.is_file():
            try:
                stored = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                stored = {"state_error": "invalid db-state.json"}

        migrated = heap_catalog_path(self.data_dir).is_file()
        plans_registered = stored.get("plans_registered")
        engine_ok = False
        probe = "skipped"

        if migrated:
            try:
                self._prepare_env()
                from liorm import embed_engine

                embed_engine.reset_session_for_tests()
                session = embed_engine.EmbeddedSession(self.data_dir)
                if session.open_and_migrate() and embed_engine.probe_engine_ready():
                    engine_ok = True
                    probe = "ok"
                session.close()
            except Exception as exc:  # noqa: BLE001 — status must report failure
                probe = "failed"
                stored["error"] = str(exc)

        checks = self._build_checks(
            migrated=migrated,
            engine_ok=engine_ok,
            plans=plans_registered if isinstance(plans_registered, int) else None,
        )
        tcp_listen = bool(stored.get("tcp_listen"))
        checks["tcp_listen"] = "ok" if tcp_listen else "off"
        ready = self._evaluate_ready(
            checks,
            plans=plans_registered if isinstance(plans_registered, int) else None,
        )

        base: dict[str, Any] = {
            "protocol_version": STATUS_PROTOCOL_VERSION,
            "live": True,
            "ready": ready,
            "profile": self.profile.name,
            "data_dir": str(self.data_dir),
            "state_file": str(path),
            "catalog": str(heap_catalog_path(self.data_dir)),
            "migration": self.profile.migration,
            "verticals": self.profile.verticals,
            "migrated": migrated,
            "engine": "lidb_embed",
            "tcp_listen": tcp_listen,
            "tcp_port": self.profile.tcp_port,
            "embed_mode": self.profile.embed_mode,
            "probe": probe,
            "checks": checks,
            **self._hosting_fields(),
        }
        if stored:
            for key in (
                "plans_registered",
                "started_at",
                "lidb_repo",
                "embed_binary",
                "service",
                "readiness_requires",
                "liveness_interval_sec",
            ):
                if key in stored:
                    base[key] = stored[key]
        if "state_error" in stored:
            base["state_error"] = stored["state_error"]
        if "error" in stored:
            base["error"] = stored["error"]
        return base

    def stop(self) -> None:
        """Clear supervisor state; embedded data dir is preserved."""
        path = state_path(self.data_dir)
        if path.is_file():
            path.unlink()
        try:
            self._prepare_env()
            from liorm import embed_engine

            embed_engine.reset_session_for_tests()
        except Exception:
            pass

    def run_foreground(self, *, interval_sec: int | None = None) -> None:
        """Block after start; re-probe on interval until interrupted."""
        import signal
        import time

        state = self.start()
        interval = interval_sec or (
            self.profile.hosting.liveness_interval_sec if self.profile.hosting else 30
        )
        stop = False

        def _handle(_signum: int, _frame: object) -> None:
            nonlocal stop
            stop = True

        signal.signal(signal.SIGTERM, _handle)
        signal.signal(signal.SIGINT, _handle)

        print(json.dumps(state), flush=True)
        while not stop:
            time.sleep(interval)
            payload = self.status()
            if not payload.get("ready"):
                print(json.dumps(payload), flush=True)
                raise RuntimeError("lis db foreground: readiness probe failed")
