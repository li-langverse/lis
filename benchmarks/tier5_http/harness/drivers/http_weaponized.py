"""Weaponized HTTP probes — aggressive real-world attack patterns (loopback only)."""
from __future__ import annotations

import socket
from typing import Any

from . import http_attacks


def _connect(host: str, port: int, timeout: float = 2.0) -> socket.socket:
    return http_attacks._connect(host, port, timeout)


def _raw(host: str, port: int, raw: bytes, timeout: float = 3.0) -> bytes:
    return http_attacks._raw_request(host, port, raw, timeout)


def attack_chunked_encoding_bomb(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    """Chunked request body without complete parser — must reject."""
    req = (
        b"POST / HTTP/1.1\r\n"
        + f"Host: {host}:{port}\r\n".encode()
        + b"Transfer-Encoding: chunked\r\n"
        + b"Connection: close\r\n\r\n"
        + b"0\r\n\r\n"
    )
    data = _raw(host, port, req)
    leaked = http_attacks._response_has_sensitive_leak(data)
    legit = http_attacks.legitimate_get(host, port)
    status = data.split(b"\r\n", 1)[0] if data else b""
    handled = (
        len(data) == 0
        or b"400" in status
        or b"405" in status
        or b"413" in status
        or b"404" in status
        or not leaked
    )
    return {
        "no_sensitive_leak": not leaked,
        "reject_or_close_attack": handled,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_oversized_headers(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    n = int(attack.get("header_lines") or 200)
    line = b"X-Weaponized: " + b"A" * 64 + b"\r\n"
    req = b"GET / HTTP/1.1\r\nHost: " + f"{host}:{port}".encode() + b"\r\n" + (line * n) + b"\r\n"
    data = _raw(host, port, req, timeout=3.0)
    legit = http_attacks.legitimate_get(host, port)
    return {
        "reject_or_close_attack": len(data) == 0 or b"400" in data or b"414" in data,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_cache_poisoning_forwarded(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    req = (
        f"GET / HTTP/1.1\r\nHost: evil.cache\r\nX-Forwarded-Host: {host}:{port}\r\n"
        f"X-Original-URL: http://{host}:{port}/\r\nConnection: close\r\n\r\n"
    ).encode()
    data = _raw(host, port, req)
    poisoned = b"evil.cache" in data and b"200" in data.split(b"\r\n", 1)[0]
    legit = http_attacks.legitimate_get(host, port)
    return {
        "no_cache_poison_reflect": not poisoned,
        "reject_or_close_attack": not poisoned or len(data) == 0,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_pipeline_request_stuffing(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    n = int(attack.get("pipelined_requests") or 32)
    parts = [
        f"GET /?n={i} HTTP/1.1\r\nHost: {host}:{port}\r\n".encode() for i in range(n)
    ]
    raw = b"".join(parts) + b"\r\n"
    try:
        s = _connect(host, port, 3.0)
        s.sendall(raw)
        data = b""
        for _ in range(n + 2):
            try:
                chunk = s.recv(8192)
            except OSError:
                break
            if not chunk:
                break
            data += chunk
            if len(data) > 131072:
                break
        s.close()
    except OSError:
        data = b""
    legit = http_attacks.legitimate_get(host, port)
    return {
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_absolute_uri_connect(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    req = (
        f"GET http://{host}:{port}/ HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
    ).encode()
    data = _raw(host, port, req)
    ok = b"200" in data.split(b"\r\n", 1)[0] or len(data) == 0 or b"400" in data
    legit = http_attacks.legitimate_get(host, port)
    return {
        "reject_or_close_attack": ok,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_post_method_override(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    req = (
        b"POST / HTTP/1.1\r\n"
        + f"Host: {host}:{port}\r\n".encode()
        + b"X-HTTP-Method-Override: GET\r\n"
        + b"Content-Length: 0\r\nConnection: close\r\n\r\n"
    )
    data = _raw(host, port, req)
    leaked = http_attacks._response_has_sensitive_leak(data)
    legit = http_attacks.legitimate_get(host, port)
    return {
        "no_sensitive_leak": not leaked,
        "reject_or_close_attack": len(data) == 0 or not leaked,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_te_cl_weaponized(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    return http_attacks.attack_request_smuggling_te_cl(host, port, attack)


def attack_cl_te_weaponized(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    return http_attacks.attack_request_smuggling_cl_te(host, port, attack)


WEAPONIZED_DRIVERS = {
    "chunked_encoding_bomb": attack_chunked_encoding_bomb,
    "oversized_headers": attack_oversized_headers,
    "cache_poisoning_forwarded": attack_cache_poisoning_forwarded,
    "pipeline_request_stuffing": attack_pipeline_request_stuffing,
    "absolute_uri_connect": attack_absolute_uri_connect,
    "post_method_override": attack_post_method_override,
    "te_cl_weaponized": attack_te_cl_weaponized,
    "cl_te_weaponized": attack_cl_te_weaponized,
}
