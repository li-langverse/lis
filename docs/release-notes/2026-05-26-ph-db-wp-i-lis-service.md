# PH-DB WP-I: lis service profile for hosting

**Branch:** `cursor/wp-i-ph-db-lis-service`  
**Phase:** PH-DB CI/hosting plan WP-I

## Summary

Adds production-shaped **hosting** without TCP wire:

- `profiles/control-plane-min.toml` — registry + control-plane liq plans for `LI_CONTROL_PLANE_STORE=lidb`
- `profiles/tcp-wire-stub.toml` — document-only future TCP loopback (start fails fast)
- `profiles/README.md` + systemd unit sample
- `lis db status` protocol v1 JSON (`live`, `ready`, `checks`, `protocol_version`)
- `lis db start --foreground` for systemd/Docker

## Smoke

```bash
./scripts/db-smoke.sh
LI_PROFILE=control-plane-min ./scripts/db-smoke.sh
```

## lidb migration deps

| Dep | Status |
|-----|--------|
| `001_registry.sql` | Required |
| Native `agent_runs` bootstrap | Required |
| `002_control_plane.sql` (WP-J) | Soft — full control-plane tables |
