# lip registry — agent-first design (2026-06-08)

## North star

**Any agent can publish, query, and audit packages with three inputs:**

```bash
LIP_REGISTRY_URL=https://lip.lilangverse.xyz/v1
LIP_REGISTRY_TOKEN=…   # or OIDC exchange / device flow once
LIP_PACKAGE=my-lib      # optional when declared in li.toml
```

No browser, no Host-header hacks, no NodePort bypass. Responses are JSON with stable `error` / `message` / `details` / `remediation` fields.

**Primary surface:** Cursor agents via **MCP server `lip-registry`** + **Cursor Automations** on tag/PR events.

**Also supported:** GitHub Actions (OIDC), autonomous bots (service tokens + audit API).

---

## Agent personas

| Persona | Runtime | Auth | Typical flow |
|---------|---------|------|--------------|
| **A. Cursor IDE / Cloud agent** | MCP tools + optional `lip --json` | `LIP_REGISTRY_TOKEN` or device login once | validate → put_blob → publish → list |
| **B. GitHub Actions** | `curl` / action | OIDC → short-lived publish JWT | on tag: build → validate → publish |
| **C. Autonomous bot** | HTTP + polling | Named service token (`publish+audit`) | watch queue → publish → query audit |

All three call the **same REST API**; MCP is a thin typed wrapper, not a separate backend.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Cursor agent    │────▶│ MCP lip-registry │────▶│ REST /v1/*      │
│ (SDK + Autom.)  │     │ (stdio / HTTP)   │     │ lis registry    │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
┌─────────────────┐                                      │
│ GitHub Actions  │──────────────────────────────────────┤
└─────────────────┘                                      │
┌─────────────────┐                                      ▼
│ Service bots    │────────────────────────────▶ lidb + SSD blobs
└─────────────────┘
```

**Layers (build in order):**

1. **REST contract** — OpenAPI v1 + new agent endpoints (below)
2. **Headless CLI** — `lip publish|validate|login --json`
3. **MCP server** — Python package `lip-registry-mcp` (tools map 1:1 to REST)
4. **Cursor Automation template** — “Publish on tag” with MCP + env prefill
5. **Auth hardening** — service tokens, signup tokens, GitHub OIDC

---

## New REST endpoints (agent API)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/v1/agent/capabilities` | Machine manifest: auth modes, max blob, required publish fields, example flows |
| `POST` | `/v1/publish/validate` | Dry-run publish gates; returns `{ ok, errors[], remediation[] }` |
| `POST` | `/v1/publish` | Atomic publish when blob already at `artifact_digest` |
| `GET` | `/v1/audit` | Query `registry_audit_log` (IP, package, token id, event) |
| `POST` | `/v1/auth/signup-tokens` | Mint gated signup invite (session bearer) |
| `POST` | `/v1/auth/oidc/github` | Exchange GitHub OIDC JWT → publish JWT (15m TTL) |
| `POST` | `/v1/auth/device/start` | Device flow: `{ device_code, verification_uri }` |
| `POST` | `/v1/auth/device/poll` | Poll for tokens after user approves |

**Error shape (all write endpoints):**

```json
{
  "error": "bad_request",
  "message": "body digest mismatch",
  "details": { "expected": "sha256:…", "computed": "sha256:…" },
  "remediation": "Re-PUT blob at PUT /v1/blobs/{digest} with exact bytes"
}
```

**Idempotency:** accept `Idempotency-Key` on `POST /v1/publish` and yank; return same 201/200 on replay.

---

## MCP server: `lip-registry`

**Package:** `lis/mcp/lip-registry/` (Python, `mcp` SDK, stdio default).

**Env (agent configures once in Cursor MCP settings):**

```json
{
  "mcpServers": {
    "lip-registry": {
      "command": "python",
      "args": ["-m", "lip_registry_mcp"],
      "env": {
        "LIP_REGISTRY_URL": "https://lip.lilangverse.xyz/v1",
        "LIP_REGISTRY_TOKEN": "${env:LIP_REGISTRY_TOKEN}"
      }
    }
  }
}
```

**Tools (Phase 1):**

| Tool | REST | Notes |
|------|------|-------|
| `registry_capabilities` | `GET /v1/agent/capabilities` | First call in any agent session |
| `registry_list_packages` | `GET /v1/packages` | Filters: name, limit, include_yanked |
| `registry_get_version` | `GET /v1/packages/{name}/{version}` | Includes peer sources |
| `registry_put_blob` | `PUT /v1/blobs/{digest}` | Base64 or file path param |
| `registry_validate_publish` | `POST /v1/publish/validate` | Dry-run |
| `registry_publish` | `POST /v1/publish` or `/packages/{name}/versions` | Idempotency-Key optional |
| `registry_yank` | `POST …/yank` | |
| `registry_query_audit` | `GET /v1/audit` | Bots + compliance |

**Tools (Phase 2 — auth admin):**

| Tool | REST |
|------|------|
| `registry_create_token` | `POST /v1/auth/tokens` |
| `registry_revoke_token` | `DELETE /v1/auth/tokens/{id}` |
| `registry_mint_signup_token` | `POST /v1/auth/signup-tokens` |

**Resources (optional):** `openapi://registry-v1` → cached OpenAPI for agent self-discovery.

**Cursor SDK wiring:** SDK agents declare MCP in `Agent.create({ mcp: { servers: ["lip-registry"] } })` or project `.cursor/mcp.json`. Automations template pre-enables `lip-registry` + `git` tools.

---

## CLI agent mode (`lip --json`)

| Command | Output |
|---------|--------|
| `lip publish --json [--dry-run]` | `{ "status", "name", "version", "digest", "published_at" }` |
| `lip validate --json` | `{ "ok", "errors" }` |
| `lip login --device --json` | `{ "verification_uri", "device_code" }` then tokens |
| `lip whoami --json` | `{ "publisher_id", "scopes" }` |

**Credential resolution order:**

1. `LIP_REGISTRY_TOKEN` env
2. `~/.config/lip/credentials.toml` (`[registry] token = …`)
3. Fail with `{ "error": "unauthorized", "remediation": "lip login or set LIP_REGISTRY_TOKEN" }`

---

## Auth by persona

### A. Cursor agent (emphasis)

1. Human runs `lip login --device` once (or pastes token into Cursor user secret).
2. Cursor MCP reads `LIP_REGISTRY_TOKEN` from env / secrets.
3. Agent calls `registry_capabilities` → `registry_validate_publish` → `registry_put_blob` → `registry_publish`.
4. **Cursor Automation** “Publish on tag”: trigger `git.tag`, tools `git` + `lip-registry`, prompt includes package name from `li.toml`.

### B. GitHub Actions

```yaml
permissions:
  id-token: write
steps:
  - uses: actions/github-script@v7
    id: oidc
    with:
      script: |
        const t = await core.getIDToken('lip-registry');
        core.setOutput('jwt', t);
  - run: |
      TOKEN=$(curl -sS -X POST "$LIP_REGISTRY_URL/auth/oidc/github" \
        -H "Authorization: Bearer ${{ steps.oidc.outputs.jwt }}" | jq -r .access_token)
      LIP_REGISTRY_TOKEN="$TOKEN" lip publish --json
```

No long-lived secret in repo; publish JWT TTL ≤ 15 minutes.

### C. Autonomous bot

1. Admin mints service token: `POST /v1/auth/tokens` `{ "name": "release-bot", "scope": "publish+yank", "ttl_days": 90 }`.
2. Bot stores token in vault; rotates via same API.
3. After each publish, `GET /v1/audit?package=…&limit=10` for confirmation.

**Signup tokens** (gated registry): admin/agent mints invite → bot or human signs up without open registration.

---

## Cursor Automation template (shipped artifact)

**Name:** `lip-publish-on-tag`

| Field | Value |
|-------|-------|
| Trigger | Git tag matching `v*` |
| Tools | `git`, MCP `lip-registry` |
| Secrets | `LIP_REGISTRY_TOKEN` or OIDC (document both) |
| Prompt | Read `li.toml` → validate → publish → print JSON result |

Ship as `docs/automations/lip-publish-on-tag.md` + prefill via Cursor Automations UI when backend-control MCP available.

---

## Implementation phases

### Phase 1 — Agent API + CLI JSON (1 week)

- [ ] `GET /v1/agent/capabilities`
- [ ] `POST /v1/publish/validate` + `remediation` on errors
- [ ] `lip publish|validate --json` + credentials.toml
- [ ] Fix liserver `:80` edge (blocker for public URL)
- [ ] OpenAPI sync for new paths

### Phase 2 — MCP server (1 week)

- [ ] `lis/mcp/lip-registry/` stdio server, Phase 1 tools
- [ ] `.cursor/mcp.json` example in `lis/`
- [ ] Integration test: MCP tool → live registry (mock)

### Phase 3 — Auth for agents (1–2 weeks)

- [ ] Wire `016_registry_security.sql` (signup + audit)
- [ ] Service token CRUD (lidb backend)
- [ ] `GET /v1/audit`
- [ ] Drop public `LI_REGISTRY_DEV_TOKEN`

### Phase 4 — CI + Automation (1 week)

- [ ] `POST /v1/auth/oidc/github`
- [ ] GitHub Action `li-langverse/lip-publish-action`
- [ ] Cursor Automation template + docs

### Phase 5 — Hardening

- [ ] Idempotency-Key on publish/yank
- [ ] Large blob streaming through liserver (>16 KiB)
- [ ] MCP Phase 2 auth tools

---

## Success criteria

| Check | Pass |
|-------|------|
| Cursor agent with MCP only (no manual curl) publishes a package | validate → put_blob → publish returns 201 JSON |
| `lip publish --json` works with only `LIP_REGISTRY_TOKEN` | No `--data-binary` / Host hacks |
| GitHub Action publishes on tag with OIDC | No repo secret for registry token |
| Bot queries audit after publish | `GET /v1/audit` returns event with IP + package |
| OpenAPI + capabilities document every tool param | Agent can self-configure from `capabilities` |

---

## Non-goals (this spec)

- Web UI for registry browsing
- Human MFA flows (separate spec: `docs/auth-2fa-webauthn.md`)
- Non-Li package formats (npm/pypi)

---

## References

- Platform storage/auth: `docs/superpowers/specs/2026-06-07-lip-registry-platform-design.md`
- OpenAPI: `openapi/registry-v1.yaml`
- E2E script: `scripts/lip-multipeer-e2e.sh`
- Cursor SDK MCP config: [cursor.com/docs/sdk](https://cursor.com/docs/sdk)
