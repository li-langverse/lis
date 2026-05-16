"""Infra tests — pass without li-httpd binary."""
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[3]

def test_defaults_toml():
    p = ROOT / "defaults.toml"
    assert p.is_file()
    tomllib.loads(p.read_bytes())

def test_suite_toml():
    p = ROOT / "suite.toml"
    assert p.is_file()
    tomllib.loads(p.read_bytes())

def test_exploit_dir():
    assert (ROOT / "exploits").is_dir()
    assert any((ROOT / "exploits").glob("*.toml"))
