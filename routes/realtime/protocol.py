"""Phoenix Channels v1.0.0 JSON framing (Supabase Realtime compatible subset)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PhoenixMessage:
    topic: str
    event: str
    payload: dict[str, Any]
    ref: str | None = None
    join_ref: str | None = None


def decode_message(raw: str) -> PhoenixMessage:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object for protocol v1.0.0")
    return PhoenixMessage(
        topic=str(data.get("topic", "")),
        event=str(data.get("event", "")),
        payload=data.get("payload") if isinstance(data.get("payload"), dict) else {},
        ref=_str_or_none(data.get("ref")),
        join_ref=_str_or_none(data.get("join_ref")),
    )


def encode_message(
    topic: str,
    event: str,
    payload: dict[str, Any],
    *,
    ref: str | None = None,
    join_ref: str | None = None,
) -> str:
    body: dict[str, Any] = {"topic": topic, "event": event, "payload": payload}
    if ref is not None:
        body["ref"] = ref
    if join_ref is not None:
        body["join_ref"] = join_ref
    return json.dumps(body, separators=(",", ":"))


def postgres_changes_payload(
    *,
    subscription_id: int,
    schema: str,
    table: str,
    event_type: str,
    record: dict[str, Any],
    old_record: dict[str, Any] | None = None,
    commit_timestamp: str | None = None,
) -> dict[str, Any]:
    return {
        "ids": [subscription_id],
        "data": {
            "schema": schema,
            "table": table,
            "commit_timestamp": commit_timestamp or _utc_now_iso(),
            "type": event_type,
            "columns": [{"name": k, "type": "text"} for k in record],
            "record": record,
            "old_record": old_record or {},
            "errors": None,
        },
    }


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
