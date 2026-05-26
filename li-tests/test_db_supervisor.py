"""PH-DB-3 lis db supervisor tests."""

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
    assert any(p.name == "agent_runs.recent" for p in prof.plans)


@pytest.mark.skipif(not _lidb_available(), reason="sibling lidb + cmake required")
def test_supervisor_start_status_stop(data_dir, monkeypatch):
    monkeypatch.setenv("LIDB_REPO", str(LIDB_REPO))
    monkeypatch.setenv("LI_DATA_DIR", str(data_dir))
    from lis.db.supervisor import DbSupervisor

    sup = DbSupervisor(data_dir=data_dir, profile_name="registry-min")
    state = sup.start()
    assert state["ready"] is True
    assert state["plans_registered"] >= 1

    status = sup.status()
    assert status["ready"] is True
    assert status["migrated"] is True

    sup.stop()
    assert not (data_dir / ".lis" / "db-state.json").exists()


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
