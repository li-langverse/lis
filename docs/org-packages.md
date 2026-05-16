# Li Langverse packages

Packages are developed in **this repo** (`lis`) as stubs until the Li compiler stabilizes, then published under the [li-langverse](https://github.com/li-langverse) org.

| Package | In `lis` monorepo | Separate org repo (when ready) |
|---------|-------------------|--------------------------------|
| `li-httpd`, `li-http`, `li-net`, … | yes | optional split |
| `li-math` | stub in `packages/li-math` | **li-langverse/li-math** (recommended home for numerics) |

Create new org repos only for boundaries you want to version independently (e.g. math used by compiler + server). Server-specific code stays in **lis**.
