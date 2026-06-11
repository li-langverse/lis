#!/usr/bin/env python3
"""Tests for lidb catalog.heap auth persistence."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from routes.auth.lidb_snapshot import catalog_path, ensure_auth_schema, load_catalog, merge_auth_tables
from routes.auth.store import auth_backend_name, get_auth_store, reset_auth_store


def test_ensure_and_roundtrip() -> None:
    tmp = tempfile.mkdtemp(prefix="lis-lidb-auth-")
    os.environ["LI_DATA_DIR"] = tmp
    os.environ["LI_AUTH_BACKEND"] = "lidb"
    os.environ["LI_REGISTRY_MOCK"] = "0"
    os.environ["LI_JWT_SECRET"] = "test-secret"
    reset_auth_store()

    ensure_auth_schema(tmp)
    store = get_auth_store()
    assert auth_backend_name() == "lidb"
    result = store.signup("lidb@test.dev", "password-123", publisher_name="lidb-pub")
    assert result["access_token"]

    reset_auth_store()
    store2 = get_auth_store()
    store2.login("lidb@test.dev", "password-123")

    cat = load_catalog(catalog_path(tmp))
    assert len(cat.get("users", [])) == 1
    assert len(cat.get("publishers", [])) == 1
    print("lidb snapshot auth: ok")


if __name__ == "__main__":
    test_ensure_and_roundtrip()
