"""Structured registry access log (IP, route, status) for security audit."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any


def _client_ip(headers: dict[str, str]) -> str:
    for key in ("X-Forwarded-For", "x-forwarded-for", "X-Real-IP", "x-real-ip"):
        raw = headers.get(key)
        if raw:
            return raw.split(",")[0].strip()
    return headers.get("X-Client-IP") or headers.get("x-client-ip") or "-"


def log_access(
    *,
    method: str,
    path: str,
    status: int,
    headers: dict[str, str],
    publisher_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    if os.environ.get("LIP_REGISTRY_AUDIT", "1") in ("0", "false", "no"):
        return
    row: dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": "registry.access",
        "method": method,
        "path": path,
        "status": status,
        "client_ip": _client_ip(headers),
    }
    if publisher_id:
        row["publisher_id"] = publisher_id
    if extra:
        row.update(extra)
    line = json.dumps(row, separators=(",", ":"))
    audit_path = os.environ.get("LIP_REGISTRY_AUDIT_LOG", "").strip()
    if audit_path:
        try:
            with open(audit_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            print(line, file=sys.stderr, flush=True)
    else:
        print(line, file=sys.stderr, flush=True)
