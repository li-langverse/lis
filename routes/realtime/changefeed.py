"""Changefeed source: native lidb poll with JSONL fallback."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from routes.realtime.lidb_native import (
    LidbChangefeedNative,
    discover_lidb_changefeed_lib,
    native_poll_enabled,
    parse_native_json_line,
    poll_lines_subprocess,
    try_open_native,
    use_subprocess_poll,
)


@dataclass
class WalChangefeedEvent:
    lsn: int
    schema: str
    table: str
    op: str  # insert | update | delete
    record: dict[str, Any]
    old_record: dict[str, Any] = field(default_factory=dict)


Listener = Callable[[WalChangefeedEvent], None]


class ChangefeedSource:
    """Poll lidb `lidb_changefeed_poll` when available; else JSONL stub files."""

    def __init__(self, data_dir: Path | None = None) -> None:
        root = data_dir or Path(os.environ.get("LI_DATA_DIR", Path.home() / ".local/share/lis/data"))
        self._data_dir = Path(root)
        self._wal_path = self._data_dir / "wal.changefeed.jsonl"
        self._mock_path = self._data_dir / "wal.changefeed.mock.jsonl"
        self._listeners: list[Listener] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._offsets: dict[str, int] = {}
        self._native: LidbChangefeedNative | None = None
        self._native_mode = "off"
        if native_poll_enabled():
            if use_subprocess_poll() and discover_lidb_changefeed_lib() is not None:
                self._native_mode = "subprocess"
            else:
                self._native = try_open_native(self._data_dir)
                if self._native is not None:
                    self._native_mode = "ctypes"

    @property
    def native_mode(self) -> str:
        """`ctypes`, `subprocess`, or `off` (JSONL-only)."""
        return self._native_mode

    def wal_stub_path(self) -> Path:
        return self._wal_path

    def start_polling(self, interval_sec: float = 0.05) -> None:
        if self._thread and self._thread.is_alive():
            return

        def _loop() -> None:
            while not self._stop.is_set():
                for event in self.poll_once():
                    self._dispatch(event)
                time.sleep(interval_sec)

        self._thread = threading.Thread(target=_loop, name="lis-changefeed-poll", daemon=True)
        self._thread.start()

    def stop_polling(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._stop.clear()
        if self._native is not None:
            self._native.close()
            self._native = None

    def subscribe(self, listener: Listener) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def _unsub() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return _unsub

    def push_mock(
        self,
        *,
        schema: str = "public",
        table: str,
        op: str = "insert",
        record: dict[str, Any],
        old_record: dict[str, Any] | None = None,
        lsn: int | None = None,
    ) -> WalChangefeedEvent:
        event = WalChangefeedEvent(
            lsn=lsn or int(time.time() * 1000),
            schema=schema,
            table=table,
            op=op,
            record=record,
            old_record=old_record or {},
        )
        line = json.dumps(
            {
                "lsn": event.lsn,
                "schema": event.schema,
                "table": event.table,
                "op": event.op,
                "record": event.record,
                "old_record": event.old_record,
            },
            separators=(",", ":"),
        )
        self._mock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._mock_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
        self._dispatch(event)
        return event

    def native_insert(self, table: str) -> int:
        """Emit a native WAL insert when lidb changefeed is linked (tests / liorm wire)."""
        if self._native is None or not self._native.available:
            return 0
        return self._native.native_insert(table)

    def poll_once(self) -> list[WalChangefeedEvent]:
        events: list[WalChangefeedEvent] = []
        events.extend(self._poll_native())
        for path in (self._wal_path, self._mock_path):
            if not path.is_file():
                continue
            events.extend(self._read_new_lines(path))
        return events

    def _poll_native(self) -> list[WalChangefeedEvent]:
        if self._native_mode == "off":
            return []
        lines: list[str] = []
        if self._native_mode == "ctypes" and self._native is not None:
            lines = self._native.poll_lines()
        elif self._native_mode == "subprocess":
            lines = poll_lines_subprocess(self._data_dir)
        out: list[WalChangefeedEvent] = []
        for line in lines:
            parsed = self._parse_native_line(line)
            if parsed:
                out.append(parsed)
        return out

    def _read_new_lines(self, path: Path) -> list[WalChangefeedEvent]:
        out: list[WalChangefeedEvent] = []
        key = str(path)
        try:
            with path.open("r", encoding="utf-8") as fh:
                fh.seek(self._offsets.get(key, 0))
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    parsed = self._parse_line(line)
                    if parsed:
                        out.append(parsed)
                self._offsets[key] = fh.tell()
        except OSError:
            return out
        return out

    @staticmethod
    def _parse_native_line(line: str) -> WalChangefeedEvent | None:
        data = parse_native_json_line(line)
        if not data:
            return None
        op = str(data.get("op") or "insert").lower()
        record = data.get("record")
        if not isinstance(record, dict):
            payload_bytes = int(data.get("payload_bytes") or 0)
            record = {"payload_bytes": payload_bytes} if payload_bytes else {}
        old = data.get("old_record")
        if not isinstance(old, dict):
            old = {}
        return WalChangefeedEvent(
            lsn=int(data.get("lsn") or 0),
            schema=str(data.get("schema") or "public"),
            table=str(data.get("table") or ""),
            op=op,
            record=record,
            old_record=old,
        )

    @staticmethod
    def _parse_line(line: str) -> WalChangefeedEvent | None:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        table = str(data.get("table") or "")
        if not table:
            return None
        op = str(data.get("op") or "insert").lower()
        record = data.get("record")
        if not isinstance(record, dict):
            record = data.get("payload")
        if not isinstance(record, dict):
            record = {"payload": data.get("payload")}
        old = data.get("old_record")
        if not isinstance(old, dict):
            old = {}
        return WalChangefeedEvent(
            lsn=int(data.get("lsn") or 0),
            schema=str(data.get("schema") or "public"),
            table=table,
            op=op,
            record=record,
            old_record=old,
        )

    def _dispatch(self, event: WalChangefeedEvent) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            listener(event)

    def iter_pending(self) -> Iterator[WalChangefeedEvent]:
        yield from self.poll_once()
