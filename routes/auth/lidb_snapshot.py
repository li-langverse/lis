"""Read/write lidb native catalog.heap snapshots (Li-native persistence)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

AUTH_TABLES = frozenset(
    {
        "users",
        "publishers",
        "api_tokens",
        "signup_tokens",
        "device_codes",
        "publisher_members",
    }
)


def catalog_path(data_dir: str | Path) -> Path:
    return Path(data_dir) / ".lidb" / "catalog.heap"


def _split_row(line: str) -> dict[str, str]:
    row: dict[str, str] = {}
    for field in line.split("|"):
        if "=" not in field:
            continue
        key, _, val = field.partition("=")
        row[key.strip()] = val.strip()
    return row


def load_catalog(path: Path) -> dict[str, list[dict[str, str]]]:
    """Parse catalog.heap (@table headers + pipe-separated rows)."""
    tables: dict[str, list[dict[str, str]]] = {}
    if not path.is_file():
        return tables
    current = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("@table:"):
            current = line[7:].strip()
            tables.setdefault(current, [])
            continue
        if not current:
            continue
        tables[current].append(_split_row(line))
    return tables


def _format_row(cols: dict[str, str]) -> str:
    return "|".join(f"{k}={v}" for k, v in cols.items())


def save_catalog(path: Path, tables: dict[str, list[dict[str, str]]]) -> None:
    """Rewrite catalog.heap (same format as lidb_embed native_catalog)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for table in sorted(tables.keys()):
        rows = tables[table]
        if not rows:
            continue
        lines.append(f"@table:{table}")
        for row in rows:
            if row:
                lines.append(_format_row(row))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def merge_auth_tables(
    path: Path,
    *,
    users: list[dict[str, Any]],
    publishers: list[dict[str, Any]],
    api_tokens: list[dict[str, Any]],
    signup_tokens: list[dict[str, Any]],
    device_codes: list[dict[str, Any]],
    publisher_members: list[dict[str, Any]] | None = None,
) -> None:
    """Update auth tables in catalog without dropping registry metadata tables."""

    def _rows(items: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for item in items:
            out.append({k: "" if v is None else str(v) for k, v in item.items()})
        return out

    tables = load_catalog(path)
    tables["users"] = _rows(users)
    tables["publishers"] = _rows(publishers)
    tables["api_tokens"] = _rows(api_tokens)
    tables["signup_tokens"] = _rows(signup_tokens)
    tables["device_codes"] = _rows(device_codes)
    if publisher_members is not None:
        tables["publisher_members"] = _rows(publisher_members)
    else:
        # Keep publisher_members in sync: one owner row per user
        members: list[dict[str, str]] = []
        for u in users:
            pub_id = u.get("publisher_id")
            uid = u.get("id")
            if pub_id and uid:
                members.append(
                    {
                        "publisher_id": str(pub_id),
                        "user_id": str(uid),
                        "role": "owner",
                        "created_at": str(u.get("created_at", "")),
                    }
                )
        tables["publisher_members"] = members
    save_catalog(path, tables)


def ensure_auth_schema(data_dir: str | Path) -> Path:
    """Ensure catalog.heap exists with schema_migrations marker for auth."""
    path = catalog_path(data_dir)
    tables = load_catalog(path)
    if not tables:
        tables = {
            "schema_migrations": [
                {"version": "001_registry", "checksum": "native-n1"},
                {"version": "004_auth_tokens", "checksum": "lis-auth"},
                {"version": "005_registry_security", "checksum": "lis-auth"},
            ],
            "publishers": [],
            "packages": [],
            "package_versions": [],
            "users": [],
            "api_tokens": [],
            "signup_tokens": [],
            "device_codes": [],
            "publisher_members": [],
        }
        save_catalog(path, tables)
        return path
    migrations = {r.get("version") for r in tables.get("schema_migrations", [])}
    changed = False
    for ver in ("004_auth_tokens", "005_registry_security"):
        if ver not in migrations:
            tables.setdefault("schema_migrations", []).append({"version": ver, "checksum": "lis-auth"})
            changed = True
    for t in AUTH_TABLES:
        if t not in tables:
            tables[t] = []
            changed = True
    if changed:
        save_catalog(path, tables)
    return path
