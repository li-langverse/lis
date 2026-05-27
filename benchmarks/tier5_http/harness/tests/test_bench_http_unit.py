"""Unit tests for bench_http helpers (no nginx required)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "harness"))

import bench_http as bh  # noqa: E402


def test_parse_wrk_rps():
    sample = """
Running 2s test @ http://127.0.0.1:9/
  2 threads and 4 connections
  Thread Stats   Avg      Stdev     Max   +/- Stdev
    Latency   123.45us   45.67us   1.23ms   89.01%
    Req/Sec    12.34k     1.23k    15.67k    78.90%
  123456 requests in 2.01s, 45.67MB read
Requests/sec:  61415.23
Transfer/sec:     22.72MB
"""
    assert abs(bh.parse_wrk_rps(sample) - 61415.23) < 0.01


def test_keepalive_scenario_loads():
    cfg = bh.merge_scenario("keepalive_pipelining")
    assert cfg.get("load", {}).get("pipeline") == 8


def test_suite_ci_includes_keepalive():
    names, timing = bh.load_suite("ci")
    assert "keepalive_pipelining" in names
    assert timing is False
