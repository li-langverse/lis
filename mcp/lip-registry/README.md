# lip-registry MCP server

Stdio MCP server that wraps the public lip registry REST API (`/v1/*`). Use from Cursor agents for signup, token minting, and package operations.

## Cursor config

```json
{
  "mcpServers": {
    "lip-registry": {
      "command": "python",
      "args": ["-m", "lip_registry_mcp"],
      "cwd": "/path/to/lis/mcp/lip-registry",
      "env": {
        "PYTHONPATH": "/path/to/lis/mcp/lip-registry",
        "LIP_REGISTRY_URL": "https://lip.lilangverse.xyz/v1",
        "LIP_REGISTRY_TOKEN": ""
      }
    }
  }
}
```

Set `LIP_REGISTRY_TOKEN` after `registry_auth_device_start` + browser approval, or `registry_auth_login` → `registry_auth_create_token`.

## Tools

| Tool | REST |
|------|------|
| `registry_capabilities` | `GET /v1/agent/capabilities` |
| `registry_list_packages` | `GET /v1/packages` |
| `registry_validate_publish` | `POST /v1/publish/validate` |
| `registry_auth_signup` | `POST /v1/auth/signup` |
| `registry_auth_login` | `POST /v1/auth/login` |
| `registry_auth_whoami` | `GET /v1/auth/whoami` |
| `registry_auth_create_token` | `POST /v1/auth/tokens` |
| `registry_auth_device_start` | `POST /v1/auth/device/start` |
| `registry_auth_device_poll` | `POST /v1/auth/device/poll` |
| `registry_mint_signup_token` | `POST /v1/auth/signup-tokens` |

## Local smoke

```bash
export LIP_REGISTRY_URL=http://127.0.0.1:54321/v1
export LI_JWT_SECRET=dev-test
export LI_DATA_DIR=$(mktemp -d)
export LI_REGISTRY_MOCK=1
python3 routes/registry/server.py &
PYTHONPATH=mcp/lip-registry python3 -m lip_registry_mcp <<'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"registry_auth_signup","arguments":{"email":"mcp@test.dev","password":"secret123","publisher_name":"mcp-pub"}}}
EOF
```
