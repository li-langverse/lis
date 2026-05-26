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

  def start(self) -> dict[str, Any]:
      """Migrate, register plans, persist ready state (no TCP for registry-min)."""
      embed = self._prepare_env()
      from liorm import embed_engine

      embed_engine.reset_session_for_tests()
      session = embed_engine.EmbeddedSession(self.data_dir)
      if not session.open_and_migrate():
          raise RuntimeError("lidb open/migrate failed")
      plans = self.register_plans()
      if not embed_engine.probe_engine_ready():
          raise RuntimeError("embedded engine probe failed after migrate")
      session.close()

      if self.profile.tcp_port and self.profile.embed_mode != "in_process":
          # TCP wire deferred until profile requests it (PH-DB-4+).
          raise NotImplementedError(f"tcp listen on port {self.profile.tcp_port} not implemented")

      state = {
          "ready": True,
          "profile": self.profile.name,
          "data_dir": str(self.data_dir),
          "lidb_repo": str(self.lidb_repo),
          "catalog": str(heap_catalog_path(self.data_dir)),
          "migrated": True,
          "engine": "lidb_embed",
          "embed_binary": str(embed),
          "plans_registered": plans,
          "tcp_listen": False,
          "tcp_port": self.profile.tcp_port,
          "started_at": datetime.now(timezone.utc).isoformat(),
      }
      path = state_path(self.data_dir)
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
      os.environ["LI_PROFILE"] = self.profile.name
      return state

  def status(self) -> dict[str, Any]:
      """Return health JSON; probe engine when state file exists."""
      path = state_path(self.data_dir)
      base: dict[str, Any] = {
          "ready": False,
          "profile": self.profile.name,
          "data_dir": str(self.data_dir),
          "state_file": str(path),
          "catalog": str(heap_catalog_path(self.data_dir)),
          "migrated": heap_catalog_path(self.data_dir).is_file(),
          "engine": "lidb_embed",
          "tcp_listen": False,
      }
      if path.is_file():
          try:
              stored = json.loads(path.read_text(encoding="utf-8"))
              base.update({k: stored[k] for k in stored if k != "ready"})
          except json.JSONDecodeError:
              base["state_error"] = "invalid db-state.json"

      if not base["migrated"]:
          return base

      try:
          self._prepare_env()
          from liorm import embed_engine

          embed_engine.reset_session_for_tests()
          session = embed_engine.EmbeddedSession(self.data_dir)
          if session.open_and_migrate() and embed_engine.probe_engine_ready():
              base["ready"] = True
              base["probe"] = "ok"
          session.close()
      except Exception as exc:  # noqa: BLE001 — status must report failure
          base["probe"] = "failed"
          base["error"] = str(exc)

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
