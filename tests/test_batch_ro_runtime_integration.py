from __future__ import annotations

from pathlib import Path

import batch_ro_runtime


def test_batch_ro_materialization_preserves_engine_and_patches_only_ui_probe():
    raw_before = batch_ro_runtime._validated_payload_bytes()
    engine_path = Path("addons/batch_ro/engine.py")
    batch_ro_runtime.materialize_batch_ro_files()
    raw_after = batch_ro_runtime._validated_payload_bytes()

    # The packaged specialist payload is immutable; the RO integration adapter
    # only changes the extracted browser shim.
    assert raw_after == raw_before
    assert engine_path.exists() and engine_path.stat().st_size > 0

    text = batch_ro_runtime.UI_SCRIPT_PATH.read_text(encoding="utf-8")
    assert batch_ro_runtime._OLD_HOST_PROBE not in text
    assert batch_ro_runtime._NEW_HOST_PROBE in text
    assert "typeof FEATURE_REGISTRY==='undefined'" in text
    assert "eval(name)" not in text
    assert "FEATURE_REGISTRY.batch_ro" in text
