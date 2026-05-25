# Release notes: 2026-05-25 — lis-lidb-changefeed-native

**Status:** Ready for review  
**Repo:** li-langverse/lis  
**PR:** (feat/lis-lidb-changefeed-native)  
**PH / REQ:** PH-DB, WP-N3  
**Author:** agent

---

## Summary (one sentence)

lis Realtime `ChangefeedSource` polls `lidb_changefeed_poll` via ctypes (JSONL fallback when `LI_CHANGEFEED_NATIVE=0` or the library is missing), pending merge of lidb native changefeed API.

## Agent continuation (required)

1. Read: `lidb/docs/changefeed.md`, `routes/realtime/lidb_native.py`, `docs/realtime.md`
2. Run: `tests/realtime-ws.test` with `LIDB_CHANGEFEED_LIB` pointing at built `liblidb_changefeed`; `lidb/scripts/changefeed_smoke.sh`
3. Then: merge **after** [lidb#11](https://github.com/li-langverse/lidb/pull/11) lands on `main`; wire liorm native INSERT to emit row-shaped `record` in changefeed JSON
4. Blocked on: **lidb PR #11** merge (do not merge this lis PR first)

## Changed (specific)

| Area | What | Evidence |
|------|------|----------|
| `routes/realtime/lidb_native.py` | ctypes `lidb_changefeed_*`, lib discovery, subprocess poll helper | `tests/realtime-ws.test` native section when lib present |
| `routes/realtime/changefeed.py` | Native poll before JSONL; `native_insert()`; `native_mode` | mock WS test unchanged |
| `scripts/lidb_changefeed_poll_once.py` | Subprocess drain for `LI_CHANGEFEED_NATIVE=subprocess` | manual |
| `tests/realtime-ws.test` | Optional native poll smoke | SKIP without lib |
| `docs/realtime.md` | Env table + #11 dependency | — |

## Not changed (scope fence)

- lidb C++ changefeed implementation — **lidb#11 only**
- liorm registry store SQL plans / row payloads in WAL heap
- Phoenix v2, broadcast, presence
- `lis db start` auto-build of lidb (operators build lidb separately)

## Breaking changes

None.

## Security

N/A — poll reads local `LI_DATA_DIR` only; same trust boundary as JSONL stub.

## Performance

N/A — 50 ms poll interval unchanged; native poll drains queue in-process (no per-line subprocess unless `LI_CHANGEFEED_NATIVE=subprocess`).

## Downstream

| Repo | Action |
|------|--------|
| lidb | Merge #11; publish/build `liblidb_changefeed` in CI |
| lis | Merge this PR after lidb #11 |

## CHANGELOG entry (paste into Unreleased)

- **WP-N3:** Native `lidb_changefeed_poll` in `ChangefeedSource` with `LI_CHANGEFEED_NATIVE=0` JSONL fallback; depends on lidb #11.
