# Release notes: 2026-05-25 — production-registry

**Status:** Ready for review  
**Repo:** li-langverse/lis  
**PR:** (feat/production-registry-docs)  
**PH / REQ:** PH-DB-4  
**Author:** agent

---

## Summary (one sentence)

Adds `docs/production-registry.md` host runbook with env template (no real secrets), `registry-min` bootstrap, and TLS via li-httpd guidance.

## Agent continuation (required)

1. Read: `docs/production-registry.md`, `profiles/registry-min.toml`
2. Run on host: `export LI_DATA_DIR=…; lis db migrate --profile registry-min; lis db start --profile registry-min`
3. Then: human wires DNS/TLS; operator `lip publish --registry https://<host>/v1`
4. Blocked on: org `LIP_REGISTRY_TOKEN` and production FQDN — human only

## Changed (specific)

| Area | What | Evidence |
|------|------|----------|
| Docs | `docs/production-registry.md` | new runbook |
| Docs | `docs/cli-db.md` link to production runbook | cross-link |

## Not changed (scope fence)

- `bin/lis` supervisor implementation — stub unchanged
- Realtime / stack-full production paths — documented as out of scope for registry-min

## Breaking changes

None.

## Security

N/A — template uses placeholders; no secrets in repo.

## Performance

N/A.

## Downstream

| Repo | Action |
|------|--------|
| lip | `validate-production-registry-url.sh` CI contract |

## CHANGELOG entry (paste into Unreleased)

- **PH-DB-4:** `docs/production-registry.md` production host runbook + env template.
