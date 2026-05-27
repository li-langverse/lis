# Release notes: 2026-05-25 — tier5-http-csv-full

**Status:** Ready for review  
**Repo:** li-langverse/lis  
**PR:** (feat/tier5-csv-full)  
**PH / REQ:** PH-H, fill-all benchmarks WP6  
**Author:** agent

---

## Summary (one sentence)

Replaces the stub `bench_http.py` with the multi-oracle tier-5 harness (nginx/wrk + optional `LI_HTTPD_BIN`) and commits a measured `benchmarks/results/latest.csv` for dashboard ingest.

## Agent continuation (required)

1. **Read:** `benchmarks/tier5_http/README.md`, `benchmarks/results/latest.csv`, `scripts/run-tier5-http-bench.sh`.
2. **Run:** `LI_HTTPD_BIN=../lic/build/li-httpd BENCH_HTTP_PROFILE=nightly ./scripts/run-tier5-http-bench.sh` on **Linux** (after `./scripts/build-li-httpd.sh` in **lic**) to refresh `lang=li` RPS rows; macOS arm64 lacks epoll-linked `li-httpd`.
3. **Then:** sync `benchmarks` vendor via `LIS_ROOT=../lis ./scripts/sync-lis-tier5-vendor.sh`; WP7 full suite ingest.
4. **Blocked on:** Human merge; no new trusted axioms.

## Changed (specific)

| Area | What | Evidence |
|------|------|----------|
| Harness | Full `bench_http.py`, `http_oracles.py`, scenarios (LB/proxy/TLS/rate-limit), exploits | `benchmarks/tier5_http/harness/bench_http.py` (970 lines) |
| CSV | `benchmarks/results/latest.csv` — 29 rows, 11 `metric=rps` (nginx/node wrk on darwin) | local `./scripts/run-tier5-http-bench.sh` |
| Scripts | `run-tier5-http-bench.sh`, `verify-http.sh` uses `--no-bench` / `--csv` | `./scripts/verify-http.sh` |

## Not changed (scope fence)

- **lic** `packages/li-net-httpd` implementation — oracle binary only via `LI_HTTPD_BIN`.
- **benchmarks** `vendor/lis-tier5/` sync — follow-up after merge.
- Nginx submodule `third_party/nginx` — still optional audit-only.

## Breaking changes

None.

## Security

N/A — exploit TOML schema validation unchanged; runtime exploit oracles still require Linux services.

## Performance

| Benchmark | Lang | Metric | Value (sample) |
|-----------|------|--------|----------------|
| static_small | nginx | rps | ~17k req/s (arm64, quick 5s) |
| static_small | node | rps | ~7.6k req/s |

Reproduce: `BENCH_HTTP_ORACLES=nginx,node BENCH_HTTP_QUICK_SEC=5 ./scripts/run-tier5-http-bench.sh`

## Downstream

| Repo | Action |
|------|--------|
| benchmarks | `sync-lis-tier5-vendor.sh` after merge; ingest `benchmarks/results/latest.csv` |

## CHANGELOG entry (paste into Unreleased)

```markdown
### Changed
- **tier5_http:** multi-oracle `bench_http.py` + measured `benchmarks/results/latest.csv` (WP6 fill-all) — replaces verify-only stub rows.
```
