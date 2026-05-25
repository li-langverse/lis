# Production registry deploy (PH-DB-4)

<!-- DOC-lis-production-registry -->

**Status:** Host runbook for **registry-min** on a single machine. Registry REST + embedded **lidb** ship via `lis db`; TLS terminates at **li-httpd** (or interim proxy) in front of the API port.

**Placeholder API base:** `https://registry.li-langverse.example/v1` — replace `<registry-host>` below with your real FQDN after DNS is live. **Do not commit real tokens or ACME keys.**

---

## 1. Human prerequisites (org)

| Item | Notes |
|------|--------|
| **DNS** | CNAME or A record for `<registry-host>` → public IP of registry VM |
| **TLS** | `li-httpd setup-tls` (target) or nginx/Caddy until li-httpd M1 binds `:443`; proxy to `127.0.0.1:54321` |
| **`LIP_REGISTRY_TOKEN`** | Org-issued bearer for `POST /v1/packages/{name}/versions`; store in vault/K8s secret; inject at publish time only |
| **Publisher keys** | Ed25519 `publishers` rows in lidb (PH-DB-5); map token → `publishers.key_id` when auth is enforced |

Agents **must not** create or paste production secrets into repos or PRs.

---

## 2. Host bootstrap (`registry-min`)

```bash
# Persistent state (adjust path for your OS layout)
export LI_DATA_DIR=/var/lib/lis/registry
export LI_PROFILE=registry-min
export LI_API_PORT=54321
export LI_DB_PORT=54322

# One-time / upgrade
lis db migrate --profile registry-min

# Long-running supervisor (foreground example; use systemd in prod)
lis db start --profile registry-min --foreground
```

Registry REST listens on **`http://127.0.0.1:54321/v1`** locally. Public clients use **`https://<registry-host>/v1`** through TLS at the edge.

Verify locally before exposing DNS:

```bash
curl -fsS "http://127.0.0.1:54321/v1/openapi.yaml" | head -n 5
lis db status
```

---

## 3. Environment template (copy to host; fill secrets offline)

Save as `/etc/lis/registry.env` (mode `600`, root-owned). Values shown are **examples only**.

```bash
# --- lis registry-min (required) ---
LI_DATA_DIR=/var/lib/lis/registry
LI_PROFILE=registry-min
LI_API_PORT=54321
LI_DB_PORT=54322
LI_REGISTRY_API=1

# --- optional overrides ---
# LI_REGISTRY_MOCK=0          # use real lidb liorm when native engine is default
# LI_CHANGEFEED_NATIVE=1      # after lidb changefeed lands

# --- edge / TLS (li-httpd or proxy) ---
# REGISTRY_PUBLIC_HOST=registry.li-langverse.example
# LI_HTTPD_CONFIG=/etc/li-httpd/registry.toml

# --- lip publish from CI or operator workstation (not on lis host unless needed) ---
# LIP_REGISTRY_TOKEN=<paste-from-org-secrets-manager>
# lip publish --registry https://${REGISTRY_PUBLIC_HOST}/v1
```

Load in systemd:

```ini
[Service]
EnvironmentFile=/etc/lis/registry.env
ExecStart=/usr/local/bin/lis db start --profile registry-min
```

---

## 4. TLS via li-httpd (target path)

Until **li-httpd** ships M1 on this host, use any TLS terminator that forwards:

| Public path | Backend |
|-------------|---------|
| `https://<registry-host>/v1/*` | `http://127.0.0.1:54321/v1/*` |
| `wss://<registry-host>/socket/websocket` (stack-full only) | `ws://127.0.0.1:54323/...` |

After **li-httpd** is installed: `li-httpd setup-tls` for ACME or org certs, then route registry vhost to `LI_API_PORT`. See [cli.md](cli.md) and [plan.md](plan.md).

---

## 5. Operator publish smoke (after TLS + token)

From a package repo with `lic build` + `lit test --coverage` green:

```bash
export LIP_REGISTRY_TOKEN="<from-secrets-manager>"
lip publish --registry "https://<registry-host>/v1"
curl -fsS -H "Accept: application/json" \
  "https://<registry-host>/v1/packages/<name>/<version>"
```

**lip** CI validates the placeholder URL without network: `../lip/scripts/validate-production-registry-url.sh`.

---

## 6. Not in scope (registry-min)

- Realtime (`stack-full`), Studio, OAuth, object storage — opt-in profiles later
- Control-plane Supabase migration (PH-DB-10) — independent of registry v1
- SQLite as production store — smoke only; native lidb required for PH-DB-3.1

---

## Links

- CLI stub: [`cli-db.md`](cli-db.md)
- Profile: [`profiles/registry-min.toml`](../profiles/registry-min.toml)
- OpenAPI: [`openapi/registry-v1.yaml`](../openapi/registry-v1.yaml)
- lip client: [registry deploy flow](https://github.com/li-langverse/lip/blob/main/docs/registry.md)
- Ecosystem checklist: [roadmap `ph-db-status.md` §5](https://github.com/li-langverse/roadmap/blob/main/docs/ecosystem/ph-db-status.md)
