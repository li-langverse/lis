#!/usr/bin/env python3
"""WebSocket Realtime server — Phoenix v1.0.0 + postgres_changes (WP-N3)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from routes.realtime.auth import (  # noqa: E402
    authorize_join,
    claims_from_access_token,
    rls_allows_row,
    row_from_changefeed_record,
)
from routes.realtime.changefeed import ChangefeedSource, WalChangefeedEvent  # noqa: E402
from routes.realtime.protocol import (  # noqa: E402
    PhoenixMessage,
    decode_message,
    encode_message,
    postgres_changes_payload,
)
from routes.realtime.session import ChannelSession, event_matches, parse_postgres_changes  # noqa: E402

try:
    import websockets
    from websockets.asyncio.server import serve
    from websockets.server import WebSocketServerProtocol
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "lis realtime requires the 'websockets' package: python3 -m pip install websockets"
    ) from exc


def _wal_op_to_pg(op: str) -> str:
    mapping = {"insert": "INSERT", "update": "UPDATE", "delete": "DELETE"}
    return mapping.get(op.lower(), op.upper())


class RealtimeServer:
    def __init__(self, changefeed: ChangefeedSource, loop: asyncio.AbstractEventLoop) -> None:
        self.changefeed = changefeed
        self._loop = loop
        self._event_queue: asyncio.Queue[WalChangefeedEvent] = asyncio.Queue()
        self._channels: dict[int, dict[str, ChannelSession]] = {}
        self._ws_index: dict[int, dict[str, ChannelSession]] = {}
        self._require_auth = os.environ.get("LI_REALTIME_REQUIRE_AUTH", "0") == "1"
        changefeed.subscribe(self._enqueue_changefeed_event)

    def _enqueue_changefeed_event(self, event: WalChangefeedEvent) -> None:
        self._loop.call_soon_threadsafe(self._event_queue.put_nowait, event)

    async def _drain_changefeed(self) -> None:
        while True:
            event = await self._event_queue.get()
            await self._broadcast_event(event)

    async def _broadcast_event(self, event: WalChangefeedEvent) -> None:
        pg_type = _wal_op_to_pg(event.op)
        for ws_id, topics in list(self._ws_index.items()):
            ws = _active_ws.get(ws_id)
            if ws is None:
                continue
            for topic, session in topics.items():
                for sub in session.postgres_changes:
                    if not event_matches(sub, event.schema, event.table, pg_type):
                        continue
                    row = row_from_changefeed_record(event.record)
                    if not rls_allows_row(session.claims, row):
                        continue
                    payload = postgres_changes_payload(
                        subscription_id=sub.subscription_id,
                        schema=event.schema,
                        table=event.table,
                        event_type=pg_type,
                        record=event.record,
                        old_record=event.old_record,
                    )
                    await ws.send(
                        encode_message(topic, "postgres_changes", payload, join_ref=session.join_ref)
                    )

    async def handler(self, ws: WebSocketServerProtocol) -> None:
        ws_id = id(ws)
        _active_ws[ws_id] = ws
        query_claims = _claims_from_query(ws.request.path if ws.request else "/")
        self._channels[ws_id] = {}
        try:
            async for raw in ws:
                if not isinstance(raw, str):
                    continue
                try:
                    msg = decode_message(raw)
                except (json.JSONDecodeError, ValueError):
                    await ws.send(
                        encode_message(
                            "phoenix",
                            "phx_error",
                            {"reason": "invalid_message"},
                            ref="0",
                        )
                    )
                    continue
                await self._handle_message(ws, ws_id, msg, query_claims)
        finally:
            _active_ws.pop(ws_id, None)
            self._channels.pop(ws_id, None)
            self._ws_index.pop(ws_id, None)

    async def _handle_message(
        self,
        ws: WebSocketServerProtocol,
        ws_id: int,
        msg: PhoenixMessage,
        query_claims: Any,
    ) -> None:
        if msg.event == "heartbeat":
            await ws.send(
                encode_message("phoenix", "phx_reply", {"status": "ok", "response": {}}, ref=msg.ref)
            )
            return

        if msg.event == "phx_join":
            await self._handle_join(ws, ws_id, msg, query_claims)
            return

        if msg.event == "phx_leave":
            self._channels.get(ws_id, {}).pop(msg.topic, None)
            self._ws_index.get(ws_id, {}).pop(msg.topic, None)
            if msg.ref and msg.join_ref:
                await ws.send(
                    encode_message(
                        msg.topic,
                        "phx_reply",
                        {"status": "ok", "response": {}},
                        ref=msg.ref,
                        join_ref=msg.join_ref,
                    )
                )
            return

    async def _handle_join(
        self,
        ws: WebSocketServerProtocol,
        ws_id: int,
        msg: PhoenixMessage,
        query_claims: Any,
    ) -> None:
        join_ref = msg.join_ref or msg.ref or "1"
        config = msg.payload.get("config") if isinstance(msg.payload.get("config"), dict) else {}
        claims = _resolve_claims(msg.payload, query_claims)
        err = authorize_join(claims, require_auth=self._require_auth)
        if err:
            await ws.send(
                encode_message(
                    msg.topic,
                    "phx_reply",
                    {"status": "error", "response": {"reason": err}},
                    ref=msg.ref,
                    join_ref=join_ref,
                )
            )
            return

        subs = parse_postgres_changes(config)
        session = ChannelSession(topic=msg.topic, join_ref=join_ref, claims=claims, postgres_changes=subs)
        self._channels.setdefault(ws_id, {})[msg.topic] = session
        self._ws_index.setdefault(ws_id, {})[msg.topic] = session

        pg_response = [
            {
                "id": s.subscription_id,
                "event": s.event,
                "schema": s.schema,
                "table": s.table,
            }
            for s in subs
        ]
        await ws.send(
            encode_message(
                msg.topic,
                "phx_reply",
                {"status": "ok", "response": {"postgres_changes": pg_response}},
                ref=msg.ref,
                join_ref=join_ref,
            )
        )
        if subs:
            await ws.send(
                encode_message(
                    msg.topic,
                    "system",
                    {
                        "message": "Subscribed to PostgreSQL",
                        "status": "ok",
                        "extension": "postgres_changes",
                        "channel": msg.topic.split(":")[-1] if ":" in msg.topic else "main",
                    },
                    join_ref=join_ref,
                )
            )


_active_ws: dict[int, WebSocketServerProtocol] = {}


def _resolve_claims(payload: dict[str, Any], query_claims: Any) -> Any:
    token = payload.get("access_token")
    if token:
        return claims_from_access_token(str(token))
    return query_claims


def _claims_from_query(path: str) -> Any:
    parsed = urlparse(path)
    qs = parse_qs(parsed.query)
    apikey = (qs.get("apikey") or [None])[0]
    return claims_from_access_token(apikey)


async def _run_server(host: str, port: int, changefeed: ChangefeedSource) -> None:
    loop = asyncio.get_running_loop()
    app = RealtimeServer(changefeed, loop)
    changefeed.start_polling()
    path = os.environ.get("LI_REALTIME_WS_PATH", "/realtime/v1/websocket")
    print(f"lis realtime WS: ws://{host}:{port}{path} (Phoenix v1.0.0)", flush=True)

    async def connection(ws: WebSocketServerProtocol) -> None:
        await app.handler(ws)

    drain_task = asyncio.create_task(app._drain_changefeed())
    try:
        async with serve(connection, host, port, ping_interval=20, ping_timeout=20):
            await asyncio.Future()
    finally:
        drain_task.cancel()


def serve_forever(host: str | None = None, port: int | None = None) -> None:
    h = host or os.environ.get("LI_REALTIME_HOST", "127.0.0.1")
    p = port or int(os.environ.get("LI_REALTIME_PORT", "54323"))
    data_dir = Path(os.environ.get("LI_DATA_DIR", Path.home() / ".local/share/lis/data"))
    feed = ChangefeedSource(data_dir)
    try:
        asyncio.run(_run_server(h, p, feed))
    finally:
        feed.stop_polling()


def main() -> None:
    parser = argparse.ArgumentParser(description="lis Supabase-shaped Realtime WebSocket")
    parser.add_argument("--host", default=os.environ.get("LI_REALTIME_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LI_REALTIME_PORT", "54323")),
    )
    args = parser.parse_args()
    serve_forever(args.host, args.port)


if __name__ == "__main__":
    main()
