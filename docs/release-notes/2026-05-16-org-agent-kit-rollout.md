# Release notes: 2026-05-16 — org-agent-kit-rollout

**Status:** Released  
**Repo:** li-langverse/lis  
**PH / REQ:** httpd / meta-governance  
**Author:** agent

---

## Summary

Adopted roadmap agent-kit v1.1.0; updated `AGENTS.md` and PR template for release-notes + PR-only; added sync script and CHANGELOG scaffolding.

## Agent continuation

1. Read: [roadmap release-notes policy](https://github.com/li-langverse/roadmap/blob/main/docs/ecosystem/release-notes.md)
2. On merge-worthy PRs: update `CHANGELOG.md` + dated `docs/release-notes/` before `gh pr create`
3. After roadmap `agent-kit/` changes: `./scripts/sync-agent-kit.sh`
4. Blocked on: `lic` P0 (bytes, async) for full httpd product — unchanged

## Changed

| Area | What | Evidence |
|------|------|----------|
| Agent-kit | `.cursor/` v1.1.0 | `scripts/expected-agent-kit-version` |
| Docs | `AGENTS.md`, PR template | roadmap links; release-notes checklist |
| Tooling | `scripts/sync-agent-kit.sh` | installs from sibling `roadmap` |

## Not changed

- `lis` server, exploit harness, bench upload — **not** in this rollout
- Infra-only scope until `lic` P0 — unchanged

## Breaking changes

None.

## Security

N/A.

## Performance

N/A.

## Downstream

| Repo | Action |
|------|--------|
| benchmarks | Ingest from `lis` bench artifacts — unchanged workflow |

## CHANGELOG entry

```markdown
### Added
- Agent-kit v1.1.0 sync, release-notes scaffolding, PR template (org rollout)
```
