# Agent instructions (`lis` — li-httpd)

1. Read [roadmap: engineering-standards](https://github.com/li-langverse/roadmap/blob/main/docs/ecosystem/engineering-standards.md).
2. Read [roadmap: release-notes](https://github.com/li-langverse/roadmap/blob/main/docs/ecosystem/release-notes.md) — **write before PR**.
3. Read [docs/plan.md](docs/plan.md) and [docs/implementation-status.md](docs/implementation-status.md).
4. **PR-only** — branch + PR; do not self-merge.
5. **No hand-rolled packages** — use `lic` `./scripts/li-new-package` when scaffolding.
6. Run `./scripts/ci.sh` before claiming done.
7. `./scripts/sync-agent-kit.sh` after roadmap `agent-kit/` changes.

Skills: `write-li-release-notes`, `li-ecosystem-discipline`.

**Blocked:** `.li` server code until `lic` P0 (2e–2f, bytes, async) — see [httpd-prerequisites](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/httpd-prerequisites.md).
