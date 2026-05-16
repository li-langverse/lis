#!/usr/bin/env python3
"""Scan nginx CHANGES for Security: lines; sync nginx_mitigations.toml stubs."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
NGINX = ROOT / "third_party" / "nginx"
CHANGES = NGINX / "CHANGES"
MITIGATIONS = ROOT / "nginx_mitigations.toml"
EXPLOITS = ROOT / "exploits"

SECURITY_RE = re.compile(r"Security:\s*(.+)", re.IGNORECASE)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return s[:64] or "security_issue"


def load_existing() -> list[dict]:
    if not MITIGATIONS.is_file():
        return []
    data = tomllib.loads(MITIGATIONS.read_text(encoding="utf-8"))
    return list(data.get("mitigation") or [])


def write_mitigations(rows: list[dict], dry_run: bool) -> None:
    lines = [
        "# Machine-readable nginx audit — see docs/security-nginx-src-audit.md",
        "",
    ]
    for row in rows:
        lines.append("[[mitigation]]")
        for k, v in row.items():
            if isinstance(v, bool):
                lines.append(f"{k} = {'true' if v else 'false'}")
            elif isinstance(v, list):
                inner = ", ".join(f'"{x}"' for x in v)
                lines.append(f"{k} = [{inner}]")
            else:
                lines.append(f'{k} = "{v}"')
        lines.append("")
    text = "\n".join(lines) + "\n"
    if dry_run:
        print(text[:2000], "..." if len(text) > 2000 else "")
        return
    MITIGATIONS.write_text(text, encoding="utf-8")


def scan_changes() -> list[dict]:
    found: list[dict] = []
    if not CHANGES.is_file():
        return found
    for line in CHANGES.read_text(encoding="utf-8", errors="replace").splitlines():
        m = SECURITY_RE.search(line)
        if not m:
            continue
        note = m.group(1).strip()
        mid = slugify(note)
        found.append(
            {
                "id": mid,
                "notes": note,
                "li_invariant": f"TBD: {note[:120]}",
                "exploit": f"exploits/{mid}.toml",
                "li_done": False,
            }
        )
    return found


def merge_rows(existing: list[dict], scanned: list[dict]) -> list[dict]:
    by_id = {r["id"]: r for r in existing if r.get("id")}
    for row in scanned:
        if row["id"] not in by_id:
            by_id[row["id"]] = row
    return sorted(by_id.values(), key=lambda r: r.get("id", ""))


def ensure_exploit_stubs(rows: list[dict], dry_run: bool) -> int:
    created = 0
    EXPLOITS.mkdir(parents=True, exist_ok=True)
    for row in rows:
        ex = row.get("exploit", "")
        if not ex.startswith("exploits/"):
            continue
        path = ROOT / ex
        if path.is_file():
            continue
        stub = f'''id = "{row.get("id", path.stem)}"
tier = "A"
enabled = false

[expect]
no_crash = true
reject_or_close_attack = true
'''
        if dry_run:
            print(f"would create {path}")
        else:
            path.write_text(stub, encoding="utf-8")
        created += 1
    return created


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    existing = load_existing()
    scanned = scan_changes()
    if not scanned and not NGINX.is_dir():
        print(
            "audit_nginx_src: no third_party/nginx — init submodule or keep hand-curated mitigations",
            file=sys.stderr,
        )
    merged = merge_rows(existing, scanned)
    write_mitigations(merged, args.dry_run)
    n = ensure_exploit_stubs(merged, args.dry_run)
    print(f"audit_nginx_src: {len(merged)} mitigations, {n} exploit stubs, nginx={NGINX.is_dir()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
