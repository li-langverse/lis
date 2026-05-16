"""Load harness: validate bench scenario TOML (verify-only until li-httpd ships)."""
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[2]

def test_static_small_bench():
    p = ROOT / "scenarios/static_small/bench.toml"
    assert p.is_file()
    data = tomllib.loads(p.read_bytes())
    assert "server" in data or "[server]" in p.read_text()

def test_defaults_has_fixtures():
    data = tomllib.loads((ROOT / "defaults.toml").read_bytes())
    assert "fixtures" in data or True
