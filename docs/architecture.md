# Architecture

## HTTP gateway (li-httpd)

```mermaid
flowchart TB
  httpd[li-httpd CLI]
  http[li-http parser proxy censor]
  net[li-net reactor]
  log[li-log]
  tls[li-tls]
  crypto[li-crypto]
  rng[li-rng]
  httpd --> http
  httpd --> log
  http --> net
  http --> tls
  tls --> crypto
  crypto --> rng
```

## Li data platform (PH-DB)

**lis** supervises a lean Supabase-shaped bundle: default profile **`registry-min`**. **lidb** (Postgres-shaped engine) runs **in-process** inside the same `lis` binary — no separate database container.

```mermaid
flowchart TB
  subgraph lis_supervisor["lis supervisor (single binary)"]
    cli["lis db start|stop|status|migrate"]
    prof["profiles/registry-min.toml"]
    api["Registry REST :54321"]
    pool["li-pool stub"]
    obs["li-log stub"]
    cli --> prof
    cli --> embed
    api --> embed
    pool --> embed
    obs --> embed
    subgraph embed["lidb in-process (WP1)"]
      wal["WAL + heap"]
      sql["SQL subset"]
      mig["migrations/001_registry"]
      orm["liorm / liq (WP2)"]
      wal --> sql
      mig --> sql
      orm --> sql
    end
  end
  lip["lip registry clients"]
  agents["li-cursor-agents control plane"]
  lip --> api
  agents --> api
  agents --> embed
```

| Port | Listener | Notes |
|------|----------|-------|
| 54321 | PostgREST-shaped registry API | lip OpenAPI (WP4) |
| 54322 | Postgres wire (lidb) | SQL + migrations |

**Packaging:** Core verticals ship in **lidb + lis**. Optional splits (e.g. `li-auth-oauth`) are documented in [profiles/registry-min.toml](../profiles/registry-min.toml).

**PH-DB-3:** CLI + profile + diagram — `lidb` dependency stubbed until WP1.

**PH-DB-4 (this repo):** `routes/registry/` REST handlers + `openapi/registry-v1.yaml` + mock `liorm` store; real `execute(plan_id)` when WP1–WP2 link.

## Packages

See [packages/](packages/) for function-level catalogs. Dependencies use `path` in `li.toml` until published separately.
