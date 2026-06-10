"""Stdio MCP server mapping registry + auth tools to REST /v1/*."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


def _base_url() -> str:
    url = os.environ.get("LIP_REGISTRY_URL", "http://127.0.0.1:54321/v1").rstrip("/")
    return url if url.endswith("/v1") else f"{url}/v1"


def _token() -> str | None:
    tok = os.environ.get("LIP_REGISTRY_TOKEN", "").strip()
    return tok or None


def _request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    token: str | None = None,
) -> dict[str, Any]:
    url = f"{_base_url()}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    bearer = token if token is not None else _token()
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": "http_error", "message": raw or str(exc), "status": exc.code}
        payload.setdefault("status", exc.code)
        return payload


TOOLS: list[dict[str, Any]] = [
    {
        "name": "registry_capabilities",
        "description": "GET /v1/agent/capabilities — auth modes, limits, example flows",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "registry_list_packages",
        "description": "GET /v1/packages",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "limit": {"type": "integer"},
                "include_yanked": {"type": "boolean"},
            },
        },
    },
    {
        "name": "registry_validate_publish",
        "description": "POST /v1/publish/validate — dry-run publish gates",
        "inputSchema": {
            "type": "object",
            "required": ["name", "version", "tree_digest", "proof_digest", "coverage_pct"],
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "tree_digest": {"type": "string"},
                "proof_digest": {"type": "string"},
                "coverage_pct": {"type": "number"},
                "artifact_digest": {"type": "string"},
            },
        },
    },
    {
        "name": "registry_auth_signup",
        "description": "POST /v1/auth/signup — email signup (optional signup_token, publisher_name)",
        "inputSchema": {
            "type": "object",
            "required": ["email", "password"],
            "properties": {
                "email": {"type": "string"},
                "password": {"type": "string"},
                "publisher_name": {"type": "string"},
                "signup_token": {"type": "string"},
            },
        },
    },
    {
        "name": "registry_auth_login",
        "description": "POST /v1/auth/login — session JWT for token admin",
        "inputSchema": {
            "type": "object",
            "required": ["email", "password"],
            "properties": {
                "email": {"type": "string"},
                "password": {"type": "string"},
            },
        },
    },
    {
        "name": "registry_auth_whoami",
        "description": "GET /v1/auth/whoami — current session user (session bearer or LIP_REGISTRY_TOKEN if session)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_token": {"type": "string", "description": "Optional session JWT from login"},
            },
        },
    },
    {
        "name": "registry_auth_create_token",
        "description": "POST /v1/auth/tokens — mint lip_ API token (requires session bearer)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_token": {"type": "string"},
                "name": {"type": "string"},
                "scope": {"type": "string", "enum": ["publish", "yank", "publish+yank", "audit", "publish+audit"]},
                "expires_in": {"type": "integer"},
            },
        },
    },
    {
        "name": "registry_auth_device_start",
        "description": "POST /v1/auth/device/start — begin device login; user approves at verification_uri",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "registry_auth_device_poll",
        "description": "POST /v1/auth/device/poll — poll device_code until approved",
        "inputSchema": {
            "type": "object",
            "required": ["device_code"],
            "properties": {"device_code": {"type": "string"}},
        },
    },
    {
        "name": "registry_mint_signup_token",
        "description": "POST /v1/auth/signup-tokens — gated invite (session bearer)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_token": {"type": "string"},
                "email_hint": {"type": "string"},
                "max_uses": {"type": "integer"},
                "ttl_hours": {"type": "integer"},
            },
        },
    },
]


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "registry_capabilities":
        return _request("GET", "/agent/capabilities")
    if name == "registry_list_packages":
        qs = []
        for key in ("name", "limit", "include_yanked"):
            if key in arguments and arguments[key] is not None:
                qs.append(f"{key}={arguments[key]}")
        path = "/packages" + (f"?{'&'.join(qs)}" if qs else "")
        return _request("GET", path)
    if name == "registry_validate_publish":
        return _request("POST", "/publish/validate", arguments)
    if name == "registry_auth_signup":
        return _request("POST", "/auth/signup", arguments)
    if name == "registry_auth_login":
        return _request("POST", "/auth/login", arguments)
    if name == "registry_auth_whoami":
        tok = arguments.get("session_token") or _token()
        return _request("GET", "/auth/whoami", token=tok)
    if name == "registry_auth_create_token":
        tok = arguments.pop("session_token", None) or _token()
        body = {k: v for k, v in arguments.items() if v is not None}
        return _request("POST", "/auth/tokens", body, token=tok)
    if name == "registry_auth_device_start":
        return _request("POST", "/auth/device/start", {})
    if name == "registry_auth_device_poll":
        return _request("POST", "/auth/device/poll", {"device_code": arguments["device_code"]})
    if name == "registry_mint_signup_token":
        tok = arguments.pop("session_token", None) or _token()
        body = {k: v for k, v in arguments.items() if v is not None}
        return _request("POST", "/auth/signup-tokens", body, token=tok)
    return {"error": "not_found", "message": f"unknown tool {name}"}


def _handle(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    req_id = msg.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "lip-registry", "version": "0.2.0"},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        tool_name = str(params.get("name", ""))
        args = dict(params.get("arguments") or {})
        payload = _call_tool(tool_name, args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]},
        }
    if req_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }
    return None


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        out = _handle(msg)
        if out is not None:
            sys.stdout.write(json.dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
