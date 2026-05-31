"""MQ REST handlers — /v1/mq/* → loopback broker (LI_MQ_UPSTREAM)."""

from __future__ import annotations

import json
import os
import threading
from http.client import HTTPConnection
from typing import Any
from urllib.parse import urlparse

UPSTREAM = os.environ.get("LI_MQ_UPSTREAM", "http://127.0.0.1:9478").rstrip("/")
BENCH_NO_AUTH = os.environ.get("LI_MQ_BENCH_NO_AUTH", "1") == "1"
_p = urlparse(UPSTREAM)
_UP_HOST = _p.hostname or "127.0.0.1"
_UP_PORT = _p.port or 9478
_local = threading.local()


def _upstream() -> HTTPConnection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = HTTPConnection(_UP_HOST, _UP_PORT)
        _local.conn = conn
    try:
        conn.connect()
    except OSError:
        conn = HTTPConnection(_UP_HOST, _UP_PORT)
        _local.conn = conn
        conn.connect()
    return conn


def _map_path(path: str) -> str | None:
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 3 and parts[0] == "v1" and parts[1] == "mq":
        rest = parts[2:]
        if rest == ["health"]:
            return "/health"
        if len(rest) >= 3 and rest[0] == "topics":
            topic, tail = rest[1], rest[2:]
            if tail == ["publish"]:
                return f"/v1/topics/{topic}/publish"
            if tail == ["publish", "batch"]:
                return f"/v1/topics/{topic}/publish/batch"
            if tail == ["consume"]:
                return f"/v1/topics/{topic}/consume"
            if tail == ["consume", "batch"]:
                return f"/v1/topics/{topic}/consume/batch"
            if tail == ["ack"]:
                return f"/v1/topics/{topic}/ack"
            if tail == ["peek"]:
                return f"/v1/topics/{topic}/peek"
        if rest == ["admin", "topics"]:
            return "/v1/admin/topics"
        if rest == ["admin", "stats"]:
            return "/v1/admin/stats"
    return None


def _json_response(status: int, body: dict[str, Any]) -> tuple[int, dict[str, str], bytes]:
    payload = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Content-Length": str(len(payload))}
    return status, headers, payload


def handle_request(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes]:
    headers = headers or {}
    if not BENCH_NO_AUTH and not headers.get("Authorization") and not headers.get("authorization"):
        return _json_response(401, {"error": "unauthorized"})

    broker_path = _map_path(path)
    if broker_path is None:
        return _json_response(404, {"error": "not_found"})

    conn = _upstream()
    req_headers: dict[str, str] = {"Connection": "keep-alive"}
    ctype = headers.get("Content-Type") or headers.get("content-type")
    if ctype:
        req_headers["Content-Type"] = ctype
    conn.request(method, broker_path, body=body, headers=req_headers)
    resp = conn.getresponse()
    data = resp.read()
    out_headers: dict[str, str] = {
        "Content-Type": resp.getheader("Content-Type", "application/json"),
        "Content-Length": str(len(data)),
    }
    return resp.status, out_headers, data
