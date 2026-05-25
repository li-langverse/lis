#!/usr/bin/env python3
"""Tier-0 HTTP harness: validate merged TOML + verify request schema (no servers required)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toml_merge import load_toml, merge_http_toml

ROOT = Path(__file__).resolve().parents[1]


def validate_verify_block(cfg: dict) -> list[str]:
    errs: list[str] = []
    verify = cfg.get("verify")
    if verify is None:
        return errs
    if not isinstance(verify, dict):
        return ["[verify] must be a table"]
    requests = verify.get("requests")
    if requests is None:
        return errs
    if not isinstance(requests, list):
        return ["[verify].requests must be an array"]
    for i, req in enumerate(requests):
        if not isinstance(req, dict):
            errs.append(f"verify.requests[{i}] must be a table")
            continue
        if "method" not in req:
            errs.append(f"verify.requests[{i}] missing method")
        if "path" not in req:
            errs.append(f"verify.requests[{i}] missing path")
        if "expect_status" not in req:
            errs.append(f"verify.requests[{i}] missing expect_status")
    return errs


def validate_scenario(name: str, profile: str) -> tuple[bool, str]:
    suite = load_toml(ROOT / "suite.toml")
    prof = suite.get("profiles", {}).get(profile) or suite.get("default", {})
    include = prof.get("include") or []
    if name not in include:
        return False, f"scenario {name!r} not in profile {profile!r} include={include}"

    bench_path = ROOT / "scenarios" / name / "bench.toml"
    if not bench_path.is_file():
        return False, f"missing {bench_path}"

    cfg = merge_http_toml(ROOT, scenario_path=bench_path)
    errs = validate_verify_block(cfg)
    if errs:
        return False, "; ".join(errs)
    if "server" not in cfg and "name" not in cfg:
        return False, "bench.toml needs [server] or name"
    return True, "OK"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("scenario", nargs="?", default="static_small")
    p.add_argument("--profile", default="ci")
    p.add_argument("--all", action="store_true", help="validate all scenarios in profile")
    args = p.parse_args()

    suite = load_toml(ROOT / "suite.toml")
    prof = suite.get("profiles", {}).get(args.profile) or suite.get("default", {})
    names = prof.get("include") or []
    if not args.all:
        names = [args.scenario]

    failed = 0
    for name in names:
        ok, msg = validate_scenario(name, args.profile)
        if ok:
            print(f"verify_http: {name} {msg}")
        else:
            print(f"verify_http: {name} FAIL: {msg}", file=sys.stderr)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
