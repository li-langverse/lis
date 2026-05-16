#!/usr/bin/env bash
set -euo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"
python3 <<'PY'
import sys
from pathlib import Path
try:
    import tomllib
    def load(p: Path):
        return tomllib.loads(p.read_text(encoding="utf-8"))
except ImportError:
    import tomli as tomllib
    def load(p: Path):
        return tomllib.loads(p.read_bytes())
errors = []
files = [p for p in Path(".").rglob("*.toml") if ".git" not in p.parts]
for p in sorted(files):
    try:
        load(p)
    except Exception as e:
        errors.append(f"{p}: {e}")
if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"TOML OK ({len(files)} files)")
PY
