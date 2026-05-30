#!/usr/bin/env python3
"""Native lidb embed lifecycle for lis db supervisor (PH-DB-3)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _lis_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_lidb_root() -> Path | None:
    env = os.environ.get("LIDB_ROOT", "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env))
    lis_root = _lis_root()
    candidates.append(lis_root.parent / "lidb")
    candidates.append(lis_root / "vendor" / "lidb")
    for path in candidates:
        if (path / "liorm" / "embed_engine.py").is_file():
            return path.resolve()
    return None


def _setup_path() -> Path:
    root = resolve_lidb_root()
    if root is None:
        raise RuntimeError("lidb checkout not found — set LIDB_ROOT to li-langverse/lidb")
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    os.environ.setdefault("LIDB_ROOT", root_s)
    return root


def _apply_data_dir(data_dir: str) -> None:
    os.environ["LIDB_DATA_DIR"] = data_dir
    os.environ["LI_DATA_DIR"] = data_dir


def cmd_ensure(data_dir: str) -> dict[str, object]:
    _setup_path()
    _apply_data_dir(data_dir)
    from liorm.embed_engine import ensure_session, probe_engine_ready

    session = ensure_session()
    if session is None or not probe_engine_ready():
        return {"ok": False, "error": "native lidb_embed unavailable (build lidb_embed or set LIDB_EMBED)"}
    catalog = Path(data_dir) / ".lidb" / "catalog.heap"
    return {
        "ok": True,
        "backend": "native",
        "catalog_path": str(catalog),
        "catalog_bytes": catalog.stat().st_size if catalog.is_file() else 0,
    }


def cmd_status(data_dir: str) -> dict[str, object]:
    _setup_path()
    _apply_data_dir(data_dir)
    catalog = Path(data_dir) / ".lidb" / "catalog.heap"
    out: dict[str, object] = {
        "ok": catalog.is_file() and catalog.stat().st_size > 0,
        "backend": "native",
        "catalog_path": str(catalog),
        "data_dir": data_dir,
    }
    if not out["ok"]:
        out["engine_ready"] = False
        return out
    try:
        from liorm.embed_engine import probe_engine_ready

        out["engine_ready"] = probe_engine_ready()
    except Exception as exc:  # noqa: BLE001
        out["engine_ready"] = False
        out["error"] = str(exc)
    return out


def cmd_migrate(data_dir: str, to_rev: str = "head") -> dict[str, object]:
    ensured = cmd_ensure(data_dir)
    if not ensured.get("ok"):
        return ensured
    Path(data_dir).joinpath(".lis-db-migrate-rev").write_text(to_rev + "\n", encoding="utf-8")
    return {"ok": True, "to": to_rev, **ensured}


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "usage: lidb_engine.py ensure|status|migrate <data-dir> [to-rev]",
                }
            )
        )
        return 2
    cmd, data_dir = argv[1], argv[2]
    to_rev = argv[3] if len(argv) > 3 else "head"
    try:
        if cmd == "ensure":
            out = cmd_ensure(data_dir)
        elif cmd == "status":
            out = cmd_status(data_dir)
        elif cmd == "migrate":
            out = cmd_migrate(data_dir, to_rev)
        else:
            out = {"ok": False, "error": f"unknown command: {cmd}"}
    except Exception as exc:  # noqa: BLE001
        out = {"ok": False, "error": str(exc)}
    print(json.dumps(out))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
