from __future__ import annotations

from pathlib import Path

import batch_ro_runtime


EXPECTED_ALPHA_PAYLOAD_SHA = "04fd024a5a8894fc623c065477fa7ebca31e7a4d9454fa03ace03b850d9e0afa"


def test_batch_ro_materialization_is_build_time_only_and_runtime_is_read_only():
    runtime_source = Path(batch_ro_runtime.__file__).read_text(encoding="utf-8")
    build_source = Path("tools/materialize_batch_ro_build.py").read_text(encoding="utf-8")
    payload_marker = Path("deploy/batch_ro_alpha/payload.sha256").read_text(encoding="ascii").strip()

    assert payload_marker == EXPECTED_ALPHA_PAYLOAD_SHA
    assert batch_ro_runtime.UI_SCRIPT == "/static/addons/batch_ro/batch_ro_addon.js"

    # The old Alpha integration contract performed payload extraction and UI
    # rewriting inside WSGI startup.  Those responsibilities must remain absent
    # from normal runtime registration after the immutable-runtime correction.
    for forbidden in (
        "materialize_batch_ro_files",
        "_validated_payload_bytes",
        "_patch_batch_ro_ui_host_probe",
        "tarfile",
        "base64",
        "extractall(",
        ".write_text(",
        ".write_bytes(",
        ".mkdir(",
    ):
        assert forbidden not in runtime_source, forbidden

    # Legacy compact-payload handling remains available only as an explicit
    # release-preparation operation before staging/Gunicorn startup.
    assert "materialize_legacy_payload" in build_source
    assert "--from-legacy-payload" in build_source
    assert "_OLD_HOST_PROBE" in build_source
    assert "_NEW_HOST_PROBE" in build_source
    assert "Legacy Batch RO payload SHA-256 mismatch" in build_source
