"""Merge tier5_http TOML: defaults <- scenario <- overrides."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, val in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def merge_http_toml(
    root: Path,
    *,
    defaults_name: str = "defaults.toml",
    scenario_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    defaults = root / defaults_name
    if defaults.is_file():
        merged = load_toml(defaults)
    if scenario_path and scenario_path.is_file():
        merged = deep_merge(merged, load_toml(scenario_path))
    if overrides:
        merged = deep_merge(merged, overrides)
    return merged


def parse_set_args(pairs: list[str]) -> dict[str, Any]:
    """Parse --set key=value (dotted keys -> nested dict)."""
    out: dict[str, Any] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"invalid --set (need key=value): {item}")
        key, _, raw = item.partition("=")
        parts = key.split(".")
        cur = out
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = raw
    return out
