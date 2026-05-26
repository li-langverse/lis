"""Load registry-min (and future) profile TOML."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlanSpec:
    name: str
    liq: str


@dataclass(frozen=True)
class HostingSpec:
    service: str
    readiness_requires: tuple[str, ...]
    liveness_interval_sec: int


@dataclass(frozen=True)
class Profile:
    name: str
    search_path: str
    embed_mode: str
    tcp_port: int
    migration: str
    modules: dict[str, bool]
    verticals: list[str]
    plans: list[PlanSpec]
    hosting: HostingSpec | None


def _parse_hosting(data: dict) -> HostingSpec | None:
    raw = data.get("hosting")
    if not raw:
        return None
    requires = raw.get("readiness_requires", ["catalog", "engine", "plans"])
    if isinstance(requires, str):
        requires = [requires]
    return HostingSpec(
        service=str(raw.get("service", "lis-db")),
        readiness_requires=tuple(str(r) for r in requires),
        liveness_interval_sec=int(raw.get("liveness_interval_sec", 30)),
    )


def load_profile(path: Path) -> Profile:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    prof = data.get("profile", {})
    modules = {k: bool(v) for k, v in data.get("modules", {}).items()}
    verticals = [v.get("id", "") for v in data.get("vertical", []) if v.get("id")]
    plans = [
        PlanSpec(name=p["name"], liq=p["liq"].strip())
        for p in data.get("plan", [])
        if p.get("name") and p.get("liq")
    ]
    return Profile(
        name=str(prof.get("name", path.stem)),
        search_path=str(prof.get("search_path", "public")),
        embed_mode=str(prof.get("embed_mode", "in_process")),
        tcp_port=int(prof.get("tcp_port", 0)),
        migration=str(prof.get("migration", "001_registry.sql")),
        modules=modules,
        verticals=verticals,
        plans=plans,
        hosting=_parse_hosting(data),
    )
