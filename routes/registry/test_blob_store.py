"""Tests for registry blob store and handlers."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from routes.registry.blob_store import BlobStore, normalize_digest
from routes.registry.handlers import handle_request
from routes.registry.liorm_mock import reset_registry_store


class BlobStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["LIP_BLOB_DIR"] = str(Path(self.tmp.name) / "blobs")
        os.environ["LI_DATA_DIR"] = self.tmp.name
        os.environ["LI_REGISTRY_MOCK"] = "1"
        os.environ["LI_REGISTRY_DEV_TOKEN"] = "test-token"
        os.environ["LI_JWT_SECRET"] = "test-secret"
        reset_registry_store()

    def tearDown(self) -> None:
        self.tmp.cleanup()
        reset_registry_store()

    def test_put_get_roundtrip(self) -> None:
        store = BlobStore()
        data = b"hello-li-package"
        import hashlib

        digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
        out = store.put(digest, data, token="test-token")
        self.assertTrue(out["stored"])
        got, _ = store.get(digest)
        self.assertEqual(got, data)

    def test_handler_blob_put_then_publish(self) -> None:
        import hashlib

        data = b"artifact-bytes"
        digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
        status, _, body = handle_request(
            "PUT",
            f"/v1/blobs/{digest}",
            headers={"Authorization": "Bearer test-token"},
            body=data,
        )
        self.assertEqual(status, 201)
        pub = {
            "version": "0.2.0",
            "tree_digest": "sha256:" + "c" * 64,
            "proof_digest": "sha256:" + "d" * 64,
            "coverage_pct": 90.0,
            "artifact_digest": digest,
        }
        status, _, body = handle_request(
            "POST",
            "/v1/packages/pkg-blob/versions",
            headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
            body=json.dumps(pub).encode(),
        )
        self.assertEqual(status, 201, body.decode())
        status, _, body = handle_request("GET", f"/v1/blobs/{digest}")
        self.assertEqual(status, 200)
        self.assertEqual(body, data)


if __name__ == "__main__":
    unittest.main()
