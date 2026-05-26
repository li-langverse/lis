"""PH-DB-3 / WP-I lis db supervisor tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

LIS_ROOT = Path(__file__).resolve().parents[1]
LIDB_REPO = Path(os.environ.get("LIDB_REPO", LIS_ROOT.parent / "lidb"))


def _lidb_available() -> bool:
    return (LIDB_REPO / "liorm").is_dir() and shutil.which("cmake") is not None


@pytest.fixture
def data_dir():
    tmp = tempfile.mkdtemp(prefix="lis-pytest-db-")
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


def test_profile_loads_registry_min():
    from lis.db.profile import load_profile

    prof = load_profile(LIS_ROOT / "profiles" / "registry-min.toml")
    assert prof.name == "registry-min"
    assert prof.tcp_port == 0
    assert prof.hosting is not None
    assert prof.hosting.service == "registry"
    assert any(p.name == "agent_runs.recent" for p in prof.plans)


def test_profile_loads_control_plane_min():
    from lis.db.profile import load_profile

    prof = load_profile(LIS_ROOT / "profiles" / "control-plane-min.toml")
    assert prof.name == "control-plane-min"
    assert "control-plane" in prof.verticals
    assert prof.hosting is not None
    assert prof.hosting.service == "control-plane"
    names = {p.name for p in prof.plans}
    assert "control_plane_state.latest" in names
    assert "agent_runs.recent" in names


def test_tcp_wire_stub_profile_documents_not_implemented():
    from lis.db.profile import load_profile

    prof = load_profile(LIS_ROOT / "profiles" / "tcp-wire-stub.toml")
    assert prof.tcp_port == 54321
    assert prof.embed_mode == "tcp_loopback"


@pytest.mark.skipif(not _lidb_available(), reason="sibling lidb + cmake required")
def test_supervisor_start_status_stop(data_dir, monkeypatch):
    monkeypatch.setenv("LIDB_REPO", str(LIDB_REPO))
    monkeypatch.setenv("LI_DATA_DIR", str(data_dir))
    from lis.db.supervisor import DbSupervisor

    sup = DbSupervisor(data_dir=data_dir, profile_name="registry-min")
    state = sup.start()
    assert state["ready"] is True
    assert state["protocol_version"] == "1"
    assert state["live"] is True
    assert state["checks"]["catalog"] == "ok"
    assert state["plans_registered"] >= 1

    status = sup.status()
    assert status["ready"] is True
    assert status["migrated"] is True
    assert status["checks"]["engine"] == "ok"

    sup.stop()
    assert not (data_dir / ".lis" / "db-state.json").exists()


@pytest.mark.skipif(not _lidb_available(), reason="sibling lidb + cmake required")
def test_control_plane_min_supervisor(data_dir, monkeypatch):
    monkeypatch.setenv("LIDB_REPO", str(LIDB_REPO))
    monkeypatch.setenv("LI_DATA_DIR", str(data_dir))
    from lis.db.supervisor import DbSupervisor

    sup = DbSupervisor(data_dir=data_dir, profile_name="control-plane-min")
    state = sup.start()
    assert state["ready"] is True
    assert state["service"] == "control-plane"
    assert state["plans_registered"] >= 5
    assert "control-plane" in state["verticals"]


@pytest.mark.skipif(not _lidb_available(), reason="sibling lidb + cmake required")
def test_cli_smoke_subprocess(data_dir, monkeypatch):
    monkeypatch.setenv("LIDB_REPO", str(LIDB_REPO))
    env = os.environ.copy()
    env["LI_DATA_DIR"] = str(data_dir)
    env["LI_PROFILE"] = "registry-min"
    env["PYTHONPATH"] = str(LIS_ROOT)
    for cmd in (
        [sys.executable, "-m", "lis.cli", "db", "start", "--json"],
        [sys.executable, "-m", "lis.cli", "db", "status", "--json"],
        [sys.executable, "-m", "lis.cli", "db", "stop"],
    ):
        proc = subprocess.run(cmd, cwd=LIS_ROOT, env=env, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = json.loads(
        subprocess.run(
            [sys.executable, "-m", "lis.cli", "db", "status", "--json"],
            cwd=LIS_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    assert payload["migrated"] is True
    assert payload.get("protocol_version") == "1"
