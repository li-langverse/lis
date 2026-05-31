#!/usr/bin/env python3
"""lis MQ edge listener — /v1/mq/* per limq/lis/routes.md."""

from __future__ import annotations

import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from routes.mq.handlers import UPSTREAM, handle_request  # noqa: E402


class MqHandler(BaseHTTPRequestHandler):
    server_version = "lis-mq/1"

    def log_message(self, fmt: str, *args: object) -> None:
        if os.environ.get("LI_MQ_BENCH_QUIET") == "1":
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
    parser = argparse.ArgumentParser(description="lis MQ REST edge")
    parser.add_argument("--host", default=os.environ.get("LIS_MQ_BIND", "0.0.0.0:8080").rsplit(":", 1)[0])
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LIS_MQ_BIND", "0.0.0.0:8080").rsplit(":", 1)[-1]),
    )
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MqHandler)
    print(f"lis MQ edge: http://{args.host}:{args.port}/v1/mq/* -> {UPSTREAM}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
