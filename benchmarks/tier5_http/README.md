# tier5_http — li-httpd benchmarks & exploits

TOML-driven harness (no hardcoded scenarios in Python). Nginx is **oracle only** — not ported to Li.

## Quick start (CI / verify-only)

```bash
./scripts/verify-http.sh
# or
cd benchmarks/tier5_http/harness
export PYTHONPATH=.
python3 verify_http.py --all --profile ci
python3 exploit_http.py --profile pr
python3 bench_http.py static_small --profile ci
```

## Nginx source audit (optional)

```bash
git submodule update --init benchmarks/tier5_http/third_party/nginx
python3 benchmarks/tier5_http/harness/audit_nginx_src.py
```

## Profiles

| Profile | `suite.toml` | Timing |
|---------|--------------|--------|
| `ci` | verify only | no |
| `nightly` | + keepalive_pipelining | yes (when servers ship) |

Exploits: `suite_exploits.toml` — `pr` vs `nightly`.

## Docs

- [docs/security-nginx-src-audit.md](../../docs/security-nginx-src-audit.md)
- [docs/plan.md](../../docs/plan.md) — full li-httpd plan copy

**Learned from:** nginx (CVE checklist), wrk/h2load (load tools), Envoy/LiteLLM (limits) — see [lic engineering-standards](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/engineering-standards.md).
