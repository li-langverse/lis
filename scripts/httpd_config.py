#!/usr/bin/env python3
"""Easy li-httpd TOML desugar + validate (M1 prep — no Li binary required)."""

from __future__ import annotations

import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    pass


ROUTE_KEY_RE = re.compile(
    r"^(?P<method>[A-Z]+)\s+(?P<path>/[^\s#]+)(?:\s+(?P<extras>.+))?$"
)
HEADER_EXTRA_RE = re.compile(r"^([a-zA-Z0-9_-]+)=([^\s]+)$")


@dataclass
class CanonicalRoute:
    name: str
    method: str
    path: str
    path_kind: str  # exact | prefix | prefix_strip
    action: str
    headers: dict[str, str]
    priority: int


def slug_route_name(method: str, path: str) -> str:
    s = f"{method.lower()}_{path.strip('/')}".replace("/", "_").replace("*", "wild")
    s = re.sub(r"[^a-z0-9_]+", "_", s).strip("_")
    return s or "route"


def parse_path_kind(path: str) -> tuple[str, str]:
    if path.endswith("/**"):
        return path[:-3], "prefix_strip"
    if path.endswith("/*"):
        return path[:-2], "prefix"
    return path, "exact"


def parse_route_key(key: str, action: str, priority: int) -> CanonicalRoute:
    m = ROUTE_KEY_RE.match(key.strip())
    if not m:
        raise ConfigError(f"invalid route key: {key!r}")
    method = m.group("method")
    raw_path = m.group("path")
    extras = (m.group("extras") or "").strip()
    headers: dict[str, str] = {}
    if extras:
        for part in extras.split():
            hm = HEADER_EXTRA_RE.match(part)
            if not hm:
                raise ConfigError(f"invalid route extra: {part!r} in {key!r}")
            headers[hm.group(1).lower()] = hm.group(2)
    if ".." in raw_path or "//" in raw_path.replace("://", ""):
        raise ConfigError(f"path must not contain .. or //: {raw_path}")
    norm_path, kind = parse_path_kind(raw_path)
    return CanonicalRoute(
        name=slug_route_name(method, raw_path),
        method=method,
        path=norm_path,
        path_kind=kind,
        action=str(action).strip().strip('"'),
        headers=headers,
        priority=priority,
    )


def desugar_config(data: dict[str, Any]) -> list[CanonicalRoute]:
    routes_tbl = data.get("routes")
    if routes_tbl is None:
        return []
    if not isinstance(routes_tbl, dict):
        raise ConfigError("[routes] must be a table (map)")
    out: list[CanonicalRoute] = []
    for i, (key, action) in enumerate(routes_tbl.items()):
        out.append(parse_route_key(str(key), str(action), priority=i))
    return out


def routes_overlap(a: CanonicalRoute, b: CanonicalRoute) -> bool:
    if a.method != b.method and a.method != "*" and b.method != "*":
        return False
    if a.path_kind == "exact" and b.path_kind == "exact":
        return a.path == b.path
    if a.path_kind in ("prefix", "prefix_strip") and b.path_kind in ("prefix", "prefix_strip"):
        pa, pb = a.path.rstrip("/"), b.path.rstrip("/")
        return pa == pb or pa.startswith(pb + "/") or pb.startswith(pa + "/")
    return a.path == b.path


def validate_routes(routes: list[CanonicalRoute]) -> None:
    for i, a in enumerate(routes):
        for b in routes[i + 1 :]:
            if routes_overlap(a, b) and a.priority != b.priority:
                continue
            if routes_overlap(a, b):
                raise ConfigError(
                    f"overlapping routes at same priority: {a.name} vs {b.name}"
                )


def load_httpd_config(path: Path) -> list[CanonicalRoute]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    routes = desugar_config(data)
    validate_routes(routes)
    return routes


def explain(routes: list[CanonicalRoute]) -> str:
    lines = ["# canonical routes (desugared)"]
    for r in routes:
        hdr = " ".join(f"{k}={v}" for k, v in sorted(r.headers.items()))
        extra = f" [{hdr}]" if hdr else ""
        lines.append(
            f"[[routes]]\n"
            f'name = "{r.name}"\n'
            f"priority = {r.priority}\n"
            f'method = "{r.method}"\n'
            f'path = "{r.path}"\n'
            f'path_kind = "{r.path_kind}"\n'
            f'action = "{r.action}"{extra}\n'
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: httpd_config.py <config.toml> [--explain]", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    routes = load_httpd_config(path)
    if "--explain" in sys.argv:
        print(explain(routes), end="")
    else:
        print(f"OK: {len(routes)} routes")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        sys.exit(1)
