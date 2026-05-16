#!/usr/bin/env python3
"""HTTP bench harness — TOML-driven; nginx/li-httpd when binaries exist, else verify-only."""

from __future__ import annotations

import argparse
import csv
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from toml_merge import merge_http_toml, parse_set_args

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT.parent.parent / "results"
CSV_HEADER = [
    "benchmark",
    "lang",
    "variant",
    "threads",
    "metric",
    "value",
    "unit",
    "git_sha",
    "cpu_model",
    "flags",
]


def git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT.parent.parent.parent,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def run_verify_only(cfg: dict, scenario: str) -> bool:
    from verify_http import validate_verify_block

    errs = validate_verify_block(cfg)
    if errs:
        print(f"bench_http: verify schema errors: {errs}", file=sys.stderr)
        return False
    print(f"bench_http: verify-only OK ({scenario})")
    return True


def write_stub_csv(scenario: str, profile: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "latest.csv"
    sha = git_sha()
    cpu = platform.processor() or platform.machine()
    rows = [
        [scenario, "harness", profile, 0, "verify_only", 1.0, "bool", sha, cpu, "stub"],
    ]
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        w.writerows(rows)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("scenario", nargs="?", default="static_small")
    p.add_argument("--profile", default="ci")
    p.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="key=value",
        help="override merged TOML",
    )
    p.add_argument("--timing", action="store_true", help="run load phase (needs wrk + servers)")
    args = p.parse_args()

    bench_path = ROOT / "scenarios" / args.scenario / "bench.toml"
    if not bench_path.is_file():
        print(f"missing {bench_path}", file=sys.stderr)
        return 1

    overrides = parse_set_args(args.set) if args.set else None
    cfg = merge_http_toml(ROOT, scenario_path=bench_path, overrides=overrides)

    suite_path = ROOT / "suite.toml"
    if suite_path.is_file():
        import tomllib

        suite = tomllib.loads(suite_path.read_text(encoding="utf-8"))
        prof = suite.get("profiles", {}).get(args.profile) or suite.get("default", {})
        timing = prof.get("timing", False)
    else:
        timing = False

    if args.timing:
        timing = True

    if not run_verify_only(cfg, args.scenario):
        return 1

    csv_path = write_stub_csv(args.scenario, args.profile)
    print(f"bench_http: wrote {csv_path}")

    if timing:
        print(
            "bench_http: timing requested but li-httpd/nginx not wired — "
            "use --profile nightly after servers ship",
            file=sys.stderr,
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
