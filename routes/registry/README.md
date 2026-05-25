# Registry REST routes (PH-DB-4)

PostgREST-shaped handlers for **lip** registry OpenAPI v1. Backed by `liorm_mock.py` until **lidb** + **liorm** link in-process (WP1–WP2).

| Method | Path | Handler |
|--------|------|---------|
| `GET` | `/v1/packages` | `handlers.handle_request` → `MockRegistryStore.list_packages` |
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

## WP swap

Replace `get_registry_store()` with liorm plan IDs, e.g. `registry.list_packages`, `registry.get_version`, registered at `lis db start` from `profiles/registry-min.toml` `[modules.liorm_plans]`.
