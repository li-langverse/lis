#!/usr/bin/env python3
"""Minimal registry API listener for registry-min profile (PH-DB-4 stub)."""

from __future__ import annotations

import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from routes.registry.handlers import handle_request  # noqa: E402


class RegistryHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        if os.environ.get("LIS_REGISTRY_QUIET"):
            return
        super().log_message(fmt, *args)

    def _dispatch(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b""
        hdrs = {k: v for k, v in self.headers.items()}
        status, resp_headers, payload = handle_request(
            self.command,
            self.path,
            headers=hdrs,
            body=body,
        )
        self.send_response(status)
        for key, value in resp_headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        self._dispatch()

    def do_POST(self) -> None:
        self._dispatch()

    def do_HEAD(self) -> None:
        self._dispatch()


def main() -> None:
    parser = argparse.ArgumentParser(description="lis registry REST stub")
    parser.add_argument("--host", default=os.environ.get("LI_REGISTRY_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LI_API_PORT", os.environ.get("LI_REGISTRY_PORT", "54321"))),
    )
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), RegistryHandler)
    print(f"lis registry API (stub): http://{args.host}:{args.port}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
