"""Changefeed source: poll lidb WAL JSONL stub until subscribe_wal() ships."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator


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
    """Poll `wal.changefeed.jsonl` or accept mock pushes (lis stub)."""

    def __init__(self, data_dir: Path | None = None) -> None:
        root = data_dir or Path(os.environ.get("LI_DATA_DIR", Path.home() / ".local/share/lis/data"))
        self._wal_path = Path(root) / "wal.changefeed.jsonl"
        self._mock_path = Path(root) / "wal.changefeed.mock.jsonl"
        self._listeners: list[Listener] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._offsets: dict[str, int] = {}

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
        self._dispatch(event)
        return event

    def poll_once(self) -> list[WalChangefeedEvent]:
        events: list[WalChangefeedEvent] = []
        for path in (self._wal_path, self._mock_path):
            if not path.is_file():
                continue
            events.extend(self._read_new_lines(path))
        return events

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
