#!/usr/bin/env python3
"""HTTP tier-5 harness — TOML verify + optional nginx/wrk RPS → results/latest.csv.

When ``nginx`` and ``wrk`` are on PATH (typical Linux CI after apt install), runs a
short load test against stock nginx serving ``fixtures/static`` and records
``lang=nginx`` ``metric=rps`` rows. ``lang=li`` rows are emitted when ``LI_HTTPD_BIN`` (default: ``lic/build/li-httpd``)
is built from ``packages/li-net-httpd`` in the **lic** repo.

See ``benchmarks/tier5_http/README.md`` for local usage.
"""
from __future__ import annotations

import argparse
import csv
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # py3.10
    import tomli as tomllib  # type: ignore

CSV_FIELDS = (
    "benchmark",
    "lang",
    "variant",
    "threads",
    "metric",
    "value",
    "unit",
    "git_sha",
    "cpu_model",
    "flags",
)


def tier5_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_suite(profile: str) -> tuple[list[str], bool]:
    """Return (scenario_names, timing_enabled)."""
    suite_path = tier5_root() / "suite.toml"
    data = load_toml(suite_path)
    prof = data.get("profiles", {}).get(profile)
    if not prof:
        prof = data.get("default", {})
    include = list(prof.get("include") or data.get("default", {}).get("include") or ["static_small"])
    timing = bool(prof.get("timing", data.get("default", {}).get("timing", False)))
    return include, timing


def merge_scenario(name: str) -> dict[str, Any]:
    root = tier5_root()
    defaults = load_toml(root / "defaults.toml")
    scenario_path = root / "scenarios" / name / "bench.toml"
    scenario = load_toml(scenario_path)
    out: dict[str, Any] = {"name": name}
    out["_fixtures"] = defaults.get("fixtures", {})
    out["_tools"] = defaults.get("tools", {})
    out["_load_defaults"] = defaults.get("load", {})
    out.update(scenario)
    return out


def lis_repo_root() -> Path:
    """tier5_http → benchmarks → lis repo root."""
    return tier5_root().parents[1]


def git_sha_short() -> str:
    try:
        p = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=lis_repo_root(),
            capture_output=True,
            text=True,
            check=False,
        )
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip()
    except OSError:
        pass
    return "unknown"


def cpu_model() -> str:
    return platform.processor() or platform.machine() or "unknown"


def pick_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    _, port = s.getsockname()
    s.close()
    return int(port)


def nginx_proxy_prefix_conf(front_port: int, backend_port: int, prefix: Path) -> str:
    return nginx_lb_proxy_prefix_conf(front_port, [backend_port], prefix)


def nginx_lb_proxy_prefix_conf(front_port: int, backend_ports: list[int], prefix: Path) -> str:
    px = str(prefix.resolve()).replace("\\", "/")
    upstream_lines = "\n".join(f"    server 127.0.0.1:{p};" for p in backend_ports)
    return f"""worker_processes 1;
error_log {px}/error.log warn;
pid {px}/nginx.pid;
daemon on;
events {{ worker_connections 4096; }}
http {{
  access_log off;
  client_body_temp_path {px}/client_temp;
  proxy_temp_path {px}/proxy_temp;
  fastcgi_temp_path {px}/fastcgi_temp;
  uwsgi_temp_path {px}/uwsgi_temp;
  scgi_temp_path {px}/scgi_temp;
  upstream loopback_backend {{
{upstream_lines}
    keepalive 32;
  }}
  server {{
    listen 127.0.0.1:{front_port};
    server_name _;
    location / {{
      proxy_pass http://loopback_backend;
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header Connection "";
    }}
  }}
}}
"""


def nginx_prefix_conf(document_root: Path, port: int, prefix: Path) -> str:
    dr = str(document_root.resolve()).replace("\\", "/")
    px = str(prefix.resolve()).replace("\\", "/")
    return f"""worker_processes 1;
error_log {px}/error.log warn;
pid {px}/nginx.pid;
daemon on;
events {{ worker_connections 4096; }}
http {{
  access_log off;
  sendfile on;
  client_body_temp_path {px}/client_temp;
  proxy_temp_path {px}/proxy_temp;
  fastcgi_temp_path {px}/fastcgi_temp;
  uwsgi_temp_path {px}/uwsgi_temp;
  scgi_temp_path {px}/scgi_temp;
  server {{
    listen 127.0.0.1:{port};
    server_name _;
    root {dr};
    location / {{
      try_files $uri /index.html =404;
    }}
  }}
}}
"""


def parse_wrk_rps(text: str) -> float | None:
    # "Requests/sec:   12345.67" or with thousands separators rarely
    m = re.search(r"Requests/sec:\s*([\d,.]+)", text, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def write_wrk_pipeline_lua(path: Path, port: int, depth: int) -> None:
    path.write_text(
        f"""-- Auto-generated for HTTP/1.1 pipelined requests (depth={depth})
local depth = {int(depth)}
request = function()
  local host = "127.0.0.1:{port}"
  local chunk = "GET / HTTP/1.1\\r\\nHost: " .. host .. "\\r\\nConnection: keep-alive\\r\\n\\r\\n"
  local r = ""
  for _ = 1, depth do
    r = r .. chunk
  end
  return r
end
""",
        encoding="utf-8",
    )


def run_wrk(
    url: str,
    threads: int,
    connections: int,
    duration_sec: int,
    lua_script: Path | None,
) -> tuple[float | None, str]:
    cmd = [
        "wrk",
        "-t",
        str(threads),
        "-c",
        str(connections),
        "-d",
        f"{duration_sec}s",
        "--latency",
    ]
    if lua_script is not None:
        cmd.extend(["-s", str(lua_script)])
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    blob = (proc.stdout or "") + (proc.stderr or "")
    return parse_wrk_rps(blob), blob


def launch_nginx(prefix: Path, conf_text: str) -> bool:
    prefix.mkdir(parents=True, exist_ok=True)
    for sub in ("logs", "client_temp", "proxy_temp", "fastcgi_temp", "uwsgi_temp", "scgi_temp"):
        (prefix / sub).mkdir(parents=True, exist_ok=True)
    conf_path = prefix / "nginx.conf"
    conf_path.write_text(conf_text, encoding="utf-8")
    nginx = shutil.which("nginx")
    if not nginx:
        return False
    pfx = str(prefix.resolve()) + os.sep
    proc = subprocess.run(
        [nginx, "-p", pfx, "-c", str(conf_path.resolve())],
        cwd=prefix,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or "") + (proc.stdout or "")
        sys.stderr.write(f"nginx start failed rc={proc.returncode}: {err}\n")
        return False
    pid_path = prefix / "nginx.pid"
    for _ in range(200):
        if pid_path.is_file():
            time.sleep(0.02)
            return True
        time.sleep(0.02)
    return False


def resolve_li_httpd_bin() -> Path | None:
    env = os.environ.get("LI_HTTPD_BIN")
    if env:
        p = Path(env)
        if p.is_file():
            return p
    lic_root = os.environ.get("LIC_ROOT")
    candidates: list[Path] = []
    if lic_root:
        candidates.append(Path(lic_root) / "build" / "li-httpd")
    # workspace layout: benchmarks/vendor/lis-tier5 or lis sibling of lic
    candidates.extend(
        [
            lis_repo_root().parent.parent / "lic" / "build" / "li-httpd",
            Path("/workspace/lic/build/li-httpd"),
        ]
    )
    for c in candidates:
        if c.is_file():
            return c
    return None


def wait_for_port(port: int, timeout_sec: float = 3.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.1)
            s.close()
            return True
        except OSError:
            time.sleep(0.02)
    return False


def stop_nginx(prefix: Path) -> None:
    pid_path = prefix / "nginx.pid"
    if pid_path.is_file():
        try:
            pid = int(pid_path.read_text().strip())
            os.kill(pid, signal.SIGQUIT)
        except (ValueError, ProcessLookupError, OSError):
            pass
    # allow worker shutdown
    time.sleep(0.1)


def _append_rps_row(
    rows: list[dict[str, str]],
    name: str,
    lang: str,
    rps: float | None,
    *,
    variant: str,
    connections: int,
    flags: str,
    sha: str,
    cpu: str,
) -> None:
    if rps is not None and rps > 0:
        rows.append(
            {
                "benchmark": name,
                "lang": lang,
                "variant": variant,
                "threads": str(connections),
                "metric": "rps",
                "value": f"{rps:.4f}",
                "unit": "req/s",
                "git_sha": sha,
                "cpu_model": cpu,
                "flags": flags,
            }
        )
    else:
        rows.append(_harness_row(name, f"wrk_parse_fail_{lang}"))


def ensure_static_large_fixture(doc_root: Path, name: str) -> None:
    """Create 1 MiB file.bin for static_large when missing."""
    if name != "static_large":
        return
    target = doc_root / "file.bin"
    if target.is_file() and target.stat().st_size >= 1024 * 1024:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\0" * (1024 * 1024))


def bench_wrk_for_lang(
    name: str,
    cfg: dict[str, Any],
    *,
    quick: bool,
    lang: str,
    port: int,
    doc_root: Path,
    start_server,
    stop_server,
) -> tuple[list[dict[str, str]], str]:
    rows: list[dict[str, str]] = []
    log_bits: list[str] = []

    load = cfg.get("load") or {}
    threads = int(load.get("threads") or cfg.get("_load_defaults", {}).get("threads") or 2)
    connections = int(load.get("connections") or 8)
    duration = int(load.get("duration_sec") or 10)
    if quick:
        duration = min(duration, int(os.environ.get("BENCH_HTTP_QUICK_SEC", "3")))
    pipeline = int(load.get("pipeline") or 1)

    lua_path: Path | None = None
    tmp_lua: tempfile.TemporaryDirectory[str] | None = None
    if pipeline > 1:
        tmp_lua = tempfile.TemporaryDirectory(prefix="lis-wrk-")
        lua_path = Path(tmp_lua.name) / "pipeline.lua"
        write_wrk_pipeline_lua(lua_path, port, pipeline)

    ctx = start_server(port, doc_root)
    try:
        if not wait_for_port(port):
            rows.append(_harness_row(name, f"{lang}_no_listen"))
            return rows, f"{lang}: port not ready"

        verify_cfg = cfg.get("verify") or {}
        for req in verify_cfg.get("requests") or []:
            path = req.get("path") or "/"
            expect = int(req.get("expect_status") or 200)
            if not verify_http_get(f"http://127.0.0.1:{port}{path}", expect):
                rows.append(_harness_row(name, f"verify_fail_{lang}:{path}"))
                return rows, f"{lang}: verify failed"

        url_path = str(load.get("url_path") or "/")
        if not url_path.startswith("/"):
            url_path = "/" + url_path
        url = f"http://127.0.0.1:{port}{url_path}"
        rps, blob = run_wrk(url, threads, connections, duration, lua_path)
        log_bits.append(f"--- {lang} ---\n{blob[-1500:]}")

        variant = "ci" if quick else "release"
        flags = f"wrk pipeline={pipeline}" if pipeline > 1 else "wrk"
        if lang in ("node", "bun"):
            from http_oracles import runtime_version

            ver = runtime_version(lang)
            if ver:
                flags = f"{flags} {ver}"
        _append_rps_row(
            rows,
            name,
            lang,
            rps,
            variant=variant,
            connections=connections,
            flags=flags,
            sha=git_sha_short(),
            cpu=cpu_model(),
        )
    finally:
        stop_server(ctx)
        if tmp_lua is not None:
            tmp_lua.cleanup()

    return rows, "\n".join(log_bits)


def proxy_scenario_enabled(cfg: dict[str, Any]) -> bool:
    return bool((cfg.get("proxy") or {}).get("enabled"))


def rate_limit_scenario_enabled(cfg: dict[str, Any]) -> bool:
    return bool((cfg.get("rate_limit") or {}).get("enabled"))


def tls_scenario_enabled(cfg: dict[str, Any]) -> bool:
    return bool((cfg.get("tls") or {}).get("enabled"))


def write_li_runtime_conf(
    path: Path,
    *,
    port: int,
    doc_root: Path,
    rate_limit_rps: int,
    rate_limit_burst: int,
) -> None:
    lines = [
        f"listen_port={port}",
        f"document_root={doc_root.resolve()}",
        f"rate_limit_rps={rate_limit_rps}",
        f"rate_limit_burst={rate_limit_burst}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_rate_limit_429(port: int, *, burst_requests: int = 30) -> bool:
    """First request 200, then rapid burst must yield at least one 429."""
    if not verify_http_get(f"http://127.0.0.1:{port}/", 200):
        return False
    import urllib.error
    import urllib.request

    for _ in range(burst_requests):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as resp:
                if int(resp.status) == 429:
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return True
        except (urllib.error.URLError, OSError, ValueError):
            pass
    return False


def openssl_https_rps(port: int, duration_sec: int) -> float | None:
    """TLS throughput via openssl s_time (self-signed friendly)."""
    openssl = shutil.which("openssl")
    if not openssl:
        return None
    proc = subprocess.run(
        [openssl, "s_time", "-connect", f"127.0.0.1:{port}", "-new", "-time", str(duration_sec)],
        capture_output=True,
        text=True,
        check=False,
    )
    blob = (proc.stdout or "") + (proc.stderr or "")
    for line in blob.splitlines():
        if "connections" in line.lower() and "/" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == "connections" and i > 0:
                    try:
                        return float(parts[i - 1].replace(",", "")) / max(duration_sec, 1)
                    except ValueError:
                        pass
    m = re.search(r"(\d+(?:\.\d+)?)\s+connections\s+in\s+[\d.]+\s+seconds", blob, re.I)
    if m:
        return float(m.group(1)) / max(duration_sec, 1)
    return None


def verify_https_get(port: int, path: str = "/") -> bool:
    import ssl
    import urllib.error
    import urllib.request

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = f"https://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=5, context=ctx) as resp:
            return int(resp.status) == 200
    except (urllib.error.URLError, OSError, ValueError, ssl.SSLError):
        return False


def bench_tls_scenario(
    name: str,
    cfg: dict[str, Any],
    *,
    quick: bool,
) -> tuple[list[dict[str, str]], str]:
    """HTTPS tier5 — multi-oracle TLS handshake/RPS (openssl s_time); li verify_skip until M1.5."""
    rows: list[dict[str, str]] = []
    log_bits: list[str] = []

    fixtures = cfg.get("_fixtures", {})
    rel_static = fixtures.get("static_root", "fixtures/static")
    doc_root = tier5_root() / rel_static
    if not (doc_root / "index.html").is_file():
        rows.append(_harness_row(name, f"missing_fixture:{doc_root}"))
        return rows, "missing static fixture"

    load = cfg.get("load") or {}
    duration = int(load.get("duration_sec") or 10)
    if quick:
        duration = min(duration, int(os.environ.get("BENCH_HTTP_QUICK_SEC", "3")))

    from http_oracles import (
        DEFAULT_BENCH_ORACLES,
        TLS_BENCH_HOOKS,
        ensure_tls_cert,
        oracle_available,
        parse_oracle_langs,
    )

    tmp_tls = tempfile.TemporaryDirectory(prefix="lis-tls-")
    cert_pair = ensure_tls_cert(Path(tmp_tls.name))
    if not cert_pair:
        rows.append(_harness_row(name, "no_tls_cert"))
        return rows, "openssl cert generation failed"
    cert, key = cert_pair

    for lang in parse_oracle_langs("BENCH_HTTP_ORACLES", DEFAULT_BENCH_ORACLES):
        if lang == "node" or lang == "bun":
            rows.append(_harness_row(name, f"no_{lang}_https"))
            continue
        if lang == "li":
            rows.append(
                {
                    "benchmark": name,
                    "lang": "li",
                    "variant": "ci",
                    "threads": "1",
                    "metric": "verify_skip",
                    "value": "1",
                    "unit": "bool",
                    "git_sha": git_sha_short(),
                    "cpu_model": cpu_model(),
                    "flags": "tls_m15_pending",
                }
            )
            continue
        if lang not in TLS_BENCH_HOOKS or not oracle_available(lang):
            rows.append(_harness_row(name, f"no_{lang}"))
            continue
        port = pick_port()
        start_fn, stop_fn = TLS_BENCH_HOOKS[lang]
        ctx = start_fn(port, doc_root, cert, key)
        try:
            if ctx is None:
                rows.append(_harness_row(name, f"{lang}_tls_no_start"))
                continue
            if not wait_for_port(port, timeout_sec=8.0):
                rows.append(_harness_row(name, f"{lang}_tls_no_listen"))
                continue
            if not verify_https_get(port):
                rows.append(_harness_row(name, f"verify_fail_{lang}:https"))
                continue
            rps = openssl_https_rps(port, duration)
            log_bits.append(f"--- {lang} tls ---\n{rps}")
            _append_rps_row(
                rows,
                name,
                lang,
                rps,
                variant="ci" if quick else "release",
                connections=8,
                flags="openssl s_time https",
                sha=git_sha_short(),
                cpu=cpu_model(),
            )
        finally:
            stop_fn(ctx)
    tmp_tls.cleanup()
    return rows, "\n".join(log_bits)


def bench_rate_limit_scenario(
    name: str,
    cfg: dict[str, Any],
    *,
    quick: bool,
) -> tuple[list[dict[str, str]], str]:
    """li-httpd only: global token bucket must return HTTP 429 under burst."""
    rows: list[dict[str, str]] = []
    _ = quick

    fixtures = cfg.get("_fixtures", {})
    rel_static = fixtures.get("static_root", "fixtures/static")
    doc_root = tier5_root() / rel_static
    if not (doc_root / "index.html").is_file():
        rows.append(_harness_row(name, f"missing_fixture:{doc_root}"))
        return rows, "missing static fixture"

    rl = cfg.get("rate_limit") or {}
    rps = int(rl.get("rps") or 2)
    burst = int(rl.get("burst") or 1)

    li_bin = resolve_li_httpd_bin()
    if not li_bin:
        rows.append(_harness_row(name, "no_li_httpd_bin"))
        return rows, "no li-httpd"

    port = pick_port()
    tmp = tempfile.TemporaryDirectory(prefix="lis-rate-limit-")
    conf_path = Path(tmp.name) / "runtime.conf"
    write_li_runtime_conf(
        conf_path,
        port=port,
        doc_root=doc_root,
        rate_limit_rps=rps,
        rate_limit_burst=burst,
    )
    proc = subprocess.Popen(
        [str(li_bin), str(conf_path.resolve())],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for_port(port):
            rows.append(_harness_row(name, "li_rate_limit_no_listen"))
            return rows, "li: port not ready"
        if verify_rate_limit_429(port):
            rows.append(
                {
                    "benchmark": name,
                    "lang": "li",
                    "variant": "ci",
                    "threads": "1",
                    "metric": "verify_pass",
                    "value": "1",
                    "unit": "bool",
                    "git_sha": git_sha_short(),
                    "cpu_model": cpu_model(),
                    "flags": f"rate_limit rps={rps} burst={burst}",
                }
            )
        else:
            rows.append(_harness_row(name, "verify_fail_li:rate_limit_429"))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        tmp.cleanup()

    return rows, "rate_limit verify"


def bench_proxy_loopback_scenario(
    name: str,
    cfg: dict[str, Any],
    *,
    quick: bool,
) -> tuple[list[dict[str, str]], str]:
    """Two-tier loopback: backend static server + front reverse proxy."""
    rows: list[dict[str, str]] = []
    log_bits: list[str] = []

    fixtures = cfg.get("_fixtures", {})
    rel_static = fixtures.get("static_root", "fixtures/static")
    doc_root = tier5_root() / rel_static
    if not (doc_root / "index.html").is_file():
        rows.append(_harness_row(name, f"missing_fixture:{doc_root}"))
        return rows, "missing static fixture"

    if not shutil.which("wrk"):
        rows.append(_harness_row(name, "no_wrk"))
        return rows, "wrk not found"

    load = cfg.get("load") or {}
    threads = int(load.get("threads") or cfg.get("_load_defaults", {}).get("threads") or 2)
    connections = int(load.get("connections") or 8)
    duration = int(load.get("duration_sec") or 10)
    if quick:
        duration = min(duration, int(os.environ.get("BENCH_HTTP_QUICK_SEC", "3")))
    url_path = str(load.get("url_path") or "/")
    if not url_path.startswith("/"):
        url_path = "/" + url_path

    proxy_cfg = cfg.get("proxy") or {}
    backend_count = int(proxy_cfg.get("backend_count") or 1)
    if backend_count < 1:
        backend_count = 1
    if backend_count > 8:
        backend_count = 8
    backend_ports = [pick_port() for _ in range(backend_count)]
    front_port = pick_port()
    csv_ports = ",".join(str(p) for p in backend_ports)
    lb_mode = str(proxy_cfg.get("lb_mode") or "round_robin")
    kill_idx = proxy_cfg.get("kill_backend_index")
    wrk_flags = "wrk proxy_lb"
    if backend_count == 1:
        wrk_flags = "wrk proxy_loopback"
    if lb_mode == "least_conn":
        wrk_flags = "wrk proxy_least_conn"

    def run_wrk_on_front(lang: str) -> None:
        url = f"http://127.0.0.1:{front_port}{url_path}"
        rps, blob = run_wrk(url, threads, connections, duration, None)
        log_bits.append(f"--- {lang} proxy ---\n{blob[-1500:]}")
        variant = "ci" if quick else "release"
        _append_rps_row(
            rows,
            name,
            lang,
            rps,
            variant=variant,
            connections=connections,
            flags=wrk_flags,
            sha=git_sha_short(),
            cpu=cpu_model(),
        )

    from http_oracles import (
        PROXY_BENCH_HOOKS,
        parse_proxy_oracle_langs,
        start_nginx_static_backends,
        stop_nginx_static_backends,
    )

    backends = start_nginx_static_backends(backend_ports, doc_root)
    if len(backends) != len(backend_ports):
        rows.append(_harness_row(name, "no_nginx_backend"))
        return rows, "backend nginx static failed"

    os.environ["BENCH_HTTP_LB_MODE"] = lb_mode
    try:
        for lang in parse_proxy_oracle_langs():
            if lang not in PROXY_BENCH_HOOKS:
                rows.append(_harness_row(name, f"unknown_proxy_oracle_{lang}"))
                continue
            if lang == "li" and not resolve_li_httpd_bin():
                rows.append(_harness_row(name, "no_li_httpd_bin"))
                continue
            if lang == "apache" and not (
                shutil.which("apache2") or shutil.which("apachectl") or shutil.which("httpd")
            ):
                rows.append(_harness_row(name, "no_apache"))
                continue
            if lang == "lighttpd" and not shutil.which("lighttpd"):
                rows.append(_harness_row(name, "no_lighttpd"))
                continue
            if lang == "caddy" and not shutil.which("caddy"):
                rows.append(_harness_row(name, "no_caddy"))
                continue
            if lang == "nginx" and not shutil.which("nginx"):
                rows.append(_harness_row(name, "no_nginx"))
                continue

            start_fn, stop_fn = PROXY_BENCH_HOOKS[lang]
            ctx = start_fn(front_port, doc_root, backend_ports)
            try:
                if ctx is None:
                    rows.append(_harness_row(name, f"{lang}_proxy_start_fail"))
                    continue
                if not wait_for_port(front_port):
                    rows.append(_harness_row(name, f"{lang}_proxy_no_listen"))
                    continue
                verify_cfg = cfg.get("verify") or {}
                ok = True
                for req in verify_cfg.get("requests") or []:
                    path = req.get("path") or "/"
                    expect = int(req.get("expect_status") or 200)
                    if not verify_http_get(f"http://127.0.0.1:{front_port}{path}", expect):
                        rows.append(_harness_row(name, f"verify_fail_{lang}:{path}"))
                        ok = False
                        break
                if ok and kill_idx is not None and lang == "li":
                    ki = int(kill_idx)
                    if 0 <= ki < len(backends):
                        from http_oracles import stop_nginx_bench

                        stop_nginx_bench(backends[ki])
                        time.sleep(0.2)
                        if not verify_http_get(f"http://127.0.0.1:{front_port}/", 200):
                            rows.append(_harness_row(name, "verify_fail_li:after_kill"))
                            ok = False
                if ok:
                    run_wrk_on_front(lang)
            finally:
                stop_fn(ctx)
    finally:
        stop_nginx_static_backends([b for b in backends if b])

    return rows, "\n".join(log_bits)


def bench_nginx_scenario(
    name: str,
    cfg: dict[str, Any],
    *,
    quick: bool,
) -> tuple[list[dict[str, str]], str]:
    """Return CSV rows and human log tail (multi-oracle bench + optional li-httpd)."""
    if rate_limit_scenario_enabled(cfg):
        return bench_rate_limit_scenario(name, cfg, quick=quick)
    if tls_scenario_enabled(cfg):
        return bench_tls_scenario(name, cfg, quick=quick)
    if proxy_scenario_enabled(cfg):
        return bench_proxy_loopback_scenario(name, cfg, quick=quick)

    from http_oracles import (
        BENCH_ORACLE_HOOKS,
        DEFAULT_BENCH_ORACLES,
        oracle_available,
        parse_oracle_langs,
        pick_port as oracle_pick_port,
    )

    rows: list[dict[str, str]] = []
    log_bits: list[str] = []

    fixtures = cfg.get("_fixtures", {})
    rel_static = fixtures.get("static_root", "fixtures/static")
    doc_root = tier5_root() / rel_static
    if not (doc_root / "index.html").is_file():
        rows.append(_harness_row(name, f"missing_fixture:{doc_root}"))
        return rows, "missing static fixture"
    ensure_static_large_fixture(doc_root, name)

    if not shutil.which("wrk"):
        rows.append(_harness_row(name, "no_wrk"))
        return rows, "wrk not found"

    for lang in parse_oracle_langs("BENCH_HTTP_ORACLES", DEFAULT_BENCH_ORACLES):
        if lang not in BENCH_ORACLE_HOOKS:
            rows.append(_harness_row(name, f"unknown_oracle_{lang}"))
            continue
        if not oracle_available(lang):
            rows.append(_harness_row(name, f"no_{lang}"))
            continue
        start_fn, stop_fn = BENCH_ORACLE_HOOKS[lang]
        port = oracle_pick_port()
        lang_rows, lang_log = bench_wrk_for_lang(
            name,
            cfg,
            quick=quick,
            lang=lang,
            port=port,
            doc_root=doc_root,
            start_server=start_fn,
            stop_server=stop_fn,
        )
        rows.extend(lang_rows)
        if lang_log:
            log_bits.append(lang_log)

    return rows, "\n".join(log_bits)


def _harness_row(name: str, flags: str) -> dict[str, str]:
    return {
        "benchmark": name,
        "lang": "harness",
        "variant": "ci",
        "threads": "1",
        "metric": "verify_only",
        "value": "1",
        "unit": "bool",
        "git_sha": git_sha_short(),
        "cpu_model": cpu_model(),
        "flags": flags,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})


def verify_http_get(url: str, expect_status: int = 200) -> bool:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return int(resp.status) == expect_status
    except (urllib.error.URLError, OSError, ValueError):
        return False


def verify_toml(name: str) -> bool:
    merge_scenario(name)
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="tier5_http bench harness")
    p.add_argument("scenario", nargs="?", default=None, help="single scenario id (default: suite profile)")
    p.add_argument("--profile", default="ci", help="suite.toml profile name")
    p.add_argument("--csv", type=Path, default=None, help="output CSV (default: <repo>/results/latest.csv)")
    p.add_argument(
        "--no-bench",
        action="store_true",
        help="TOML verify + harness-only CSV rows (no nginx/wrk)",
    )
    args = p.parse_args()

    csv_path = args.csv
    if csv_path is None:
        csv_path = lis_repo_root() / "results" / "latest.csv"

    if args.scenario:
        scenarios = [args.scenario]
        _, timing = load_suite(args.profile)
    else:
        scenarios, timing = load_suite(args.profile)
    quick = not timing

    all_rows: list[dict[str, str]] = []
    for name in scenarios:
        try:
            verify_toml(name)
        except Exception as e:
            print(f"bench_http: TOML error {name}: {e}", file=sys.stderr)
            return 1
        if args.no_bench:
            all_rows.append(_harness_row(name, "no_bench_flag"))
            continue
        cfg = merge_scenario(name)
        rows, _log = bench_nginx_scenario(name, cfg, quick=quick)
        all_rows.extend(rows)

    write_csv(csv_path, all_rows)
    print(f"bench_http: wrote {len(all_rows)} row(s) -> {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())