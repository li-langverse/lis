"""Bearer token resolution for registry publish/yank."""

from __future__ import annotations

from .store import get_auth_store


def resolve_registry_bearer(token: str | None) -> dict[str, object] | None:
    if not token:
        return None
    return get_auth_store().resolve_bearer_token(token)
