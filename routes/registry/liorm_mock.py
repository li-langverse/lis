"""Mock liorm/lidb registry store (PH-DB-4).

Implements the lidb registry contract until lidb is linkable in-process.
Swap `get_registry_store()` for `liorm.execute(plan_id, params)` when WP1+WP2 land.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RegistryError(Exception):
    def __init__(self, error: str, message: str, status: int = 400, **details: Any) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.status = status
        self.details = details


@dataclass
class PackageVersion:
    name: str
    version: str
    tree_digest: str
    proof_digest: str
    coverage_pct: float
    published_at: str
    pkg_id: str | None = None
    manifest_signature: str | None = None
    publisher_key_id: str | None = None
    yanked: bool = False
    yank_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class MockRegistryStore:
    """In-memory registry backed by JSON under LI_DATA_DIR (stub persistence)."""

    data_dir: Path
    versions: dict[tuple[str, str], PackageVersion] = field(default_factory=dict)

    @classmethod
    def open(cls, data_dir: str | Path | None = None) -> MockRegistryStore:
        root = Path(data_dir or os.environ.get("LI_DATA_DIR", Path.home() / ".local/share/lis/data"))
        store = cls(data_dir=root)
        store._load()
        return store

    def _db_path(self) -> Path:
        return self.data_dir / "registry-mock.json"

    def _load(self) -> None:
        path = self._db_path()
        if not path.is_file():
            self._seed_demo()
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        for row in raw.get("versions", []):
            pv = PackageVersion(**row)
            self.versions[(pv.name, pv.version)] = pv

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {"versions": [v.to_dict() for v in self.versions.values()]}
        self._db_path().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _seed_demo(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        demo = PackageVersion(
            name="pkg-ok",
            version="0.1.0",
            pkg_id="PKG-pkg-ok",
            tree_digest="sha256:" + "a" * 64,
            proof_digest="sha256:" + "b" * 64,
            coverage_pct=85.0,
            published_at=now,
            publisher_key_id="demo-publisher",
        )
        self.versions[(demo.name, demo.version)] = demo
        self._save()

    def list_packages(
        self,
        *,
        name: str | None = None,
        limit: int = 50,
        offset: int = 0,
        include_yanked: bool = False,
    ) -> dict[str, Any]:
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        rows = list(self.versions.values())
        if name:
            rows = [r for r in rows if r.name == name or r.name.startswith(name)]
        if not include_yanked:
            rows = [r for r in rows if not r.yanked]
        rows.sort(key=lambda r: (r.name, r.version))
        total = len(rows)
        page = rows[offset : offset + limit]
        return {
            "packages": [r.to_dict() for r in page],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_package_version(self, name: str, version: str) -> dict[str, Any]:
        key = (name, version)
        if key not in self.versions:
            raise RegistryError("not_found", f"package {name}@{version} not found", status=404)
        pv = self.versions[key]
        if pv.yanked:
            raise RegistryError(
                "gone",
                f"package {name}@{version} is yanked",
                status=410,
                reason=pv.yank_reason,
            )
        return pv.to_dict()

    def publish(self, name: str, body: dict[str, Any], *, token: str | None) -> dict[str, Any]:
        if not token:
            raise RegistryError("unauthorized", "missing bearer token", status=401)
        version = body.get("version")
        if not version:
            raise RegistryError("bad_request", "version is required")
        tree = body.get("tree_digest")
        proof = body.get("proof_digest")
        coverage = body.get("coverage_pct")
        if not tree or not proof or coverage is None:
            raise RegistryError("bad_request", "tree_digest, proof_digest, coverage_pct required")
        if float(coverage) < 80:
            raise RegistryError(
                "forbidden",
                "coverage_pct below minimum (80)",
                status=403,
                coverage_pct=coverage,
            )
        key = (name, version)
        if key in self.versions:
            existing = self.versions[key]
            if existing.tree_digest != tree:
                raise RegistryError(
                    "conflict",
                    "version exists with different tree_digest",
                    status=409,
                )
            return {
                "name": name,
                "version": version,
                "published_at": existing.published_at,
                "index_url": f"/v1/packages/{name}/{version}",
            }
        now = datetime.now(timezone.utc).isoformat()
        pv = PackageVersion(
            name=name,
            version=version,
            tree_digest=tree,
            proof_digest=proof,
            coverage_pct=float(coverage),
            published_at=now,
            pkg_id=body.get("pkg_id"),
            manifest_signature=body.get("manifest_signature"),
            publisher_key_id=body.get("publisher_key_id") or "stub-publisher",
        )
        self.versions[key] = pv
        self._save()
        return {
            "name": name,
            "version": version,
            "published_at": now,
            "index_url": f"/v1/packages/{name}/{version}",
        }

    def yank(self, name: str, version: str, reason: str, *, token: str | None) -> dict[str, Any]:
        if not token:
            raise RegistryError("unauthorized", "missing bearer token", status=401)
        if not reason:
            raise RegistryError("bad_request", "reason is required")
        key = (name, version)
        if key not in self.versions:
            raise RegistryError("not_found", f"package {name}@{version} not found", status=404)
        pv = self.versions[key]
        if pv.yanked:
            raise RegistryError("conflict", "version already yanked", status=409)
        now = datetime.now(timezone.utc).isoformat()
        pv.yanked = True
        pv.yank_reason = reason
        self._save()
        return {"name": name, "version": version, "reason": reason, "yanked_at": now}


_store: MockRegistryStore | None = None


def get_registry_store() -> MockRegistryStore:
    global _store
    if _store is None:
        _store = MockRegistryStore.open()
    return _store


def reset_registry_store() -> None:
    """Test helper: drop cached store."""
    global _store
    _store = None
