"""Queryable registry audit trail (in-memory + optional JSONL file)."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()
_entries: list[dict[str, Any]] = []
_MAX_MEMORY = 10_000


def _audit_file() -> Path | None:
    explicit = os.environ.get("LIP_REGISTRY_AUDIT_LOG", "").strip()
    if explicit:
        return Path(explicit)
    data = os.environ.get("LI_DATA_DIR", "").strip()
    if data:
        return Path(data) / "registry-audit.jsonl"
    return None


def append_event(row: dict[str, Any]) -> None:
    with _lock:
        _entries.append(dict(row))
        if len(_entries) > _MAX_MEMORY:
            del _entries[: len(_entries) - _MAX_MEMORY]
    path = _audit_file()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    except OSError:
        pass


def query_audit(
    *,
    package: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    with _lock:
        rows = list(_entries)
    if not rows:
        path = _audit_file()
        if path and path.is_file():
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    rows.append(json.loads(line))
            except (OSError, json.JSONDecodeError):
                pass
    if package:
        rows = [r for r in rows if r.get("package_name") == package or package in str(r.get("path", ""))]
    rows.sort(key=lambda r: str(r.get("ts") or r.get("occurred_at") or ""), reverse=True)
    total = len(rows)
    page = rows[offset : offset + limit]
    return {"events": page, "total": total, "limit": limit, "offset": offset}


def reset_audit_store() -> None:
    with _lock:
        _entries.clear()
