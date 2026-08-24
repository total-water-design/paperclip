from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

import batch_ro_runtime as runtime


def _copy_runtime_tree(tmp_path: Path) -> Path:
    root = tmp_path / "release"
    for relative in runtime.EXPECTED_RUNTIME_MEMBERS:
        src = runtime.ROOT / relative
        dst = root / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    manifest_src = runtime.ROOT / "deploy" / "batch_ro_runtime_manifest.json"
    manifest_dst = root / "deploy" / "batch_ro_runtime_manifest.json"
    manifest_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_src, manifest_dst)
    return root


def test_current_tracked_runtime_matches_frozen_manifest():
    identity = runtime.validate_batch_ro_deployment_files(runtime.ROOT)
    assert identity["schema"] == runtime.MANIFEST_SCHEMA
    assert identity["manifest_version"] == runtime.MANIFEST_VERSION
    assert identity["file_count"] == 4
    assert set(identity["files"]) == runtime.EXPECTED_RUNTIME_MEMBERS


def test_repeated_verification_is_idempotent():
    first = runtime.validate_batch_ro_deployment_files(runtime.ROOT)
    second = runtime.validate_batch_ro_deployment_files(runtime.ROOT)
    assert first == second


def test_missing_runtime_file_fails_closed(tmp_path):
    root = _copy_runtime_tree(tmp_path)
    (root / "addons" / "batch_ro" / "engine.py").unlink()
    with pytest.raises(runtime.BatchRODeploymentError) as excinfo:
        runtime.validate_batch_ro_deployment_files(root)
    message = str(excinfo.value)
    assert "missing addons/batch_ro/engine.py" in message
    assert "normal application startup will not modify application source files" in message


def test_tampered_runtime_file_fails_closed(tmp_path):
    root = _copy_runtime_tree(tmp_path)
    target = root / "static" / "addons" / "batch_ro" / "batch_ro_addon.js"
    target.write_text(target.read_text(encoding="utf-8") + "\n// tampered\n", encoding="utf-8")
    with pytest.raises(runtime.BatchRODeploymentError, match="identity mismatch"):
        runtime.validate_batch_ro_deployment_files(root)


def test_missing_or_malformed_manifest_fails_closed(tmp_path):
    root = _copy_runtime_tree(tmp_path)
    manifest = root / "deploy" / "batch_ro_runtime_manifest.json"
    manifest.unlink()
    with pytest.raises(runtime.BatchRODeploymentError, match="runtime manifest is missing"):
        runtime.validate_batch_ro_deployment_files(root)

    root = _copy_runtime_tree(tmp_path / "malformed")
    manifest = root / "deploy" / "batch_ro_runtime_manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["files"]["addons/batch_ro/engine.py"] = "not-a-sha"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(runtime.BatchRODeploymentError, match="Invalid Batch RO SHA-256"):
        runtime.validate_batch_ro_deployment_files(root)


def test_runtime_module_contains_no_source_tree_write_or_payload_unpacking():
    source = Path(runtime.__file__).read_text(encoding="utf-8")
    forbidden = (
        "tarfile",
        "base64",
        "extractall(",
        ".write_text(",
        ".write_bytes(",
        ".mkdir(",
        "os.makedirs(",
        "shutil.copy",
    )
    for token in forbidden:
        assert token not in source, token
