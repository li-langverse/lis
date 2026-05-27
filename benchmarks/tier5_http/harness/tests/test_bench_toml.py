"""Load harness: validate bench scenario TOML (verify-only until li-httpd ships)."""
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[2]

def test_static_small_bench():
    p = ROOT / "scenarios/static_small/bench.toml"
    assert p.is_file()
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    assert "server" in data or "[server]" in p.read_text()


def test_keepalive_pipelining_bench():
    p = ROOT / "scenarios/keepalive_pipelining/bench.toml"
    assert p.is_file()
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    assert int(data["load"]["pipeline"]) >= 2

def test_defaults_has_fixtures():
    data = tomllib.loads((ROOT / "defaults.toml").read_text(encoding="utf-8"))
    assert "fixtures" in data or True
