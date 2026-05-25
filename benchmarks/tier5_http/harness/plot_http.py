#!/usr/bin/env python3
"""Plot tier5_http results/latest.csv — stub until share PNG pipeline lands."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT.parent.parent / "results" / "latest.csv"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, default=RESULTS)
    args = p.parse_args()
    if not args.csv.is_file():
        print(f"plot_http: missing {args.csv}", file=sys.stderr)
        return 1
    print(f"plot_http: stub OK ({args.csv.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
