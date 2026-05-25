# Registry REST routes (PH-DB-4)

PostgREST-shaped handlers for **lip** registry OpenAPI v1. Default store uses **lidb** `liorm.execute` via `store.py` / `liorm_store.py`; set `LI_REGISTRY_MOCK=1` for `liorm_mock.py`.

| Method | Path | Handler |
|--------|------|---------|
| `GET` | `/v1/packages` | `handlers.handle_request` → `get_registry_store().list_packages` |
| `GET` | `/v1/packages/{name}/{version}` | `get_package_version` |
| `POST` | `/v1/packages/{name}/versions` | `publish` (bearer required) |
| `POST` | `/v1/packages/{name}/{version}/yank` | `yank` (bearer required) |
| `GET` | `/v1/openapi.yaml` | Serves [openapi/registry-v1.yaml](../../openapi/registry-v1.yaml) |
| `GET` | `/health` | Liveness |

## Run

```bash
export LI_DATA_DIR="${LI_DATA_DIR:-./.li-data}"
export LI_API_PORT=54321
python3 routes/registry/server.py
```

Or via supervisor: `lis db start` (starts registry listener in background when `LI_REGISTRY_API=1`, default on).

## Contract

- OpenAPI canonical in **lip**: `registry/api/openapi-stub.yaml`
- **lis** copy: `openapi/registry-v1.yaml` (local server URL uses API port **54321**)
- DDL: `lidb/migrations/001_registry.sql` — mock store mirrors `package_versions` + yank flags

## liorm wiring

- **Default:** `LIDB_ROOT` (sibling `../lidb` or env) must contain `liorm/execute.py` (WP2). Plans in `plans.py` match `[modules.liorm_plans]` in `profiles/registry-min.toml`.
- **Mock:** `LI_REGISTRY_MOCK=1` skips liorm and uses `liorm_mock.py`.
- **Subprocess:** `LI_LIDB_LIORM_SUBPROCESS=1` runs `execute` in a child interpreter.
- **WP1:** When the embedded engine returns rows, drop JSON backing in `liorm_store.py` and map `ExecuteResult.rows` directly.
