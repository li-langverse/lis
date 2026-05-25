"""ctypes + subprocess helpers for lidb `lidb_changefeed_poll` (requires lidb #11)."""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class LidbChangefeedNative:
    """In-process poll via liblidb_changefeed."""

    def __init__(self, lib_path: Path, data_dir: Path) -> None:
        self._lib_path = lib_path
        self._data_dir = data_dir
        self._lib: ctypes.CDLL | None = None
        self._handle: ctypes.c_void_p | None = None
        self._bind()
        self._handle = self._open(data_dir)

    @property
    def available(self) -> bool:
        return self._handle is not None

    def close(self) -> None:
        if self._lib is not None and self._handle is not None:
            self._lib.lidb_changefeed_close(self._handle)
        self._handle = None

    def subscribe(self, table: str) -> int:
        if self._lib is None or self._handle is None:
            return 0
        raw = table.encode("utf-8")
        return int(self._lib.lidb_changefeed_subscribe(self._handle, raw))

    def native_insert(self, table: str) -> int:
        if self._lib is None or self._handle is None:
            return 0
        raw = table.encode("utf-8")
        return int(self._lib.lidb_changefeed_native_insert(self._handle, raw))

    def poll_lines(self) -> list[str]:
        if self._lib is None or self._handle is None:
            return []
        buf = ctypes.create_string_buffer(8192)
        out_len = ctypes.c_size_t(0)
        lines: list[str] = []
        while True:
            rc = int(self._lib.lidb_changefeed_poll(self._handle, buf, len(buf) - 1, ctypes.byref(out_len)))
            if rc == 0:
                break
            if rc < 0:
                break
            n = int(out_len.value)
            if n <= 0:
                break
            lines.append(buf.raw[:n].decode("utf-8", errors="replace"))
        return lines

    def _bind(self) -> None:
        lib = ctypes.CDLL(str(self._lib_path))
        lib.lidb_changefeed_open.argtypes = [ctypes.c_char_p]
        lib.lidb_changefeed_open.restype = ctypes.c_void_p
        lib.lidb_changefeed_close.argtypes = [ctypes.c_void_p]
        lib.lidb_changefeed_close.restype = None
        lib.lidb_changefeed_subscribe.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.lidb_changefeed_subscribe.restype = ctypes.c_uint64
        lib.lidb_changefeed_native_insert.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.lidb_changefeed_native_insert.restype = ctypes.c_uint64
        lib.lidb_changefeed_poll.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        lib.lidb_changefeed_poll.restype = ctypes.c_int
        self._lib = lib

    def _open(self, data_dir: Path) -> ctypes.c_void_p | None:
        if self._lib is None:
            return None
        handle = self._lib.lidb_changefeed_open(str(data_dir).encode("utf-8"))
        return handle if handle else None


def discover_lidb_changefeed_lib() -> Path | None:
    """Resolve liblidb_changefeed (.dylib / .so) from env or sibling lidb build."""
    explicit = os.environ.get("LIDB_CHANGEFEED_LIB", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return path

    root = Path(__file__).resolve().parents[2]
    names = ("liblidb_changefeed.dylib", "liblidb_changefeed.so", "liblidb_changefeed.dll")
    search_roots = [
        root / "../lidb",
        Path(os.environ.get("LIDB_ROOT", "")).expanduser() if os.environ.get("LIDB_ROOT") else None,
    ]
    for base in search_roots:
        if base is None or not base.is_dir():
            continue
        build = os.environ.get("LIDB_BUILD_DIR", "").strip()
        if build:
            dirs = [Path(build)]
        else:
            dirs = sorted((base / "build").glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for build_dir in dirs:
            for name in names:
                candidate = build_dir / name
                if candidate.is_file():
                    return candidate
    return None


def native_poll_enabled() -> bool:
    """True unless operator forces JSONL-only (`LI_CHANGEFEED_NATIVE=0`)."""
    return os.environ.get("LI_CHANGEFEED_NATIVE", "1").strip().lower() not in ("0", "false", "no")


def use_subprocess_poll() -> bool:
    return os.environ.get("LI_CHANGEFEED_NATIVE", "").strip().lower() == "subprocess"


def try_open_native(data_dir: Path) -> LidbChangefeedNative | None:
    if not native_poll_enabled():
        return None
    lib = discover_lidb_changefeed_lib()
    if lib is None:
        return None
    try:
        handle = LidbChangefeedNative(lib, data_dir)
    except OSError:
        return None
    if not handle.available:
        handle.close()
        return None
    handle.subscribe("*")
    return handle


def poll_lines_subprocess(data_dir: Path) -> list[str]:
    """One-shot poll via helper script (fallback when in-process ctypes fails)."""
    script = Path(__file__).resolve().parents[2] / "scripts" / "lidb_changefeed_poll_once.py"
    if not script.is_file():
        return []
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(script.parent.parent))
    proc = subprocess.run(
        [sys.executable, str(script), str(data_dir)],
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        return []
    lines: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            lines.append(line)
    return lines


def parse_native_json_line(line: str) -> dict[str, Any] | None:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    table = str(data.get("table") or "")
    if not table:
        return None
    return data
