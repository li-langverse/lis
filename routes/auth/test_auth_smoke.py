#!/usr/bin/env python3
"""Smoke test for /v1/auth signup, login, tokens."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from routes.auth.store import reset_auth_store  # noqa: E402
from routes.registry.handlers import handle_request  # noqa: E402


def _call(method: str, path: str, *, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    raw = json.dumps(body or {}).encode("utf-8") if body is not None else b""
    headers: dict[str, str] = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, _, payload = handle_request(method, path, headers=headers, body=raw)
    return status, json.loads(payload.decode("utf-8"))


def main() -> int:
    os.environ.setdefault("LI_JWT_SECRET", "smoke-test-secret")
    os.environ.setdefault("LI_REGISTRY_MOCK", "1")
    tmp = tempfile.mkdtemp(prefix="lis-auth-smoke-")
    os.environ["LI_DATA_DIR"] = tmp
    reset_auth_store()
    from routes.registry.store import reset_registry_store

    reset_registry_store()

    status, signup = _call(
        "POST",
        "/v1/auth/signup",
        body={"email": "smoke@example.com", "password": "smoke-pass-1", "publisher_name": "smoke-pub"},
    )
    assert status == 201, signup
    session = signup["access_token"]

    status, login = _call(
        "POST",
        "/v1/auth/login",
        body={"email": "smoke@example.com", "password": "smoke-pass-1"},
    )
    assert status == 200, login
    assert login["access_token"]

    status, created = _call("POST", "/v1/auth/tokens", body={"name": "ci", "scope": "publish"}, token=session)
    assert status == 201, created
    api_token = created["token"]
    token_id = created["id"]

    status, listed = _call("GET", "/v1/auth/tokens", token=session)
    assert status == 200, listed
    assert listed["total"] >= 1

    status, pub = _call(
        "POST",
        "/v1/packages/smoke-pkg/versions",
        body={
            "version": "0.1.0",
            "tree_digest": "sha256:" + "a" * 64,
            "proof_digest": "sha256:" + "b" * 64,
            "coverage_pct": 90.0,
        },
        token=api_token,
    )
    assert status == 201, pub

    status, revoked = _call("DELETE", f"/v1/auth/tokens/{token_id}", token=session)
    assert status == 200, revoked

    status, who = _call("GET", "/v1/auth/whoami", token=session)
    assert status == 200, who
    assert who["email"] == "smoke@example.com"

    status, dev = _call("POST", "/v1/auth/device/start")
    assert status == 200, dev
    assert dev.get("device_code") and dev.get("user_code")

    status, approved = _call(
        "POST",
        "/v1/auth/device/approve",
        body={"user_code": dev["user_code"]},
        token=session,
    )
    assert status == 200, approved

    status, polled = _call("POST", "/v1/auth/device/poll", body={"device_code": dev["device_code"]})
    assert status == 200, polled
    assert polled.get("status") == "complete"
    assert polled.get("token")

    print("auth smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
