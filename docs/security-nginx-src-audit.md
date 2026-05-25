# Nginx source security audit (oracle)

li-httpd does **not** port nginx C. We read nginx to build **`nginx_mitigations.toml`** and replay exploits against stock nginx + li-httpd.

## Run audit

```bash
git submodule update --init benchmarks/tier5_http/third_party/nginx
python3 benchmarks/tier5_http/harness/audit_nginx_src.py
```

`audit_nginx_src.py` scans `third_party/nginx/CHANGES` for `Security:` lines and merges rows into `benchmarks/tier5_http/nginx_mitigations.toml`. Human review fills `li_invariant` and links proofs.

## Exploit harness

```bash
export PYTHONPATH=benchmarks/tier5_http/harness
python3 benchmarks/tier5_http/harness/exploit_http.py --profile pr
```

Report: `benchmarks/results/exploit_report.csv`.

## Agent rules

- [lic: engineering-standards](https://github.com/li-langverse/lic/blob/dev/docs/ecosystem/engineering-standards.md)
- Tier A/B exploits must pass before M1 httpd merge
