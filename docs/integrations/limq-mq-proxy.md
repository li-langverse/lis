# limq message queue — lis edge integration

See [limq `lis/routes.md`](https://github.com/li-langverse/limq/blob/main/lis/routes.md) for the full route table.

## Environment

| Variable | Default |
|----------|---------|
| `LI_MQ_UPSTREAM` | `http://127.0.0.1:9478` |

## Auth

JWT → `mq:publish:{topic}`, `mq:consume:{topic}`, `mq:admin`.

## Note

Current `lis` tree is the embedded **lidb supervisor**. HTTP edge proxy may land in **li-httpd**; this doc is the contract until proxy code exists.
