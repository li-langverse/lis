"""Bearer token resolution for registry publish/yank."""

from __future__ import annotations

from .jwt_util import decode_jwt
from .store import get_auth_store

_AUDIT_SCOPES = frozenset({"audit", "publish+audit", "publish+yank", "admin"})


def resolve_registry_bearer(token: str | None) -> dict[str, object] | None:
    if not token:
        return None
    return get_auth_store().resolve_bearer_token(token)


def resolve_audit_bearer(token: str | None) -> dict[str, object] | None:
    if not token:
        return None
    ctx = resolve_registry_bearer(token)
    if ctx is not None:
        scope = str(ctx.get("scope", ""))
        if scope in _AUDIT_SCOPES:
            return ctx
        return None
    claims = decode_jwt(token)
    if claims and claims.get("typ") == "session":
        sub = claims.get("sub")
        if sub:
            return {"user_id": str(sub), "scope": "audit", "source": "session"}
    return None
