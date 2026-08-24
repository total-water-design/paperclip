"""Immutable runtime registration for the Total RO Design Batch RO add-on.

Batch RO executable/UI files are tracked in the release artifact before
Gunicorn starts. Normal WSGI startup reads a checked-in SHA-256 manifest,
verifies the already-present files, and then imports/registers Batch RO.

This module deliberately contains no payload extraction, source patching,
directory creation, file generation, or other application-source mutation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "deploy" / "batch_ro_runtime_manifest.json"
UI_SCRIPT = "/static/addons/batch_ro/batch_ro_addon.js"
EXPECTED_RUNTIME_MEMBERS = {
    "addons/batch_ro/__init__.py",
    "addons/batch_ro/engine.py",
    "static/addons/batch_ro/batch_ro.svg",
    "static/addons/batch_ro/batch_ro_addon.js",
}
MANIFEST_SCHEMA = "twds.batch-ro-runtime-manifest"
MANIFEST_VERSION = 1


class BatchRODeploymentError(RuntimeError):
    """The immutable Batch RO deployment artifact is absent or does not match."""


def _load_runtime_manifest(root: Path = ROOT) -> dict:
    root = Path(root).resolve()
    path = root / "deploy" / "batch_ro_runtime_manifest.json"
    if not path.is_file():
        raise BatchRODeploymentError(
            "Batch RO runtime manifest is missing: deploy/batch_ro_runtime_manifest.json. "
            "Prepare the complete release artifact before Gunicorn starts."
        )
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BatchRODeploymentError("Batch RO runtime manifest is not valid UTF-8 JSON.") from exc
    if not isinstance(manifest, dict):
        raise BatchRODeploymentError("Batch RO runtime manifest root must be an object.")
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("version") != MANIFEST_VERSION:
        raise BatchRODeploymentError(
            f"Unsupported Batch RO runtime manifest: expected {MANIFEST_SCHEMA} v{MANIFEST_VERSION}."
        )
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise BatchRODeploymentError("Batch RO runtime manifest files entry must be an object.")
    names = set(files)
    if names != EXPECTED_RUNTIME_MEMBERS:
        missing = sorted(EXPECTED_RUNTIME_MEMBERS - names)
        unexpected = sorted(names - EXPECTED_RUNTIME_MEMBERS)
        raise BatchRODeploymentError(
            f"Batch RO runtime manifest member mismatch; missing={missing}, unexpected={unexpected}."
        )
    for relative, digest in files.items():
        if not isinstance(relative, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise BatchRODeploymentError(f"Invalid Batch RO SHA-256 identity for {relative!r}.")
    return manifest


def validate_batch_ro_deployment_files(root: Path = ROOT) -> dict:
    """Fail closed unless every tracked Batch RO runtime file matches its SHA."""
    root = Path(root).resolve()
    manifest = _load_runtime_manifest(root)
    problems: list[str] = []
    identities: dict[str, str] = {}
    for relative, expected_sha in sorted(manifest["files"].items()):
        path = root / relative
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            problems.append(f"missing {relative}")
            continue
        if root not in resolved.parents:
            problems.append(f"unsafe path {relative}")
            continue
        if path.is_symlink() or not resolved.is_file():
            problems.append(f"not a regular tracked file {relative}")
            continue
        actual_sha = hashlib.sha256(resolved.read_bytes()).hexdigest()
        identities[relative] = actual_sha
        if actual_sha != expected_sha:
            problems.append(
                f"identity mismatch {relative}: expected {expected_sha}, got {actual_sha}"
            )
    if problems:
        raise BatchRODeploymentError(
            "Batch RO immutable deployment artifact is not ready: " + "; ".join(problems) + ". "
            "Release preparation/reconciliation must install the exact tracked files; "
            "normal application startup will not modify application source files."
        )
    manifest_bytes = (root / "deploy" / "batch_ro_runtime_manifest.json").read_bytes()
    return {
        "schema": manifest["schema"],
        "manifest_version": manifest["version"],
        "batch_ro_version": manifest.get("batch_ro_version"),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "files": identities,
        "file_count": len(identities),
        "provenance": manifest.get("provenance") or {},
    }


def register_batch_ro_runtime(app, calculations) -> None:
    """Read-only verification followed by Batch RO calculation/UI registration."""
    identity = validate_batch_ro_deployment_files(ROOT)
    from addons.batch_ro import register_batch_ro

    register_batch_ro(app, calculations)
    app.config["BATCH_RO_DEPLOYMENT_IDENTITY"] = identity

    if getattr(app, "_totalro_batch_ro_ui_runtime_registered", False):
        return

    from flask import request

    @app.after_request
    def _inject_batch_ro_workspace_loader(response):
        if request.path != "/ro" or response.status_code != 200:
            return response
        content_type = str(response.headers.get("Content-Type", "")).lower()
        if "text/html" not in content_type:
            return response
        html = response.get_data(as_text=True)
        if UI_SCRIPT in html or "</body>" not in html:
            return response
        loader = f'<script src="{UI_SCRIPT}"></script>\n'
        response.set_data(html.replace("</body>", loader + "</body>", 1))
        response.headers["Content-Length"] = str(len(response.get_data()))
        return response

    app._totalro_batch_ro_ui_runtime_registered = True
