"""Agent-first registry API helpers (capabilities + dry-run validate)."""

from __future__ import annotations

import os
import re
from typing import Any

from .errors import RegistryError

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$")

MIN_COVERAGE_PCT = 80.0
DEFAULT_MAX_BLOB_BYTES = 16 * 1024 * 1024


def _max_blob_bytes() -> int:
    raw = os.environ.get("LIP_MAX_BLOB_BYTES", "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_MAX_BLOB_BYTES


def get_agent_capabilities() -> dict[str, Any]:
    """Machine manifest for Cursor agents and headless CLI."""
    return {
        "api_version": "1",
        "auth_modes": ["bearer_token", "oidc_github", "device"],
        "max_blob_bytes": _max_blob_bytes(),
        "min_coverage_pct": MIN_COVERAGE_PCT,
        "required_publish_fields": ["version", "tree_digest", "proof_digest", "coverage_pct"],
        "optional_publish_fields": [
            "artifact_digest",
            "manifest_signature",
            "publisher_key_id",
            "pkg_id",
            "spdx_license",
            "repository_url",
            "documentation_url",
            "source",
            "attestation",
        ],
        "example_flows": [
            {
                "name": "agent_publish",
                "steps": [
                    "GET /v1/agent/capabilities",
                    "POST /v1/publish/validate",
                    "PUT /v1/blobs/{artifact_digest}",
                    "POST /v1/packages/{name}/versions",
                ],
            },
            {
                "name": "cli_publish",
                "steps": [
                    "lip validate --json",
                    "lip publish --json",
                ],
            },
        ],
        "endpoints": {
            "capabilities": "GET /v1/agent/capabilities",
            "validate": "POST /v1/publish/validate",
            "put_blob": "PUT /v1/blobs/{digest}",
            "publish": "POST /v1/packages/{name}/versions",
            "list_packages": "GET /v1/packages",
            "openapi": "GET /v1/openapi.yaml",
            "audit": "GET /v1/audit",
        },
    }


def _validation_issue(
    field: str,
    error: str,
    message: str,
    remediation: str,
) -> dict[str, str]:
    return {
        "field": field,
        "error": error,
        "message": message,
        "remediation": remediation,
    }


def validate_publish_payload(
    name: str,
    body: dict[str, Any],
    *,
    check_blob: bool = True,
) -> dict[str, Any]:
    """Dry-run publish gates; returns { ok, errors[], remediation[] }."""
    errors: list[dict[str, str]] = []
    remediations: list[str] = []

    def add(field: str, error: str, message: str, remediation: str) -> None:
        errors.append(_validation_issue(field, error, message, remediation))
        if remediation not in remediations:
            remediations.append(remediation)

    if not name:
        add("name", "bad_request", "package name is required", "Set name in JSON body or URL path")
    elif not NAME_RE.match(name):
        add(
            "name",
            "bad_request",
            "invalid package name",
            "Use lowercase semver-safe name matching ^[a-z][a-z0-9_-]*$",
        )

    version = body.get("version")
    if not version:
        add("version", "bad_request", "version is required", "Set semver version (e.g. 0.1.0)")
    elif not VERSION_RE.match(str(version)):
        add("version", "bad_request", "invalid version", "Use semver MAJOR.MINOR.PATCH (optional -prerelease)")

    tree = body.get("tree_digest")
    proof = body.get("proof_digest")
    coverage = body.get("coverage_pct")

    if not tree:
        add(
            "tree_digest",
            "bad_request",
            "tree_digest is required",
            "Run lic build and copy tree_digest from publish manifest",
        )
    if not proof:
        add(
            "proof_digest",
            "bad_request",
            "proof_digest is required",
            "Run lic build — proof_digest comes from the build certificate",
        )
    if coverage is None:
        add(
            "coverage_pct",
            "bad_request",
            "coverage_pct is required",
            "Run lit test --coverage and read .lit/coverage_pct.txt",
        )
    else:
        try:
            cov = float(coverage)
        except (TypeError, ValueError):
            add("coverage_pct", "bad_request", "coverage_pct must be a number", "Set coverage_pct from lit test output")
        else:
            if cov < MIN_COVERAGE_PCT:
                add(
                    "coverage_pct",
                    "forbidden",
                    f"coverage_pct below minimum ({MIN_COVERAGE_PCT:g})",
                    f"Increase test coverage to at least {MIN_COVERAGE_PCT:g}% before publishing",
                )

    if check_blob and os.environ.get("LIP_REGISTRY_REQUIRE_BLOB", "1") not in ("0", "false", "no"):
        artifact = body.get("artifact_digest") or tree
        if artifact:
            from .blob_store import get_blob_store, normalize_digest

            try:
                digest = normalize_digest(str(artifact))
                get_blob_store().head(digest)
            except RegistryError as exc:
                if exc.status == 404:
                    add(
                        "artifact_digest",
                        "precondition_failed",
                        "artifact blob must be uploaded before publish",
                        f"PUT /v1/blobs/{artifact} with exact package bytes before publish",
                    )
                elif exc.status == 400:
                    add(
                        "artifact_digest",
                        exc.error,
                        exc.message,
                        "Use sha256: + 64 lowercase hex chars for digests",
                    )
                else:
                    add("artifact_digest", exc.error, exc.message, "Fix blob upload and retry validate")

    return {"ok": len(errors) == 0, "errors": errors, "remediation": remediations}


def remediation_for_error(error: str, message: str, details: dict[str, Any] | None = None) -> str | None:
    """Map registry error codes to agent-facing remediation hints."""
    details = details or {}
    if error == "unauthorized":
        return "Set LIP_REGISTRY_TOKEN or run lip login --device"
    if error == "forbidden" and "coverage" in message.lower():
        return f"Run lit test --coverage and ensure >= {MIN_COVERAGE_PCT:g}% before publish"
    if error == "precondition_failed" or "blob" in message.lower():
        digest = details.get("expected") or details.get("digest") or details.get("artifact_digest")
        if digest:
            return f"Re-PUT blob at PUT /v1/blobs/{digest} with exact bytes"
        return "PUT /v1/blobs/{artifact_digest} with exact package bytes before publish"
    if error == "bad_request" and "digest mismatch" in message.lower():
        expected = details.get("expected", "{digest}")
        return f"Re-PUT blob at PUT /v1/blobs/{expected} with exact bytes"
    if error == "conflict":
        return "Bump version or yank the existing release before republishing"
    if error == "not_found":
        return "Check package name and version, or publish a new version"
    return None
