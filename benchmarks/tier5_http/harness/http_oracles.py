"""Shared loopback webserver oracles for tier-5 HTTP bench + exploit harnesses."""
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

# Performance + security oracles (comma-separated env overrides).
DEFAULT_BENCH_ORACLES = ("nginx", "apache", "lighttpd", "node", "bun", "li")
DEFAULT_EXPLOIT_ORACLES = ("nginx", "apache", "node", "bun", "li")
STATIC_ORACLES = frozenset({"nginx", "apache", "lighttpd", "caddy", "node", "bun"})
DEFAULT_PROXY_ORACLES = ("nginx", "apache", "lighttpd", "caddy", "li")
PROXY_ORACLES = frozenset(DEFAULT_PROXY_ORACLES)


def parse_oracle_langs(env_var: str, default: tuple[str, ...]) -> list[str]:
    raw = os.environ.get(env_var, "").strip()
    if not raw:
        return list(default)
    out: list[str] = []
    for part in raw.split(","):
        lang = part.strip().lower()
        if lang and lang not in out:
            out.append(lang)
    return out


def pick_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    _, port = s.getsockname()
    s.close()
    return int(port)


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


def oracle_available(lang: str) -> bool:
    lang = lang.lower()
    if lang == "nginx":
        return shutil.which("nginx") is not None
    if lang == "apache":
        return bool(shutil.which("apache2") or shutil.which("apachectl") or shutil.which("httpd"))
    if lang == "lighttpd":
        return shutil.which("lighttpd") is not None
    if lang == "caddy":
        return shutil.which("caddy") is not None
    if lang == "li":
        return resolve_li_httpd_bin() is not None
    if lang == "node":
        return shutil.which("node") is not None and static_server_script().is_file()
    if lang == "bun":
        return shutil.which("bun") is not None and static_server_script().is_file()
    return False


def static_server_script() -> Path:
    return Path(__file__).resolve().parent / "static_server.mjs"


def runtime_version(lang: str) -> str:
    lang = lang.lower()
    exe = lang if lang in ("node", "bun") else None
    if not exe:
        return ""
    try:
        proc = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        line = (proc.stdout or proc.stderr or "").strip().split("\n", 1)[0]
        return line[:80]
    except (OSError, subprocess.TimeoutExpired):
        return ""


def resolve_li_httpd_bin() -> Path | None:
    env = os.environ.get("LI_HTTPD_BIN")
    if env and Path(env).is_file():
        return Path(env)
    tier5 = Path(__file__).resolve().parents[1]
    lis_root = tier5.parents[1]
    for c in (
        lis_root.parent / "lic" / "build" / "li-httpd",
        Path(os.environ.get("LIC_ROOT", "")) / "build" / "li-httpd",
        Path("/workspace/lic/build/li-httpd"),
    ):
        if c.is_file():
            return c
    return None


# --- nginx ---


def parse_proxy_oracle_langs() -> list[str]:
    return parse_oracle_langs("BENCH_PROXY_ORACLES", DEFAULT_PROXY_ORACLES)


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
events {{ worker_connections 1024; }}
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
        return False
    pid_path = prefix / "nginx.pid"
    for _ in range(200):
        if pid_path.is_file():
            time.sleep(0.02)
            return True
        time.sleep(0.02)
    return False


def stop_nginx(prefix: Path) -> None:
    pid_path = prefix / "nginx.pid"
    if pid_path.is_file():
        try:
            os.kill(int(pid_path.read_text().strip()), signal.SIGQUIT)
        except (ValueError, ProcessLookupError, OSError):
            pass
    time.sleep(0.1)


# --- apache ---


def apache_modules_dir() -> str:
    for d in ("/usr/lib/apache2/modules", "/usr/lib64/httpd/modules", "/usr/lib/httpd/modules"):
        if Path(d).is_dir():
            return d
    return "/usr/lib/apache2/modules"


def apache_prefix_conf(document_root: Path, port: int, prefix: Path) -> str:
    dr = str(document_root.resolve()).replace("\\", "/")
    px = str(prefix.resolve()).replace("\\", "/")
    mod = apache_modules_dir()
    return f"""ServerRoot "{px}"
ServerName 127.0.0.1
PidFile logs/httpd.pid
ErrorLog logs/error.log
LoadModule mpm_event_module {mod}/mod_mpm_event.so
LoadModule authz_core_module {mod}/mod_authz_core.so
LoadModule dir_module {mod}/mod_dir.so
LoadModule mime_module {mod}/mod_mime.so
TypesConfig /etc/mime.types
Listen 127.0.0.1:{port}
DocumentRoot "{dr}"
<Directory "{dr}">
    Require all granted
    Options -Indexes +FollowSymLinks
</Directory>
"""


def launch_apache(prefix: Path, conf_text: str, port: int) -> bool:
    prefix.mkdir(parents=True, exist_ok=True)
    (prefix / "logs").mkdir(parents=True, exist_ok=True)
    (prefix / "apache.conf").write_text(conf_text, encoding="utf-8")
    apache = shutil.which("apache2") or shutil.which("apachectl") or shutil.which("httpd")
    if not apache:
        return False
    conf_path = str((prefix / "apache.conf").resolve())
    subprocess.run(
        [apache, "-f", conf_path, "-k", "start"],
        cwd=prefix,
        capture_output=True,
        text=True,
        check=False,
    )
    return wait_for_port(port, timeout_sec=5.0)


def stop_apache(prefix: Path) -> None:
    apache = shutil.which("apache2") or shutil.which("apachectl") or shutil.which("httpd")
    if not apache:
        return
    conf_path = str((prefix / "apache.conf").resolve())
    subprocess.run(
        [apache, "-f", conf_path, "-k", "stop"],
        cwd=prefix,
        capture_output=True,
        text=True,
        check=False,
    )
    time.sleep(0.05)


# --- lighttpd ---


def lighttpd_modules_dir() -> str:
    for d in ("/usr/lib/lighttpd", "/usr/lib64/lighttpd"):
        if Path(d).is_dir():
            return d
    return "/usr/lib/lighttpd"


def lighttpd_prefix_conf(document_root: Path, port: int, prefix: Path) -> str:
    dr = str(document_root.resolve()).replace("\\", "/")
    px = str(prefix.resolve()).replace("\\", "/")
    return f"""server.modules = ("mod_indexfile", "mod_access", "mod_alias")
server.document-root = "{dr}"
server.port = {port}
server.bind = "127.0.0.1"
server.pid-file = "{px}/lighttpd.pid"
server.errorlog = "{px}/logs/error.log"
index-file.names = ("index.html")
dirlisting.activate = "disable"
"""


def launch_lighttpd(prefix: Path, conf_text: str, port: int) -> bool:
    prefix.mkdir(parents=True, exist_ok=True)
    (prefix / "logs").mkdir(parents=True, exist_ok=True)
    conf_path = prefix / "lighttpd.conf"
    conf_path.write_text(conf_text, encoding="utf-8")
    lighttpd = shutil.which("lighttpd")
    if not lighttpd:
        return False
    mod = lighttpd_modules_dir()
    proc = subprocess.run(
        [lighttpd, "-f", str(conf_path.resolve()), "-m", mod],
        cwd=prefix,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False
    return wait_for_port(port, timeout_sec=5.0)


def stop_lighttpd(prefix: Path) -> None:
    pid_path = prefix / "lighttpd.pid"
    if pid_path.is_file():
        try:
            os.kill(int(pid_path.read_text().strip()), signal.SIGTERM)
        except (ValueError, ProcessLookupError, OSError):
            pass
    time.sleep(0.05)


def apache_proxy_lb_conf(front_port: int, backend_ports: list[int], prefix: Path) -> str:
    mod = apache_modules_dir()
    members = "\n".join(f"    BalancerMember http://127.0.0.1:{p}" for p in backend_ports)
    px = str(prefix.resolve()).replace("\\", "/")
    return f"""ServerRoot "{px}"
ServerName 127.0.0.1
PidFile logs/httpd.pid
ErrorLog logs/error.log
LoadModule mpm_event_module {mod}/mod_mpm_event.so
LoadModule authz_core_module {mod}/mod_authz_core.so
LoadModule proxy_module {mod}/mod_proxy.so
LoadModule proxy_http_module {mod}/mod_proxy_http.so
LoadModule proxy_balancer_module {mod}/mod_proxy_balancer.so
LoadModule slotmem_shm_module {mod}/mod_slotmem_shm.so
LoadModule lbmethod_byrequests_module {mod}/mod_lbmethod_byrequests.so
Listen 127.0.0.1:{front_port}
ProxyPreserveHost On
<Proxy balancer://tier5>
{members}
  ProxySet lbmethod=byrequests
</Proxy>
ProxyPass / balancer://tier5/
ProxyPassReverse / balancer://tier5/
"""


def lighttpd_proxy_lb_conf(front_port: int, backend_ports: list[int], prefix: Path) -> str:
    px = str(prefix.resolve()).replace("\\", "/")
    docroot = px + "/htdocs"
    members = "\n".join(
        f'    ( "host" => "127.0.0.1", "port" => {p} ),' for p in backend_ports
    )
    return f"""server.modules = ("mod_proxy", "mod_indexfile", "mod_access")
server.document-root = "{docroot}"
server.port = {front_port}
server.bind = "127.0.0.1"
server.pid-file = "{px}/lighttpd.pid"
server.errorlog = "{px}/logs/error.log"
proxy.balance = "round-robin"
proxy.server = ("/" => (
{members}
))
"""


def caddy_proxy_lb_conf(front_port: int, backend_ports: list[int]) -> str:
    backends = " ".join(f"127.0.0.1:{p}" for p in backend_ports)
    return f"""127.0.0.1:{front_port} {{
  reverse_proxy {backends}
}}
"""


def ensure_tls_cert(tmp: Path) -> tuple[Path, Path] | None:
    cert = tmp / "tier5.pem"
    key = tmp / "tier5-key.pem"
    if cert.is_file() and key.is_file():
        return cert, key
    openssl = shutil.which("openssl")
    if not openssl:
        return None
    subprocess.run(
        [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=127.0.0.1",
        ],
        check=False,
        capture_output=True,
    )
    if cert.is_file() and key.is_file():
        return cert, key
    return None


def nginx_https_conf(document_root: Path, port: int, prefix: Path, cert: Path, key: Path) -> str:
    dr = str(document_root.resolve()).replace("\\", "/")
    px = str(prefix.resolve()).replace("\\", "/")
    crt = str(cert.resolve()).replace("\\", "/")
    k = str(key.resolve()).replace("\\", "/")
    return f"""worker_processes 1;
error_log {px}/error.log warn;
pid {px}/nginx.pid;
daemon on;
events {{ worker_connections 1024; }}
http {{
  access_log off;
  client_body_temp_path {px}/client_temp;
  server {{
    listen 127.0.0.1:{port} ssl;
    server_name _;
    ssl_certificate {crt};
    ssl_certificate_key {k};
    root {dr};
    location / {{ try_files $uri /index.html =404; }}
  }}
}}
"""


def apache_https_conf(document_root: Path, port: int, prefix: Path, cert: Path, key: Path) -> str:
    mod = apache_modules_dir()
    dr = str(document_root.resolve()).replace("\\", "/")
    px = str(prefix.resolve()).replace("\\", "/")
    crt = str(cert.resolve()).replace("\\", "/")
    k = str(key.resolve()).replace("\\", "/")
    return f"""ServerRoot "{px}"
PidFile logs/httpd.pid
ErrorLog logs/error.log
LoadModule mpm_event_module {mod}/mod_mpm_event.so
LoadModule authz_core_module {mod}/mod_authz_core.so
LoadModule ssl_module {mod}/mod_ssl.so
LoadModule dir_module {mod}/mod_dir.so
Listen 127.0.0.1:{port}
DocumentRoot "{dr}"
<Directory "{dr}">
  Require all granted
</Directory>
SSLEngine on
SSLCertificateFile "{crt}"
SSLCertificateKeyFile "{k}"
"""


def lighttpd_https_conf(document_root: Path, port: int, prefix: Path, cert: Path, key: Path) -> str:
    dr = str(document_root.resolve()).replace("\\", "/")
    px = str(prefix.resolve()).replace("\\", "/")
    crt = str(cert.resolve()).replace("\\", "/")
    k = str(key.resolve()).replace("\\", "/")
    return f"""server.modules = ("mod_openssl", "mod_indexfile")
server.document-root = "{dr}"
server.port = {port}
server.bind = "127.0.0.1"
server.pid-file = "{px}/lighttpd.pid"
server.errorlog = "{px}/logs/error.log"
ssl.engine = "enable"
ssl.pemfile = "{crt}"
ssl.privkey = "{k}"
index-file.names = ("index.html")
"""


def caddy_https_conf(document_root: Path, port: int, cert: Path, key: Path) -> str:
    dr = str(document_root.resolve()).replace("\\", "/")
    crt = str(cert.resolve()).replace("\\", "/")
    k = str(key.resolve()).replace("\\", "/")
    return f"""127.0.0.1:{port} {{
  tls {crt} {k}
  root * {dr}
  file_server
}}
"""


# --- caddy ---


def caddy_prefix_conf(document_root: Path, port: int) -> str:
    dr = str(document_root.resolve()).replace("\\", "/")
    return f"""127.0.0.1:{port} {{
  root * {dr}
  file_server
}}
"""


def launch_caddy(prefix: Path, conf_text: str, port: int) -> subprocess.Popen[str] | None:
    prefix.mkdir(parents=True, exist_ok=True)
    conf_path = prefix / "Caddyfile"
    conf_path.write_text(conf_text, encoding="utf-8")
    caddy = shutil.which("caddy")
    if not caddy:
        return None
    proc = subprocess.Popen(
        [caddy, "run", "--config", str(conf_path.resolve()), "--adapter", "caddyfile"],
        cwd=prefix,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not wait_for_port(port, timeout_sec=5.0):
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        return None
    return proc


def stop_caddy(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# --- bench helpers (temp dir + prefix or subprocess) ---


def start_nginx_bench(port: int, doc_root: Path) -> tuple[tempfile.TemporaryDirectory[str], Path] | None:
    tmp = tempfile.TemporaryDirectory(prefix="lis-nginx-")
    prefix = Path(tmp.name)
    conf = nginx_prefix_conf(doc_root, port, prefix)
    if not launch_nginx(prefix, conf):
        tmp.cleanup()
        return None
    return tmp, prefix


def stop_nginx_bench(ctx: tuple[tempfile.TemporaryDirectory[str], Path] | None) -> None:
    if not ctx:
        return
    tmp, prefix = ctx
    stop_nginx(prefix)
    tmp.cleanup()


def start_apache_bench(port: int, doc_root: Path) -> tuple[tempfile.TemporaryDirectory[str], Path] | None:
    tmp = tempfile.TemporaryDirectory(prefix="lis-apache-")
    prefix = Path(tmp.name)
    conf = apache_prefix_conf(doc_root, port, prefix)
    if not launch_apache(prefix, conf, port):
        tmp.cleanup()
        return None
    return tmp, prefix


def stop_apache_bench(ctx: tuple[tempfile.TemporaryDirectory[str], Path] | None) -> None:
    if not ctx:
        return
    tmp, prefix = ctx
    stop_apache(prefix)
    tmp.cleanup()


def start_lighttpd_bench(port: int, doc_root: Path) -> tuple[tempfile.TemporaryDirectory[str], Path] | None:
    tmp = tempfile.TemporaryDirectory(prefix="lis-lighttpd-")
    prefix = Path(tmp.name)
    conf = lighttpd_prefix_conf(doc_root, port, prefix)
    if not launch_lighttpd(prefix, conf, port):
        tmp.cleanup()
        return None
    return tmp, prefix


def stop_lighttpd_bench(ctx: tuple[tempfile.TemporaryDirectory[str], Path] | None) -> None:
    if not ctx:
        return
    tmp, prefix = ctx
    stop_lighttpd(prefix)
    tmp.cleanup()


def start_caddy_bench(port: int, doc_root: Path) -> tuple[tempfile.TemporaryDirectory[str], subprocess.Popen[str]] | None:
    tmp = tempfile.TemporaryDirectory(prefix="lis-caddy-")
    prefix = Path(tmp.name)
    conf = caddy_prefix_conf(doc_root, port)
    proc = launch_caddy(prefix, conf, port)
    if proc is None:
        tmp.cleanup()
        return None
    return tmp, proc


def stop_caddy_bench(ctx: tuple[tempfile.TemporaryDirectory[str], subprocess.Popen[str]] | None) -> None:
    if not ctx:
        return
    tmp, proc = ctx
    stop_caddy(proc)
    tmp.cleanup()


def start_li_bench(port: int, doc_root: Path) -> subprocess.Popen[str] | None:
    li_bin = resolve_li_httpd_bin()
    if not li_bin:
        return None
    return subprocess.Popen(
        [str(li_bin), str(port), str(doc_root.resolve())],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_li_bench(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def start_js_runtime_bench(runtime: str, port: int, doc_root: Path) -> subprocess.Popen[str] | None:
    exe = shutil.which(runtime)
    script = static_server_script()
    if not exe or not script.is_file():
        return None
    env = os.environ.copy()
    env["TIER5_HTTP_SERVER_READY"] = "0"
    return subprocess.Popen(
        [exe, str(script.resolve()), str(port), str(doc_root.resolve())],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )


def start_node_bench(port: int, doc_root: Path) -> subprocess.Popen[str] | None:
    return start_js_runtime_bench("node", port, doc_root)


def stop_node_bench(proc: subprocess.Popen[str] | None) -> None:
    stop_li_bench(proc)


def start_bun_bench(port: int, doc_root: Path) -> subprocess.Popen[str] | None:
    return start_js_runtime_bench("bun", port, doc_root)


def stop_bun_bench(proc: subprocess.Popen[str] | None) -> None:
    stop_li_bench(proc)


def start_nginx_proxy_bench(
    front_port: int, doc_root: Path, backend_ports: list[int]
) -> tuple[tempfile.TemporaryDirectory[str], Path] | None:
    tmp = tempfile.TemporaryDirectory(prefix="lis-nginx-proxy-")
    prefix = Path(tmp.name)
    conf = nginx_lb_proxy_prefix_conf(front_port, backend_ports, prefix)
    if not launch_nginx(prefix, conf):
        tmp.cleanup()
        return None
    return tmp, prefix


def stop_nginx_proxy_bench(ctx: tuple[tempfile.TemporaryDirectory[str], Path] | None) -> None:
    stop_nginx_bench(ctx)


def start_apache_proxy_bench(
    front_port: int, doc_root: Path, backend_ports: list[int]
) -> tuple[tempfile.TemporaryDirectory[str], Path] | None:
    _ = doc_root
    tmp = tempfile.TemporaryDirectory(prefix="lis-apache-proxy-")
    prefix = Path(tmp.name)
    conf = apache_proxy_lb_conf(front_port, backend_ports, prefix)
    if not launch_apache(prefix, conf, front_port):
        tmp.cleanup()
        return None
    return tmp, prefix


def stop_apache_proxy_bench(ctx: tuple[tempfile.TemporaryDirectory[str], Path] | None) -> None:
    stop_apache_bench(ctx)


def start_lighttpd_proxy_bench(
    front_port: int, doc_root: Path, backend_ports: list[int]
) -> tuple[tempfile.TemporaryDirectory[str], Path] | None:
    _ = doc_root
    tmp = tempfile.TemporaryDirectory(prefix="lis-lighttpd-proxy-")
    prefix = Path(tmp.name)
    (prefix / "htdocs").mkdir(parents=True, exist_ok=True)
    conf = lighttpd_proxy_lb_conf(front_port, backend_ports, prefix)
    if not launch_lighttpd(prefix, conf, front_port):
        tmp.cleanup()
        return None
    return tmp, prefix


def stop_lighttpd_proxy_bench(ctx: tuple[tempfile.TemporaryDirectory[str], Path] | None) -> None:
    stop_lighttpd_bench(ctx)


def start_caddy_proxy_bench(
    front_port: int, doc_root: Path, backend_ports: list[int]
) -> tuple[tempfile.TemporaryDirectory[str], subprocess.Popen[str]] | None:
    _ = doc_root
    tmp = tempfile.TemporaryDirectory(prefix="lis-caddy-proxy-")
    prefix = Path(tmp.name)
    conf = caddy_proxy_lb_conf(front_port, backend_ports)
    proc = launch_caddy(prefix, conf, front_port)
    if proc is None:
        tmp.cleanup()
        return None
    return tmp, proc


def stop_caddy_proxy_bench(ctx: tuple[tempfile.TemporaryDirectory[str], subprocess.Popen[str]] | None) -> None:
    stop_caddy_bench(ctx)


def start_li_proxy_bench(
    front_port: int, doc_root: Path, backend_ports: list[int]
) -> subprocess.Popen[str] | None:
    li_bin = resolve_li_httpd_bin()
    if not li_bin:
        return None
    csv_ports = ",".join(str(p) for p in backend_ports)
    cmd = [str(li_bin), str(front_port), str(doc_root.resolve()), csv_ports]
    if os.environ.get("BENCH_HTTP_LB_MODE", "").strip() == "least_conn":
        cmd.append("least_conn")
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stop_li_proxy_bench(proc: subprocess.Popen[str] | None) -> None:
    stop_li_bench(proc)


def start_nginx_static_backends(
    backend_ports: list[int], doc_root: Path
) -> list[tuple[tempfile.TemporaryDirectory[str], Path]]:
    out: list[tuple[tempfile.TemporaryDirectory[str], Path]] = []
    for bp in backend_ports:
        ctx = start_nginx_bench(bp, doc_root)
        if ctx:
            out.append(ctx)
        else:
            break
    return out


def stop_nginx_static_backends(backends: list[tuple[tempfile.TemporaryDirectory[str], Path]]) -> None:
    for ctx in backends:
        stop_nginx_bench(ctx)


ProxyStarter = Callable[[int, Path, list[int]], Any]
ProxyStopper = Callable[[Any], None]

PROXY_BENCH_HOOKS: dict[str, tuple[ProxyStarter, ProxyStopper]] = {
    "nginx": (start_nginx_proxy_bench, stop_nginx_proxy_bench),
    "apache": (start_apache_proxy_bench, stop_apache_proxy_bench),
    "lighttpd": (start_lighttpd_proxy_bench, stop_lighttpd_proxy_bench),
    "caddy": (start_caddy_proxy_bench, stop_caddy_proxy_bench),
    "li": (start_li_proxy_bench, stop_li_proxy_bench),
}


def start_nginx_https_bench(
    port: int, doc_root: Path, cert: Path, key: Path
) -> tuple[tempfile.TemporaryDirectory[str], Path] | None:
    tmp = tempfile.TemporaryDirectory(prefix="lis-nginx-tls-")
    prefix = Path(tmp.name)
    conf = nginx_https_conf(doc_root, port, prefix, cert, key)
    if not launch_nginx(prefix, conf):
        tmp.cleanup()
        return None
    return tmp, prefix


def start_apache_https_bench(
    port: int, doc_root: Path, cert: Path, key: Path
) -> tuple[tempfile.TemporaryDirectory[str], Path] | None:
    tmp = tempfile.TemporaryDirectory(prefix="lis-apache-tls-")
    prefix = Path(tmp.name)
    conf = apache_https_conf(doc_root, port, prefix, cert, key)
    if not launch_apache(prefix, conf, port):
        tmp.cleanup()
        return None
    return tmp, prefix


def start_lighttpd_https_bench(
    port: int, doc_root: Path, cert: Path, key: Path
) -> tuple[tempfile.TemporaryDirectory[str], Path] | None:
    tmp = tempfile.TemporaryDirectory(prefix="lis-lighttpd-tls-")
    prefix = Path(tmp.name)
    conf = lighttpd_https_conf(doc_root, port, prefix, cert, key)
    if not launch_lighttpd(prefix, conf, port):
        tmp.cleanup()
        return None
    return tmp, prefix


def start_caddy_https_bench(
    port: int, doc_root: Path, cert: Path, key: Path
) -> tuple[tempfile.TemporaryDirectory[str], subprocess.Popen[str]] | None:
    tmp = tempfile.TemporaryDirectory(prefix="lis-caddy-tls-")
    prefix = Path(tmp.name)
    conf = caddy_https_conf(doc_root, port, cert, key)
    proc = launch_caddy(prefix, conf, port)
    if proc is None:
        tmp.cleanup()
        return None
    return tmp, proc


TlsStarter = Callable[[int, Path, Path, Path], Any]
TlsStopper = Callable[[Any], None]

TLS_BENCH_HOOKS: dict[str, tuple[TlsStarter, TlsStopper]] = {
    "nginx": (start_nginx_https_bench, stop_nginx_proxy_bench),
    "apache": (start_apache_https_bench, stop_apache_proxy_bench),
    "lighttpd": (start_lighttpd_https_bench, stop_lighttpd_proxy_bench),
    "caddy": (start_caddy_https_bench, stop_caddy_proxy_bench),
}


BenchStarter = Callable[[int, Path], Any]
BenchStopper = Callable[[Any], None]

BENCH_ORACLE_HOOKS: dict[str, tuple[BenchStarter, BenchStopper]] = {
    "nginx": (start_nginx_bench, stop_nginx_bench),
    "apache": (start_apache_bench, stop_apache_bench),
    "lighttpd": (start_lighttpd_bench, stop_lighttpd_bench),
    "caddy": (start_caddy_bench, stop_caddy_bench),
    "node": (start_node_bench, stop_node_bench),
    "bun": (start_bun_bench, stop_bun_bench),
    "li": (start_li_bench, stop_li_bench),
}


# --- exploit helpers (return (tmpdir, prefix) or Popen) ---


def exploit_start(lang: str, port: int, doc_root: Path):
    if lang == "nginx":
        tmp = tempfile.TemporaryDirectory(prefix="lis-exploit-nginx-")
        prefix = Path(tmp.name)
        conf = nginx_prefix_conf(doc_root, port, prefix)
        if not launch_nginx(prefix, conf):
            tmp.cleanup()
            return None, None
        return (tmp, prefix), "nginx"

    if lang == "apache":
        tmp = tempfile.TemporaryDirectory(prefix="lis-exploit-apache-")
        prefix = Path(tmp.name)
        conf = apache_prefix_conf(doc_root, port, prefix)
        if not launch_apache(prefix, conf, port):
            tmp.cleanup()
            return None, None
        return (tmp, prefix), "apache"

    if lang == "lighttpd":
        tmp = tempfile.TemporaryDirectory(prefix="lis-exploit-lighttpd-")
        prefix = Path(tmp.name)
        conf = lighttpd_prefix_conf(doc_root, port, prefix)
        if not launch_lighttpd(prefix, conf, port):
            tmp.cleanup()
            return None, None
        return (tmp, prefix), "lighttpd"

    if lang == "caddy":
        tmp = tempfile.TemporaryDirectory(prefix="lis-exploit-caddy-")
        prefix = Path(tmp.name)
        conf = caddy_prefix_conf(doc_root, port)
        proc = launch_caddy(prefix, conf, port)
        if proc is None:
            tmp.cleanup()
            return None, None
        return (tmp, proc), "caddy"

    if lang in ("node", "bun"):
        proc = start_js_runtime_bench(lang, port, doc_root)
        if proc is None:
            return None, None
        if not wait_for_port(port, timeout_sec=8.0):
            proc.kill()
            return None, None
        return proc, lang

    if lang == "li":
        li_bin = resolve_li_httpd_bin()
        if not li_bin:
            return None, None
        proc = subprocess.Popen(
            [str(li_bin), str(port), str(doc_root.resolve())],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_port(port):
            proc.kill()
            return None, None
        return proc, "li"

    return None, None


def exploit_stop(lang: str, ctx: Any) -> None:
    if ctx is None:
        return
    if lang in ("nginx", "apache", "lighttpd"):
        tmp, prefix = ctx
        if lang == "nginx":
            stop_nginx(prefix)
        elif lang == "apache":
            stop_apache(prefix)
        else:
            stop_lighttpd(prefix)
        tmp.cleanup()
    elif lang == "caddy":
        tmp, proc = ctx
        stop_caddy(proc)
        tmp.cleanup()
    elif lang in ("li", "node", "bun"):
        stop_li_bench(ctx)
