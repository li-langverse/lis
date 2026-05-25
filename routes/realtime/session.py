"""Per-connection channel subscriptions (postgres_changes subset)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from routes.realtime.auth import JwtClaims


@dataclass
class PostgresSubscription:
    subscription_id: int
    event: str
    schema: str
    table: str
    filter: str | None = None


@dataclass
class ChannelSession:
    topic: str
    join_ref: str
    claims: JwtClaims
    postgres_changes: list[PostgresSubscription] = field(default_factory=list)


def parse_postgres_changes(config: dict[str, Any]) -> list[PostgresSubscription]:
    raw = config.get("postgres_changes")
    if not isinstance(raw, list):
        return []
    out: list[PostgresSubscription] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        out.append(
            PostgresSubscription(
                subscription_id=100_000 + idx,
                event=str(item.get("event") or "*").upper(),
                schema=str(item.get("schema") or "public"),
                table=str(item.get("table") or ""),
                filter=str(item["filter"]) if item.get("filter") else None,
            )
        )
    return out


def event_matches(sub: PostgresSubscription, schema: str, table: str, op: str) -> bool:
    if sub.schema != "*" and sub.schema != schema:
        return False
    if sub.table != "*" and sub.table != table:
        return False
    op_u = op.upper()
    if sub.event == "*":
        return True
    if sub.event == "INSERT" and op_u == "INSERT":
        return True
    if sub.event == "UPDATE" and op_u == "UPDATE":
        return True
    if sub.event == "DELETE" and op_u == "DELETE":
        return True
    return sub.event == op_u
