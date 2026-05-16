# Package API catalogs

Planned public surface per package (implementation follows Li compiler stabilization).

**Create or change packages only via [`li-new-package`](../../package-workflow.md)** (master plan Pkg) — not by copying these directories by hand.

| Package | Doc |
|---------|-----|
| [li-httpd](li-httpd.md) | Binary, workers, setup commands |
| [li-http](li-http.md) | Parser, router, proxy, leak_censor |
| [li-net](li-net.md) | Reactor, TCP, DNS |
| [li-log](li-log.md) | Sinks, rotation, redaction |
| [li-tls](li-tls.md) | TLS 1.3 record + handshake |
| [li-acme](li-acme.md) | Let's Encrypt client |
| [li-crypto](li-crypto.md) | Primitives |
| [li-rng](li-rng.md) | Prng, Csprng, SimRng |
| [li-prob](li-prob.md) | prob_ensures, Monte Carlo |
| [li-schema](li-schema.md) | Migration → censor paths |
| [li-bytes](li-bytes.md) | Reader/Writer |
| [li-math](li-math.md) | Numerics (org package) |

See also [org-packages.md](../org-packages.md).
