## Summary

## Release notes (required)

Policy: https://github.com/li-langverse/roadmap/blob/main/docs/ecosystem/release-notes.md

- [ ] **CHANGELOG.md** + `docs/release-notes/YYYY-MM-DD-<slug>.md` (**Agent continuation**, **Not changed**)

## Engineering gates (mandatory)

- [ ] **Functionality** — tests / harness green; spec or REQ ids cited
- [ ] **Security** — relevant CVE/exploit TOML rows; `exploit_http --profile pr` if touching http/net/crypto/rng
- [ ] **Performance** — bench row or N/A with reason
- [ ] **Learned from** — 2–4 reference ecosystems noted (if new feature)

## Test plan

- [ ] CI green on ubuntu-24.04, macos-14, windows-latest
- [ ] `./scripts/ci.sh` locally

## Notes

Infra-only until `lic` P0 (2e–2f, bytes, async). See [implementation-status.md](../docs/implementation-status.md).
