# Release notes: 2026-05-28 — staging-majico-httpd-bridge

**Status:** Ready for review  
**Repo:** li-langverse/lis  
**PR:** cursor/staging-majico-httpd-bridge-3861  
**PH / REQ:** PH-DB staging / httpd M1 bridge  
**Author:** agent

---

## Summary (one sentence)

Adds Majico staging Docker edge with li-httpd TOML validated and rendered to Caddy, plus `lis http` / `lis staging` CLI and `packages/lis-cli` for lip install.

## Agent continuation (required)

1. Read: `docs/staging-majico.md`, `profiles/httpd/majico-staging.toml`, `deploy/staging/.env.example`
2. Run: `./scripts/ci.sh` (includes `li-tests/run_httpd_caddy.sh`); on host `cp deploy/staging/.env.example deploy/staging/.env`, edit hosts, `lis staging up --with-supabase`
3. Then: replace Kong stub with official Supabase docker init; set `MAJICO_WEB_IMAGE` / `PULSE_WEB_IMAGE`; run Majico `npm run verify:api-db-local` against staging API URL
4. Blocked on: production ACME email, real anon/service keys, full Supabase compose — human/ops

## Changed (specific)

| Area | What | Evidence |
|------|------|----------|
| Scripts | `scripts/httpd_config.py` (`HttpdConfig`, `[[site]]`, upstream validation) | `python scripts/httpd_config.py …` |
| Scripts | `scripts/httpd_render_caddy.py`, `scripts/staging-up.sh`, `scripts/install-lis.sh` | `li-tests/run_httpd_caddy.sh` |
| CLI | `bin/lis` `http`, `staging` subcommands | `lis http validate profiles/httpd/majico-staging.toml` |
| Deploy | `deploy/staging/docker-compose*.yml`, `.env.example` | compose smoke |
| Profile | `profiles/httpd/majico-staging.toml` | multi-site api/app/pulse |
| Docs | `docs/staging-majico.md` | runbook |
| Package | `packages/lis-cli/` | lip git dep metadata |

## Not changed (scope fence)

- **li-httpd** Li binary in `lic` — Caddy remains the runtime edge
- **lidb** embedded engine — `lis db` stub unchanged
- Majico application code — only documented env wiring

## Breaking changes

None.

## Security

- `.env.example` uses placeholders only; no secrets committed
- Kong `kong.yml` is empty stub — not production-ready until Supabase init

## Performance

N/A — infra scaffold only.

## Downstream

| Repo | Action |
|------|--------|
| lip | `lip install` git deps; `packages/lis-cli` |
| majico.xyz | Point staging env at `api.staging.*`; use container images |
| lic | Replace Caddy with `li-httpd` when M1 binary ships on host |
