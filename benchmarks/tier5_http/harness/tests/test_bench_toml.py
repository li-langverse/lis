"""Load harness: validate bench scenario TOML (verify-only until li-httpd ships)."""
import subprocess
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"


def test_static_small_bench():
    p = ROOT / "scenarios/static_small/bench.toml"
    assert p.is_file()
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    assert "server" in data


def test_defaults_has_fixtures():
    data = tomllib.loads((ROOT / "defaults.toml").read_text(encoding="utf-8"))
    assert "fixtures" in data


def test_verify_http_ci_profile():
    env = {**__import__("os").environ, "PYTHONPATH": str(HARNESS)}
    r = subprocess.run(
        [sys.executable, str(HARNESS / "verify_http.py"), "--all", "--profile", "ci"],
        cwd=HARNESS,
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr


def test_exploit_http_pr_profile():
    env = {**__import__("os").environ, "PYTHONPATH": str(HARNESS)}
    r = subprocess.run(
        [sys.executable, str(HARNESS / "exploit_http.py"), "--profile", "pr"],
        cwd=HARNESS,
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
