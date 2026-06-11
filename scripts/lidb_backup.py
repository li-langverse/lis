#!/usr/bin/env python3
"""Li-native backup/restore for lip registry (lidb catalog + content-addressed blobs)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_LIS_ROOT = Path(__file__).resolve().parents[1]
if str(_LIS_ROOT) not in sys.path:
    sys.path.insert(0, str(_LIS_ROOT))


def _data_dir() -> Path:
    return Path(os.environ.get("LI_DATA_DIR", Path.home() / ".local/share/lis/data"))


def _blob_dir(data_dir: Path) -> Path:
    raw = os.environ.get("LIP_BLOB_DIR", "").strip()
    if raw:
        return Path(raw)
    return data_dir / "blobs"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_backup(out_path: Path) -> dict[str, object]:
    data_dir = _data_dir()
    blob_dir = _blob_dir(data_dir)
    catalog = data_dir / ".lidb" / "catalog.heap"
    if not catalog.is_file():
        return {"ok": False, "error": f"missing lidb catalog: {catalog}"}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "format": "lis-registry-backup",
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_dir": str(data_dir),
        "files": {},
    }

    with tempfile.TemporaryDirectory(prefix="lis-backup-") as tmp:
        stage = Path(tmp)
        lidb_stage = stage / ".lidb"
        lidb_stage.mkdir()
        shutil.copy2(catalog, lidb_stage / "catalog.heap")
        manifest["files"][".lidb/catalog.heap"] = _sha256_file(lidb_stage / "catalog.heap")

        if blob_dir.is_dir():
            shutil.copytree(blob_dir, stage / "blobs", dirs_exist_ok=True)
            blob_manifest: dict[str, str] = {}
            for fp in sorted((stage / "blobs").rglob("*")):
                if fp.is_file():
                    rel = str(fp.relative_to(stage)).replace("\\", "/")
                    blob_manifest[rel] = _sha256_file(fp)
            manifest["blob_count"] = len(blob_manifest)
            manifest["files"].update(blob_manifest)

        mock = data_dir / "auth-mock.json"
        if mock.is_file():
            shutil.copy2(mock, stage / "auth-mock.json")
            manifest["files"]["auth-mock.json"] = _sha256_file(stage / "auth-mock.json")

        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        with tarfile.open(out_path, "w:gz") as tar:
            for item in stage.rglob("*"):
                if item.is_file():
                    tar.add(item, arcname=item.relative_to(stage).as_posix())

    return {"ok": True, "path": str(out_path), "bytes": out_path.stat().st_size, **manifest}


def cmd_restore(archive: Path, *, force: bool = False) -> dict[str, object]:
    data_dir = _data_dir()
    if data_dir.exists() and any(data_dir.iterdir()) and not force:
        return {
            "ok": False,
            "error": f"data_dir not empty: {data_dir} (pass --force)",
        }

    with tempfile.TemporaryDirectory(prefix="lis-restore-") as tmp:
        stage = Path(tmp)
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(stage)
        manifest_path = stage / "manifest.json"
        if not manifest_path.is_file():
            return {"ok": False, "error": "backup missing manifest.json"}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != "lis-registry-backup":
            return {"ok": False, "error": "not a lis-registry-backup archive"}

        data_dir.mkdir(parents=True, exist_ok=True)
        catalog_src = stage / ".lidb" / "catalog.heap"
        if catalog_src.is_file():
            dest = data_dir / ".lidb"
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(catalog_src, dest / "catalog.heap")

        blobs_src = stage / "blobs"
        if blobs_src.is_dir():
            blob_dest = _blob_dir(data_dir)
            if blob_dest.exists() and force:
                shutil.rmtree(blob_dest)
            shutil.copytree(blobs_src, blob_dest, dirs_exist_ok=True)

        mock_src = stage / "auth-mock.json"
        if mock_src.is_file():
            shutil.copy2(mock_src, data_dir / "auth-mock.json")

    return {"ok": True, "restored_to": str(data_dir), "created_at": manifest.get("created_at")}


def cmd_import_auth(mock_path: Path) -> dict[str, object]:
    from routes.auth.lidb_store import import_mock_json
    from routes.auth.lidb_snapshot import ensure_auth_schema

    data_dir = _data_dir()
    ensure_auth_schema(data_dir)
    counts = import_mock_json(data_dir, mock_path)
    return {"ok": True, "data_dir": str(data_dir), "imported": counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Li-native lip registry backup")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_backup = sub.add_parser("backup", help="Create .tar.gz of lidb catalog + blobs")
    p_backup.add_argument("-o", "--output", required=True, help="Output .tar.gz path")

    p_restore = sub.add_parser("restore", help="Restore from .tar.gz")
    p_restore.add_argument("archive", help="Backup .tar.gz")
    p_restore.add_argument("--force", action="store_true", help="Overwrite non-empty data dir")

    p_import = sub.add_parser("import-auth", help="Import auth-mock.json into lidb catalog")
    p_import.add_argument("mock_json", help="Path to auth-mock.json")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "backup":
            out = cmd_backup(Path(args.output))
        elif args.cmd == "restore":
            out = cmd_restore(Path(args.archive), force=args.force)
        else:
            out = cmd_import_auth(Path(args.mock_json))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
