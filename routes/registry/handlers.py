"""Registry REST handlers (PH-DB-4) — lip OpenAPI v1 paths under /v1."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from .liorm_mock import RegistryError, get_registry_store

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$")


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
    store = get_registry_store()

    if route == "/health":
        return _json_response(200, {"status": "ok", "service": "lis-registry", "stub": True})

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
            return _json_response(200, store.get_package_version(name, version))
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
