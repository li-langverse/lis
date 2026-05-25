# Release notes: 2026-05-25 — ph-db-4-lidb-liorm-wire

**PR:** feat/ph-db-4-lidb-liorm-wire (stacks on feat/ph-db-4-registry-routes)  
**Phase:** PH-DB-4 gap #2

## Summary

Registry REST handlers default to **lidb** `liorm.execute` with plans registered from `profiles/registry-min.toml`; `LI_REGISTRY_MOCK=1` retains the JSON mock store.

## Agent continuation

1. **Read** — `routes/registry/store.py`, `liorm_store.py`, `plans.py`, `lidb_import.py`, `profiles/registry-min.toml` `[modules.liorm_plans]`.
2. **Run** — `LIDB_ROOT=../lidb ./tests/registry-api.test` (requires `lidb` `feat/ph-db-2-liorm-impl` or newer with `liorm/execute.py`).
3. **Next** — When WP1 engine returns rows, map `ExecuteResult.rows` in `liorm_store.py` and remove JSON backing.
4. **Blocked** — In-process lidb embed without sibling checkout; set `LIDB_ROOT` or `LI_REGISTRY_MOCK=1`.

## Changed

| Area | Paths | Evidence |
|------|-------|----------|
| Store factory | `routes/registry/store.py` | `get_registry_store()` |
| liorm bridge | `routes/registry/{liorm_store,plans,lidb_import}.py` | plan IDs `registry.*` |
| Handlers | `routes/registry/handlers.py` | `/health` reports `backend` |
| Tests | `tests/registry-api.test` | liorm + mock modes |
| Profile | `profiles/registry-min.toml` | `registry_store` module |

## Not changed

- **lidb** C++ engine / WAL (WP1) — execute still returns stub rows.
- **lip** publish client — separate PR.
- Bearer auth verification — still stub.

## Breaking

N/A — new env vars only: `LIDB_ROOT`, `LI_REGISTRY_MOCK`, `LI_LIDB_LIORM_SUBPROCESS`.

## Security

Uses liorm param binding (no verbatim values in SQL). Run `lidb/tests/security/run_all.sh` before dropping `LI_REGISTRY_MOCK` default in production.

## Performance

N/A — same JSON persistence until engine wired.

## Downstream

- **lidb** PR #4 (liorm): merge before relying on default liorm path in CI without `LI_REGISTRY_MOCK=1`.
