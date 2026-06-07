"""Stdio MCP server mapping Phase 1 registry tools to REST /v1/*."""

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


def _request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{_base_url()}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "http_error", "message": raw or str(exc), "status": exc.code}


TOOLS: list[dict[str, Any]] = [
    {
        "name": "registry_capabilities",
        "description": "GET /v1/agent/capabilities — auth modes, limits, example flows",
        "inputSchema": {"type": "object", "properties": {}},
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
]


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "registry_capabilities":
        return _request("GET", "/agent/capabilities")
    if name == "registry_validate_publish":
        return _request("POST", "/publish/validate", arguments)
    if name == "registry_list_packages":
        qs = []
        for key in ("name", "limit", "include_yanked"):
            if key in arguments and arguments[key] is not None:
                qs.append(f"{key}={arguments[key]}")
        path = "/packages" + (f"?{'&'.join(qs)}" if qs else "")
        return _request("GET", path)
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
                "serverInfo": {"name": "lip-registry", "version": "0.1.0"},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = str(params.get("name", ""))
        args = params.get("arguments") or {}
        payload = _call_tool(name, args)
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
