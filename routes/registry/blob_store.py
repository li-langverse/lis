"""Content-addressed blob store for lip registry artifacts (CAS)."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from .errors import RegistryError

DIGEST_RE = re.compile(r"^sha256:([a-f0-9]{64})$")


def normalize_digest(raw: str) -> str:
    s = raw.strip().lower()
    if not s.startswith("sha256:"):
        s = f"sha256:{s}"
    if not DIGEST_RE.match(s):
        raise RegistryError("bad_request", "digest must be sha256: + 64 hex chars", status=400)
    return s


def blob_root() -> Path:
    root = Path(
        os.environ.get("LIP_BLOB_DIR")
        or os.environ.get("LI_BLOB_DIR")
        or Path(os.environ.get("LI_DATA_DIR", Path.home() / ".local/share/lis/data")) / "blobs"
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def _blob_path(digest: str) -> Path:
    d = normalize_digest(digest)
    hexpart = d.split(":", 1)[1]
    return blob_root() / "sha256" / hexpart[:2] / hexpart[2:]


class BlobStore:
    def head(self, digest: str) -> dict[str, int | str]:
        path = _blob_path(digest)
        if not path.is_file():
            raise RegistryError("not_found", f"blob {digest} not found", status=404)
        st = path.stat()
        return {"digest": normalize_digest(digest), "size": st.st_size}

    def get(self, digest: str) -> tuple[bytes, dict[str, str]]:
        path = _blob_path(digest)
        if not path.is_file():
            raise RegistryError("not_found", f"blob {digest} not found", status=404)
        data = path.read_bytes()
        got = hashlib.sha256(data).hexdigest()
        expected = normalize_digest(digest).split(":", 1)[1]
        if got != expected:
            raise RegistryError("internal", "blob store corruption detected", status=500)
        return data, {
            "Content-Type": "application/vnd.li.package+tar",
            "Content-Length": str(len(data)),
            "Digest": normalize_digest(digest),
        }

    def put(self, digest: str, data: bytes, *, token: str | None) -> dict[str, str | int]:
        from routes.auth.verify import resolve_registry_bearer

        if not token:
            raise RegistryError("unauthorized", "missing bearer token", status=401)
        ctx = resolve_registry_bearer(token)
        if ctx is None:
            raise RegistryError("unauthorized", "invalid or expired bearer token", status=401)
        scope = str(ctx.get("scope", ""))
        if scope not in ("publish", "publish+yank"):
            raise RegistryError("forbidden", "token scope does not allow blob upload", status=403)

        expected = normalize_digest(digest)
        got = hashlib.sha256(data).hexdigest()
        if got != expected.split(":", 1)[1]:
            raise RegistryError(
                "bad_request",
                "body digest mismatch",
                status=400,
                remediation=f"Re-PUT blob at PUT /v1/blobs/{expected} with exact bytes",
                expected=expected,
                computed=f"sha256:{got}",
            )

        path = _blob_path(expected)
        if path.is_file():
            return {"digest": expected, "size": path.stat().st_size, "stored": False}

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(path)
        return {"digest": expected, "size": len(data), "stored": True}


_store: BlobStore | None = None


def get_blob_store() -> BlobStore:
    global _store
    if _store is None:
        _store = BlobStore()
    return _store
