#!/usr/bin/env python3
"""Drain pending lidb changefeed JSON lines (stdout). Used by LI_CHANGEFEED_NATIVE=subprocess."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from routes.realtime.lidb_native import discover_lidb_changefeed_lib, LidbChangefeedNative  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: lidb_changefeed_poll_once.py <data_dir>", file=sys.stderr)
        return 2
    lib = discover_lidb_changefeed_lib()
    if lib is None:
        return 1
    data_dir = Path(sys.argv[1])
    native = LidbChangefeedNative(lib, data_dir)
    if not native.available:
        return 1
    try:
        native.subscribe("*")
        for line in native.poll_lines():
            print(line)
    finally:
        native.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
