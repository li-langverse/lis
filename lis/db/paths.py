"""Resolve lidb sibling repo, embed binary, and data directories."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

_LIS_ROOT = Path(__file__).resolve().parents[2]


def lis_root() -> Path:
    return _LIS_ROOT


def resolve_data_dir(explicit: str | None = None) -> Path:
    raw = explicit or os.environ.get("LI_DATA_DIR") or "./.li-data"
    return Path(raw).expanduser().resolve()


def resolve_profile_name(explicit: str | None = None) -> str:
    return explicit or os.environ.get("LI_PROFILE", "registry-min")


def profile_path(profile: str) -> Path:
    path = lis_root() / "profiles" / f"{profile}.toml"
    if not path.is_file():
        raise FileNotFoundError(f"profile not found: {path}")
    return path


def find_lidb_repo() -> Path | None:
    override = os.environ.get("LIDB_REPO", "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        return p if (p / "liorm").is_dir() else None
    for candidate in (
        lis_root().parent / "lidb",
        lis_root() / "vendor" / "lidb",
    ):
        if (candidate / "liorm").is_dir() and (candidate / "migrations" / "001_registry.sql").is_file():
            return candidate.resolve()
    return None


def require_lidb_repo() -> Path:
    repo = find_lidb_repo()
    if repo is None:
        raise RuntimeError(
            "lidb repo not found. Clone li-langverse/lidb beside lis or set LIDB_REPO to its root."
        )
    return repo


def embed_binary(lidb_repo: Path) -> Path | None:
    override = os.environ.get("LIDB_EMBED", "").strip()
    if override:
        p = Path(override)
        return p if p.is_file() else None
    for candidate in (
        lidb_repo / "build" / "smoke" / "lidb_embed",
        lidb_repo / "build" / "lidb_embed",
    ):
        if candidate.is_file():
            return candidate
    return None


def build_embed(lidb_repo: Path) -> Path | None:
    if not shutil.which("cmake"):
        return None
    build_dir = lidb_repo / "build" / "smoke"
    build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["cmake", "-S", str(lidb_repo), "-B", str(build_dir), "-DCMAKE_BUILD_TYPE=Release"],
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["cmake", "--build", str(build_dir), "--target", "lidb_embed", "-j"],
        capture_output=True,
        check=False,
    )
    return embed_binary(lidb_repo)


def ensure_embed(lidb_repo: Path) -> Path:
    binary = embed_binary(lidb_repo) or build_embed(lidb_repo)
    if binary is None:
        raise RuntimeError("lidb_embed unavailable (install cmake and build lidb)")
    return binary


def heap_catalog_path(data_dir: Path) -> Path:
    return data_dir / ".lidb" / "catalog.heap"


def state_path(data_dir: Path) -> Path:
    return data_dir / ".lis" / "db-state.json"


def configure_lidb_env(*, lidb_repo: Path, data_dir: Path, embed: Path) -> None:
    os.environ["LIDB_REPO"] = str(lidb_repo)
    os.environ["LIDB_DATA_DIR"] = str(data_dir)
    os.environ["LIDB_EMBED"] = str(embed)
    os.environ["LI_DATA_DIR"] = str(data_dir)
