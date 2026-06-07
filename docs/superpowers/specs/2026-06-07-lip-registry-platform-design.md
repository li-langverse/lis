# lip registry platform — storage, auth, security (2026-06-07)

## SSD storage (engine)

### Disk map (detected 2026-06-07)

| Device | Size | Mount | Role |
|--------|------|-------|------|
| **sdb1** | 931G | `/var/lib/lip-registry` | **Primary registry SSD** (870G free) |
| sdc1 | 931G | — | Spare — cold backup / peer tier |
| nvme0n1p3 | 930G | — | Spare — optional hot tier after repartition |
| sda2 | 441G | root | OS — do not use |

**Decision:** Keep **sdb1** as the package registry blob store. Blobs at `/var/lib/lip-registry/blobs` via hostPath on `lip-registry-bootstrap` and peers.

**Verify:** `kubectl apply -f deploy/k8s/registry/job-lip-ssd-verify.yaml`

### Gaps

- Main `deployment.yaml` still uses 10Gi PVC only — wire `lip-registry-blobs` PVC or hostPath like bootstrap.
- ~~PUT via liserver `:80` returns 502 — use `:30422` for blob writes until li-httpd PUT relay fixed.~~ **Fixed (2026-06-07):** rebuild `lip-liserver-bin` from `lic@cursor/ph-ml-li-array` + upstream reuse patch; verify with `job-lip-put-smoke.yaml`.
- **Large blob streaming (>16 KiB):** small payloads PUT/GET via `:80` pass; bodies above ~16 KiB may still stall in li-httpd proxy relay (track in lic `li_rt_net.c` streaming path — Phase 5 hardening).

---

## Auth (Li-native, agent-automatable)

### Today (MVP mock)

- `POST /v1/auth/signup`, `login`, token CRUD — `lis/routes/auth/`
- Scoped API tokens: `publish`, `yank`, `publish+yank`
- CLI: `lip-login.sh` → `~/.config/lip/credentials.toml`
- Agents: `LIP_REGISTRY_TOKEN` env for publish

### Phase A — production backend (next)

1. `lidb` migration `016_registry_security.sql` — signup_tokens + registry_audit_log
2. Users table + wire `api_tokens` DDL (`004_auth_tokens.sql`)
3. Replace `auth-mock.json` with lidb store
4. Remove `LI_REGISTRY_DEV_TOKEN` on public engine

### Phase B — signup policy

- `POST /v1/auth/signup` requires `signup_token` when `LIP_REGISTRY_SIGNUP=gated`
- Admin/agent mint: `POST /v1/auth/signup-tokens` (session bearer)
- One-time or multi-use invites with expiry

### Phase C — MFA (spec: `docs/auth-2fa-webauthn.md`)

- TOTP enroll/verify after password login
- WebAuthn register/login ceremonies
- API tokens unchanged for CI (no MFA on bearer publish)

### Phase D — agent automation

| Agent flow | Mechanism |
|------------|-----------|
| Human once | `lip login` → session → `lip token create --scope publish` |
| CI publish | GitHub Actions secret `LIP_REGISTRY_TOKEN` |
| OIDC (future) | `POST /v1/auth/oidc/github` → short-lived publish JWT |
| Device flow | `lip login --device` (OAuth2 device code) |

**Gap:** `lip publish` does not auto-read `credentials.toml` — add in `lip/scripts/registry_client.py`.

---

## Security

| Feature | Status | Path |
|---------|--------|------|
| Semver versioning + yank | Shipped (mock) | `liorm_mock.py` |
| Blob-before-publish | Shipped | `LIP_REGISTRY_REQUIRE_BLOB` |
| Scoped bearer tokens | Shipped | `routes/auth/` |
| Edge rate limit | Shipped | liserver 1000 rps |
| **IP access log** | **Added** | `routes/registry/audit_log.py` |
| Audit DB table | Migration ready | `lidb/migrations/016_registry_security.sql` |
| Publish event audit | Pending | wire lidb on publish/yank |
| App rate limits | Pending | middleware on POST/PUT |
| RLS multi-tenant | DDL prep | `002_rls_registry.sql` |

---

## Implementation order

1. SSD verify job + wire bootstrap blobs (done on engine)
2. IP access log (stderr JSON lines)
3. lidb users + auth store + drop dev token
4. Signup tokens (gated registry)
5. MFA Phase 1 (TOTP)
6. OIDC for CI
7. Full audit persistence to `registry_audit_log`
