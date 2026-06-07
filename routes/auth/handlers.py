"""Auth REST handlers — /v1/auth/* (signup, login, token CRUD)."""

from __future__ import annotations

import json
import re
from typing import Any

from .errors import AuthError
from .jwt_util import decode_jwt
from .store import get_auth_store

_TOKEN_ID_RE = re.compile(r"^[0-9a-f-]{36}$")


def _json_response(status: int, body: dict[str, Any]) -> tuple[int, dict[str, str], bytes]:
    payload = json.dumps(body).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(payload)),
    }
    return status, headers, payload


def _error_response(exc: AuthError) -> tuple[int, dict[str, str], bytes]:
    body: dict[str, Any] = {"error": exc.error, "message": exc.message}
    if exc.details:
        body["details"] = exc.details
    return _json_response(exc.status, body)


def _parse_bearer(headers: dict[str, str]) -> str | None:
    auth = headers.get("Authorization") or headers.get("authorization")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _session_user_id(token: str | None) -> str | None:
    if not token:
        return None
    claims = decode_jwt(token)
    if not claims or claims.get("typ") != "session":
        return None
    sub = claims.get("sub")
    return str(sub) if sub else None


def handle_auth_request(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, dict[str, str], bytes] | None:
    """Dispatch /v1/auth/*; returns None when route is not auth."""
    headers = headers or {}
    route = path.rstrip("/") or "/"
    if not route.startswith("/v1/auth"):
        return None

    store = get_auth_store()

    if method == "POST" and route == "/v1/auth/signup":
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return _json_response(400, {"error": "bad_request", "message": "invalid JSON body"})
        email = payload.get("email", "")
        password = payload.get("password", "")
        if not email or not password:
            return _json_response(400, {"error": "bad_request", "message": "email and password required"})
        try:
            result = store.signup(
                email,
                password,
                publisher_name=payload.get("publisher_name"),
                signup_token=payload.get("signup_token"),
            )
            return _json_response(201, result)
        except AuthError as exc:
            return _error_response(exc)
        except RuntimeError as exc:
            return _json_response(500, {"error": "misconfigured", "message": str(exc)})

    if method == "POST" and route == "/v1/auth/login":
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return _json_response(400, {"error": "bad_request", "message": "invalid JSON body"})
        email = payload.get("email", "")
        password = payload.get("password", "")
        if not email or not password:
            return _json_response(400, {"error": "bad_request", "message": "email and password required"})
        try:
            result = store.login(email, password)
            return _json_response(200, result)
        except AuthError as exc:
            return _error_response(exc)
        except RuntimeError as exc:
            return _json_response(500, {"error": "misconfigured", "message": str(exc)})

    if method == "POST" and route == "/v1/auth/tokens":
        session = _parse_bearer(headers)
        user_id = _session_user_id(session)
        if not user_id:
            return _json_response(401, {"error": "unauthorized", "message": "valid session bearer required"})
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return _json_response(400, {"error": "bad_request", "message": "invalid JSON body"})
        try:
            result = store.create_api_token(
                user_id=user_id,
                name=payload.get("name"),
                scope=payload.get("scope", "publish"),
                expires_in=payload.get("expires_in"),
            )
            return _json_response(201, result)
        except AuthError as exc:
            return _error_response(exc)

    if method == "GET" and route == "/v1/auth/tokens":
        session = _parse_bearer(headers)
        user_id = _session_user_id(session)
        if not user_id:
            return _json_response(401, {"error": "unauthorized", "message": "valid session bearer required"})
        try:
            return _json_response(200, store.list_api_tokens(user_id=user_id))
        except AuthError as exc:
            return _error_response(exc)

    m = re.match(r"^/v1/auth/tokens/([^/]+)$", route)
    if method == "DELETE" and m:
        token_id = m.group(1)
        if not _TOKEN_ID_RE.match(token_id):
            return _json_response(400, {"error": "bad_request", "message": "invalid token id"})
        session = _parse_bearer(headers)
        user_id = _session_user_id(session)
        if not user_id:
            return _json_response(401, {"error": "unauthorized", "message": "valid session bearer required"})
        try:
            return _json_response(200, store.revoke_api_token(user_id=user_id, token_id=token_id))
        except AuthError as exc:
            return _error_response(exc)

    if method == "POST" and route == "/v1/auth/signup-tokens":
        session = _parse_bearer(headers)
        user_id = _session_user_id(session)
        if not user_id:
            return _json_response(401, {"error": "unauthorized", "message": "valid session bearer required"})
        try:
            payload = json.loads(body or b"{}")
        except json.JSONDecodeError:
            return _json_response(400, {"error": "bad_request", "message": "invalid JSON body"})
        mint = getattr(store, "mint_signup_token", None)
        if not callable(mint):
            return _json_response(501, {"error": "not_implemented", "message": "signup tokens not supported"})
        try:
            result = mint(
                created_by=user_id,
                email_hint=payload.get("email_hint"),
                max_uses=int(payload.get("max_uses", 1)),
                ttl_hours=payload.get("ttl_hours", 168),
            )
            return _json_response(201, result)
        except AuthError as exc:
            return _error_response(exc)
        except (TypeError, ValueError) as exc:
            return _json_response(400, {"error": "bad_request", "message": str(exc)})

    return _json_response(404, {"error": "not_found", "message": f"no auth route for {method} {route}"})
