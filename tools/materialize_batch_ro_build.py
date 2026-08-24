#!/usr/bin/env python3
"""Batch RO release-artifact preparation tool.

Normal Batch RO source is directly tracked and requires only ``--check``.
``--from-legacy-payload`` exists solely to prepare older reconciled releases
whose Batch RO executable/UI files are still stored as compact Base64/tar
payload pieces. This tool is never imported or called by normal WSGI startup.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from batch_ro_runtime import (  # noqa: E402
    EXPECTED_RUNTIME_MEMBERS,
    MANIFEST_SCHEMA,
    MANIFEST_VERSION,
    validate_batch_ro_deployment_files,
)

LEGACY_PAYLOAD_PARTS = (
    "payload.segment01",
    "payload.segment02",
    "payload.part02",
    "payload.part03",
)
LEGACY_ALLOWED_MEMBERS = EXPECTED_RUNTIME_MEMBERS | {
    "docs/BATCH_RO_ENGINEERING_BASIS.md",
    "tests/test_batch_ro_addon.py",
}
LEGACY_IDENTITY_FILE = "payload.sha256"
UI_MEMBER = "static/addons/batch_ro/batch_ro_addon.js"
_OLD_HOST_PROBE = """const required=['FEATURE_REGISTRY','MODE_FEATURE','WORKSPACE_META','defaults','sections','processModeConfigured','renderFields','changeMode','processPerformanceBody'];
    const missing=required.filter(name=>{try{return typeof eval(name)==='undefined'}catch(_){return true}});
    if(missing.length){console.error('Batch RO add-on not activated; incompatible Total RO Design UI hooks:',missing);return;}""".encode("ascii")
_NEW_HOST_PROBE = """const missing=[];
    if(typeof FEATURE_REGISTRY==='undefined')missing.push('FEATURE_REGISTRY');
    if(typeof MODE_FEATURE==='undefined')missing.push('MODE_FEATURE');
    if(typeof WORKSPACE_META==='undefined')missing.push('WORKSPACE_META');
    if(typeof defaults==='undefined')missing.push('defaults');
    if(typeof sections==='undefined')missing.push('sections');
    if(typeof processModeConfigured==='undefined')missing.push('processModeConfigured');
    if(typeof renderFields==='undefined')missing.push('renderFields');
    if(typeof changeMode==='undefined')missing.push('changeMode');
    if(typeof processPerformanceBody==='undefined')missing.push('processPerformanceBody');
    if(missing.length){console.error('Batch RO add-on not activated; incompatible Total RO Design UI hooks:',missing);return;}""".encode("ascii")


def _read_expected_legacy_sha(root: Path) -> str:
    marker = root / "deploy" / "batch_ro_alpha" / LEGACY_IDENTITY_FILE
    if not marker.is_file():
        raise RuntimeError(f"Missing legacy Batch RO identity marker: {marker}")
    value = marker.read_text(encoding="ascii").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise RuntimeError("Legacy Batch RO payload identity marker is malformed.")
    return value


def _decode_legacy_payload(root: Path, expected_sha: str) -> bytes:
    payload_dir = root / "deploy" / "batch_ro_alpha"
    parts = [payload_dir / name for name in LEGACY_PAYLOAD_PARTS]
    missing = [p.name for p in parts if not p.is_file()]
    if missing:
        raise RuntimeError(f"Legacy Batch RO payload is incomplete: missing {missing}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    padding = (-len(encoded)) % 4
    if padding:
        if padding > 2 or "=" in encoded:
            raise RuntimeError("Legacy Batch RO payload has invalid Base64 padding.")
        encoded += "=" * padding
    raw = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha:
        raise RuntimeError(f"Legacy Batch RO payload SHA-256 mismatch: expected {expected_sha}, got {actual}")
    return raw


def materialize_legacy_payload(root: Path, expected_sha: str) -> dict:
    """Write an older payload into a release tree before application startup."""
    root = root.resolve()
    raw = _decode_legacy_payload(root, expected_sha)
    runtime_hashes: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        names = set(tf.getnames())
        missing_runtime = sorted(EXPECTED_RUNTIME_MEMBERS - names)
        unexpected = sorted(names - LEGACY_ALLOWED_MEMBERS)
        if missing_runtime or unexpected:
            raise RuntimeError(
                f"Legacy Batch RO payload members invalid; missing_runtime={missing_runtime}, unexpected={unexpected}"
            )
        for member in tf.getmembers():
            if not member.isfile():
                raise RuntimeError(f"Legacy Batch RO payload member is not a regular file: {member.name}")
            target = (root / member.name).resolve()
            if root not in target.parents:
                raise RuntimeError(f"Unsafe Batch RO build output path: {member.name}")
            extracted = tf.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"Unable to read Batch RO payload member: {member.name}")
            data = extracted.read()
            if member.name == UI_MEMBER:
                if _NEW_HOST_PROBE in data:
                    pass
                elif _OLD_HOST_PROBE in data:
                    data = data.replace(_OLD_HOST_PROBE, _NEW_HOST_PROBE, 1)
                else:
                    raise RuntimeError("Legacy Batch RO UI host-probe pattern is not recognized.")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            if member.name in EXPECTED_RUNTIME_MEMBERS:
                runtime_hashes[member.name] = hashlib.sha256(data).hexdigest()

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "version": MANIFEST_VERSION,
        "batch_ro_version": "legacy-release",
        "files": dict(sorted(runtime_hashes.items())),
        "provenance": {
            "legacy_payload_sha256": expected_sha,
            "build_transform": "lexical host-probe compatibility moved before WSGI startup",
        },
    }
    manifest_path = root / "deploy" / "batch_ro_runtime_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return validate_batch_ro_deployment_files(root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or verify the immutable Batch RO release artifact.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--check", action="store_true", help="Read-only verification of directly tracked/materialized runtime files.")
    parser.add_argument(
        "--from-legacy-payload",
        action="store_true",
        help="Materialize an older compact Batch payload before staging. Never use from WSGI/runtime.",
    )
    parser.add_argument("--expect-payload-sha", default="")
    args = parser.parse_args()
    root = args.root.resolve()

    if args.check and args.from_legacy_payload:
        raise RuntimeError("Choose either --check or --from-legacy-payload, not both.")
    if args.from_legacy_payload:
        expected = str(args.expect_payload_sha or "").strip().lower() or _read_expected_legacy_sha(root)
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise RuntimeError("--expect-payload-sha must be a 64-character hexadecimal SHA-256.")
        marker = _read_expected_legacy_sha(root)
        if marker != expected:
            raise RuntimeError(f"Legacy Batch RO payload gate mismatch: marker {marker}, expected {expected}")
        identity = materialize_legacy_payload(root, expected)
    else:
        identity = validate_batch_ro_deployment_files(root)

    print(json.dumps(identity, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
