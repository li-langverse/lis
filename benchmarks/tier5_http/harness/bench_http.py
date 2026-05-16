#!/usr/bin/env python3
"""HTTP bench harness — infra: validate TOML only until li-httpd binary exists."""
import argparse
import sys
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("scenario", nargs="?", default="static_small")
    p.add_argument("--profile", default="ci")
    p.add_argument("--stub", action="store_true", default=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    bench = root / "scenarios" / args.scenario / "bench.toml"
    if not bench.is_file():
        print(f"missing {bench}", file=sys.stderr)
        return 1
    print(f"bench_http: stub OK ({args.scenario}, profile={args.profile})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
