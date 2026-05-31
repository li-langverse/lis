#!/usr/bin/env python3
"""Li Data Studio bridge — read-only lidb catalog, rows, and SQL (PH-DB-11)."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


def _lis_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_lidb_root() -> Path | None:
    env = os.environ.get("LIDB_ROOT", "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env))
    lis_root = _lis_root()
    candidates.append(lis_root.parent / "lidb")
    candidates.append(lis_root / "vendor" / "lidb")
    for path in candidates:
        if (path / "liorm" / "catalog.py").is_file():
            return path.resolve()
    return None


def _setup() -> None:
    root = _resolve_lidb_root()
    if root is None:
        raise RuntimeError("lidb checkout not found — set LIDB_ROOT")
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    os.environ.setdefault("LIDB_ROOT", root_s)
    data_dir = os.environ.get("LI_DATA_DIR", "").strip()
    if not data_dir:
        home = Path.home()
        data_dir = str(home / ".local" / "share" / "lis" / "data")
    os.environ["LIDB_DATA_DIR"] = data_dir
    os.environ["LI_DATA_DIR"] = data_dir


def _columns_for_table(table_key: str) -> list[str]:
    from liorm.catalog import CATALOG_ALLOWLIST

    allowed = CATALOG_ALLOWLIST.get(table_key)
    if allowed is None:
        return []
    return sorted(allowed)


def cmd_catalog() -> dict[str, Any]:
    _setup()
    from liorm.catalog import CATALOG_ALLOWLIST

    tables: list[dict[str, Any]] = []
    for key in sorted(CATALOG_ALLOWLIST):
        schema, name = key.split(".", 1)
        cols = _columns_for_table(key)
        tables.append({"schema": schema, "name": name, "key": key, "columns": cols})
    return {"ok": True, "tables": tables, "count": len(tables)}


def _validate_table(raw: str) -> str:
    from liorm.catalog import resolve_table

    schema, name = resolve_table(raw)
    return f"{schema}.{name}"


def cmd_rows(table: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    _setup()
    from liorm.embed_engine import ensure_session, execute_sql

    key = _validate_table(table)
    _, bare = key.split(".", 1)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    if ensure_session() is None:
        return {"ok": False, "error": "lidb embed unavailable — run `lis db start`"}
    sql = f'SELECT * FROM "{bare}" LIMIT ? OFFSET ?'
    rows = execute_sql(sql, [limit, offset])
    columns = sorted({k for row in rows for k in row}) if rows else _columns_for_table(key)
    return {"ok": True, "table": key, "columns": columns, "rows": rows, "limit": limit, "offset": offset}


_READ_ONLY_RE = re.compile(
    r"^\s*(select|with)\b",
    re.IGNORECASE | re.DOTALL,
)
_FORBIDDEN_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|attach|detach|pragma)\b",
    re.IGNORECASE,
)


def _validate_readonly_sql(sql: str) -> str:
    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise ValueError("empty SQL")
    if ";" in cleaned:
        raise ValueError("only single-statement SELECT queries are allowed")
    if not _READ_ONLY_RE.match(cleaned):
        raise ValueError("only SELECT / WITH queries are allowed")
    if _FORBIDDEN_RE.search(cleaned):
        raise ValueError("mutating or DDL statements are not allowed")
    return cleaned


def cmd_query(sql: str, limit: int = 200) -> dict[str, Any]:
    _setup()
    from liorm.embed_engine import ensure_session, execute_sql

    safe = _validate_readonly_sql(sql)
    limit = max(1, min(limit, 500))
    if ensure_session() is None:
        return {"ok": False, "error": "lidb embed unavailable — run `lis db start`"}
    wrapped = f"SELECT * FROM ({safe}) AS _studio_q LIMIT ?"
    rows = execute_sql(wrapped, [limit])
    columns = sorted({k for row in rows for k in row}) if rows else []
    return {"ok": True, "columns": columns, "rows": rows, "row_count": len(rows), "limit": limit}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(json.dumps({"ok": False, "error": "usage: lidb_studio_bridge.py catalog|rows|query ..."}))
        return 2
    cmd = argv[1]
    try:
        if cmd == "catalog":
            out = cmd_catalog()
        elif cmd == "rows":
            if len(argv) < 3:
                raise ValueError("usage: rows <table> [limit] [offset]")
            table = argv[2]
            lim = int(argv[3]) if len(argv) > 3 else 100
            off = int(argv[4]) if len(argv) > 4 else 0
            out = cmd_rows(table, lim, off)
        elif cmd == "query":
            if len(argv) < 3:
                raise ValueError("usage: query <sql>")
            sql = argv[2] if len(argv) == 3 else " ".join(argv[2:])
            out = cmd_query(sql)
        else:
            out = {"ok": False, "error": f"unknown command: {cmd}"}
    except Exception as exc:  # noqa: BLE001
        out = {"ok": False, "error": str(exc)}
    print(json.dumps(out))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
