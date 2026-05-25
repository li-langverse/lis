"""JWT claims + RLS row filter for Realtime postgres_changes (stub; see docs/realtime.md)."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JwtClaims:
    sub: str | None
    role: str
    publisher_id: str | None

    @property
    def is_service_role(self) -> bool:
        return self.role == "service_role"


def claims_from_access_token(token: str | None) -> JwtClaims:
    if not token:
        return JwtClaims(sub=None, role="anon", publisher_id=None)
    payload = _decode_jwt_payload_unverified(token)
    role = str(payload.get("role") or "authenticated")
    sub = payload.get("sub")
    publisher_id = payload.get("publisher_id")
    return JwtClaims(
        sub=str(sub) if sub is not None else None,
        role=role,
        publisher_id=str(publisher_id) if publisher_id is not None else None,
    )


def authorize_join(claims: JwtClaims, *, require_auth: bool) -> str | None:
    """Return error string if join must be rejected."""
    if not require_auth:
        return None
    if claims.role == "anon" and not claims.sub:
        return "missing or invalid access_token"
    return None


def rls_allows_row(claims: JwtClaims, row: dict[str, Any]) -> bool:
    """Registry-shaped RLS: service_role sees all; authenticated matches publisher_id."""
    if claims.is_service_role:
        return True
    tenant = claims.publisher_id
    if tenant is None:
        return claims.role == "anon"
    row_tenant = row.get("publisher_id")
    if row_tenant is None:
        return True
    return str(row_tenant) == tenant


def row_from_changefeed_record(record: dict[str, Any]) -> dict[str, Any]:
    return record if isinstance(record, dict) else {}


def _decode_jwt_payload_unverified(token: str) -> dict[str, Any]:
    secret = os.environ.get("LI_REALTIME_JWT_SECRET")
    if secret:
        return _decode_with_hs256(token, secret)
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _decode_with_hs256(token: str, secret: str) -> dict[str, Any]:
    try:
        import hmac
        import hashlib
    except ImportError:
        return _decode_jwt_payload_unverified(token)

    parts = token.split(".")
    if len(parts) != 3:
        return {}
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    try:
        sig = base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))
    except ValueError:
        return {}
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        return {}
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
