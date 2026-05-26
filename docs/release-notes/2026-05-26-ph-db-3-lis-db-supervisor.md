# PH-DB-3: lis db supervisor

**Branch:** `cursor/wp-b-ph-db-3-lis-db`  
**Phase:** PH-DB-3 (WP-B)

## Summary

Adds `lis db start|migrate|status|stop` wired to sibling **lidb** `lidb_embed` and `registry-min` profile (`profiles/registry-min.toml`). Integration smoke (`scripts/db-smoke.sh`) and CI checkout of **lidb** `main`.

## Commands

- `lis db start` — migrate, register liq plans, write `.lis/db-state.json`
- `lis db migrate` — idempotent migration apply
- `lis db status` — JSON health; exit 0 when ready
- `lis db stop` — clear supervisor state

## Dependencies

- **lidb** `main` @ `6d2632d` or later (`lidb_embed`, `001_registry.sql`, `liorm`/`liq`)
- **WP-A (soft):** remaining lidb pytest failures do not block supervisor smoke

## Verification

```bash
export LI_DATA_DIR=./.li-data LIDB_REPO=../lidb
pip install -e .
lis db start && lis db status
./scripts/db-smoke.sh
```
