# li-math

**Status:** planned (org package stub — no `.li` sources yet)

Shared proved numerics (vectors, stable reductions) for **lis** and other Li projects. May live in this monorepo or as a separate [li-langverse/li-math](https://github.com/li-langverse/li-math) repository.

## Planned API

| Module | Procs (planned) |
|--------|-----------------|
| `scalar` | `fma`, `clamp`, `lerp` with `requires`/`ensures` |
| `vec` | `dot`, `norm`, `normalize` on fixed-size vectors |
| `prob` | helpers shared with `li-prob` (collision estimators consume math lemmas) |

## Dependencies

- None at infra phase; will depend on compiler `std` / `li-bytes` when coded.

## See also

- [org-packages.md](../org-packages.md)
- [packages/li-math/PUBLISH.md](../../packages/li-math/PUBLISH.md)
