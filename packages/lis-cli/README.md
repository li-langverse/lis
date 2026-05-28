# lis-cli (lip meta-package)

Declares a **git** dependency on [li-langverse/lis](https://github.com/li-langverse/lis) for `lip install`.

After install, run the repo installer:

```bash
./.li/vendor/lis/scripts/install-lis.sh
lis staging up
```

For local development beside **lip**, use `path = "../../"` instead of `git =` in `li.toml`.
