"""Registry REST handlers (PH-DB-4) — lip OpenAPI v1 paths under /v1."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from routes.auth.handlers import handle_auth_request
from routes.auth.verify import resolve_audit_bearer

from .agent import get_agent_capabilities, remediation_for_error
from .audit_store import query_audit
from .blob_store import get_blob_store, normalize_digest
from .errors import RegistryError
from .peer_store import get_peer_store
from .store import get_registry_store, registry_backend_name

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$")


def _bytes_response(status: int, headers: dict[str, str], payload: bytes) -> tuple[int, dict[str, str], bytes]:
    out = dict(headers)
    out.setdefault("Content-Length", str(len(payload)))
    return status, out, payload


def _json_response(status: int, body: dict[str, Any]) -> tuple[int, dict[str, str], bytes]:
    payload = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(payload)),
    }
    return status, headers, payload


def _error_response(exc: RegistryError) -> tuple[int, dict[str, str], bytes]:
    body: dict[str, Any] = {"error": exc.error, "message": exc.message}
    if exc.details:
        body["details"] = exc.details
    remediation = exc.remediation or remediation_for_error(exc.error, exc.message, exc.details or None)
    if remediation:
        body["remediation"] = remediation
    return _json_response(exc.status, body)


def _parse_bearer(headers: dict[str, str]) -> str | None:
    auth = headers.get("Authorization") or headers.get("authorization")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _query_int(qs: dict[str, list[str]], key: str, default: int) -> int:
    raw = qs.get(key, [str(default)])[0]
    return int(raw)


def _query_bool(qs: dict[str, list[str]], key: str, default: bool) -> bool:
    raw = qs.get(key, ["true" if default else "false"])[0].lower()
    return raw in ("1", "true", "yes")


def handle_request(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    """Dispatch one HTTP request; returns (status, headers, body)."""
    headers = headers or {}
    parsed = urlparse(path)
    route = parsed.path.rstrip("/") or "/"
    qs = parse_qs(parsed.query)

    auth_result = handle_auth_request(method, route, headers=headers, body=body)
    if auth_result is not None:
        return auth_result

    store = get_registry_store()

    if route == "/health":
        backend = registry_backend_name()
        from routes.auth.store import auth_backend_name

        body: dict[str, Any] = {
            "status": "ok",
            "service": "lis-registry",
            "backend": backend,
            "auth": auth_backend_name(),
            "stub": backend == "mock" or backend == "liorm",
        }
        return _json_response(200, body)

    if method == "GET" and route == "/v1/agent/capabilities":
        return _json_response(200, get_agent_capabilities())

    if method == "POST" and route == "/v1/publish/validate":
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return _json_response(
                400,
                {
                    "error": "bad_request",
                    "message": "invalid JSON body",
                    "remediation": "Send JSON with name, version, tree_digest, proof_digest, coverage_pct",
                },
            )
        name = str(payload.get("name") or payload.get("package") or "")
        try:
            result = store.validate_publish(name, payload)
            return _json_response(200, result)
        except RegistryError as exc:
            return _error_response(exc)

    if method == "GET" and route == "/v1/audit":
        if resolve_audit_bearer(_parse_bearer(headers)) is None:
            return _json_response(
                401,
                {
                    "error": "unauthorized",
                    "message": "audit scope bearer or session required",
                    "remediation": "Mint API token with audit scope or login and use session JWT",
                },
            )
        try:
            result = query_audit(
                package=qs.get("package", [None])[0],
                limit=_query_int(qs, "limit", 50),
                offset=_query_int(qs, "offset", 0),
            )
            return _json_response(200, result)
        except ValueError as exc:
            return _json_response(400, {"error": "bad_request", "message": str(exc)})

    if route == "/v1/openapi.yaml":
        from pathlib import Path

        spec = Path(__file__).resolve().parents[2] / "openapi" / "registry-v1.yaml"
        if not spec.is_file():
            return _json_response(404, {"error": "not_found", "message": "openapi spec missing"})
        data = spec.read_bytes()
        return 200, {"Content-Type": "application/yaml", "Content-Length": str(len(data))}, data

    if method == "GET" and route == "/v1/packages":
        try:
            result = store.list_packages(
                name=qs.get("name", [None])[0],
                limit=_query_int(qs, "limit", 50),
                offset=_query_int(qs, "offset", 0),
                include_yanked=_query_bool(qs, "include_yanked", False),
            )
            return _json_response(200, result)
        except (ValueError, RegistryError) as exc:
            if isinstance(exc, RegistryError):
                return _error_response(exc)
            return _json_response(400, {"error": "bad_request", "message": str(exc)})

    m = re.match(r"^/v1/packages/([^/]+)/([^/]+)$", route)
    if method == "GET" and m:
        name, version = m.group(1), m.group(2)
        if not NAME_RE.match(name) or not VERSION_RE.match(version):
            return _json_response(400, {"error": "bad_request", "message": "invalid name or version"})
        try:
            pkg = store.get_package_version(name, version)
            digest = pkg.get("artifact_digest") or pkg.get("tree_digest")
            if digest:
                sources = [{"type": "origin", "url": f"/v1/blobs/{digest}"}]
                sources.extend(get_peer_store().list_for_digest(str(digest)))
                pkg = {**pkg, "sources": sources}
            return _json_response(200, pkg)
        except RegistryError as exc:
            return _error_response(exc)

    m_blob = re.match(r"^/v1/blobs/(.+)$", route)
    if m_blob:
        digest_raw = m_blob.group(1)
        blobs = get_blob_store()
        try:
            digest = normalize_digest(digest_raw)
        except RegistryError as exc:
            return _error_response(exc)
        if method == "HEAD":
            try:
                meta = blobs.head(digest)
                hdrs = {
                    "Content-Type": "application/vnd.li.package+tar",
                    "Content-Length": str(meta["size"]),
                    "Digest": str(meta["digest"]),
                }
                return 200, hdrs, b""
            except RegistryError as exc:
                return _error_response(exc)
        if method == "GET":
            try:
                data, hdrs = blobs.get(digest)
                return _bytes_response(200, hdrs, data)
            except RegistryError as exc:
                return _error_response(exc)
        if method == "PUT":
            try:
                result = blobs.put(digest, body or b"", token=_parse_bearer(headers))
                return _json_response(201 if result.get("stored") else 200, result)
            except RegistryError as exc:
                return _error_response(exc)

    if method == "POST" and route == "/v1/peers/announce":
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return _json_response(400, {"error": "bad_request", "message": "invalid JSON body"})
        try:
            return _json_response(200, get_peer_store().announce(payload))
        except RegistryError as exc:
            return _error_response(exc)

    if method == "GET" and route == "/v1/peers":
        digest_q = qs.get("digest", [None])[0]
        if not digest_q:
            return _json_response(400, {"error": "bad_request", "message": "digest query required"})
        try:
            digest = normalize_digest(digest_q)
            peers = get_peer_store().list_for_digest(digest)
            return _json_response(200, {"digest": digest, "peers": peers})
        except RegistryError as exc:
            return _error_response(exc)

    m_pub = re.match(r"^/v1/packages/([^/]+)/versions$", route)
    if method == "POST" and m_pub:
        name = m_pub.group(1)
        if not NAME_RE.match(name):
            return _json_response(400, {"error": "bad_request", "message": "invalid package name"})
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return _json_response(400, {"error": "bad_request", "message": "invalid JSON body"})
        try:
            result = store.publish(name, payload, token=_parse_bearer(headers))
            return _json_response(201, result)
        except RegistryError as exc:
            return _error_response(exc)

    m_yank = re.match(r"^/v1/packages/([^/]+)/([^/]+)/yank$", route)
    if method == "POST" and m_yank:
        name, version = m_yank.group(1), m_yank.group(2)
        if not NAME_RE.match(name) or not VERSION_RE.match(version):
            return _json_response(400, {"error": "bad_request", "message": "invalid name or version"})
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return _json_response(400, {"error": "bad_request", "message": "invalid JSON body"})
        try:
            result = store.yank(
                name,
                version,
                payload.get("reason", ""),
                token=_parse_bearer(headers),
            )
            return _json_response(200, result)
        except RegistryError as exc:
            return _error_response(exc)

    return _json_response(404, {"error": "not_found", "message": f"no route for {method} {route}"})
