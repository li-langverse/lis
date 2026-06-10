"""Registry-mediated peer announcements for P2P blob fetch."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .blob_store import normalize_digest
from .errors import RegistryError


@dataclass
class PeerRecord:
    endpoint: str
    digests: list[str] = field(default_factory=list)
    capacity_bytes: int = 0
    ttl_sec: int = 3600
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PeerStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.peers: dict[str, PeerRecord] = {}
        self._load()

    @classmethod
    def open(cls, data_dir: str | Path | None = None) -> PeerStore:
        root = Path(data_dir or os.environ.get("LI_DATA_DIR", Path.home() / ".local/share/lis/data"))
        return cls(root)

    def _path(self) -> Path:
        return self.data_dir / "registry-peers.json"

    def _load(self) -> None:
        p = self._path()
        if not p.is_file():
            return
        raw = json.loads(p.read_text(encoding="utf-8"))
        for endpoint, row in (raw.get("peers") or {}).items():
            self.peers[endpoint] = PeerRecord(endpoint=endpoint, **{k: v for k, v in row.items() if k != "endpoint"})

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {"peers": {k: v.to_dict() for k, v in self.peers.items()}}
        self._path().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def announce(self, body: dict[str, Any]) -> dict[str, Any]:
        endpoint = str(body.get("endpoint", "")).strip().rstrip("/")
        if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
            raise RegistryError("bad_request", "endpoint must be http(s) URL", status=400)
        digests = [normalize_digest(str(d)) for d in body.get("digests") or []]
        if not digests:
            raise RegistryError("bad_request", "digests required", status=400)
        now = datetime.now(timezone.utc).isoformat()
        rec = PeerRecord(
            endpoint=endpoint,
            digests=sorted(set(digests)),
            capacity_bytes=int(body.get("capacity_bytes") or 0),
            ttl_sec=int(body.get("ttl_sec") or 3600),
            updated_at=now,
        )
        self.peers[endpoint] = rec
        self._save()
        return {"endpoint": endpoint, "digests": len(rec.digests), "updated_at": now}

    def list_for_digest(self, digest: str) -> list[dict[str, Any]]:
        want = normalize_digest(digest)
        out: list[dict[str, Any]] = []
        for rec in self.peers.values():
            if want in rec.digests:
                out.append({"type": "peer", "url": rec.endpoint, "last_seen": rec.updated_at})
        return out


_store: PeerStore | None = None


def get_peer_store() -> PeerStore:
    global _store
    if _store is None:
        _store = PeerStore.open()
    return _store
