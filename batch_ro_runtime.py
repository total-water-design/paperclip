"""Runtime registration for the Total RO Design Batch RO specialist add-on.

The validated Batch RO engine/UI is stored as a compact payload on the dedicated
feature branch. At application startup this module materializes only Batch-RO-
owned files, registers the ``batch_ro`` calculation mode, and injects its UI
loader only into the Total RO Design ``/ro`` workspace.

No conventional RO calculation, entitlement, database, or Suite shell file is
modified by payload extraction.  A narrow RO-owned compatibility patch is
applied only to the materialized Batch UI script so its host-hook probe works
with the current Total RO Design lexical bindings.  The specialist calculation
engine and payload digest remain authoritative and unchanged.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
PAYLOAD_DIR = ROOT / "deploy" / "batch_ro_alpha"
PAYLOAD_PARTS = (
    "payload.segment01",
    "payload.segment02",
    "payload.part02",
    "payload.part03",
)
EXPECTED_MEMBERS = {
    "addons/batch_ro/__init__.py",
    "addons/batch_ro/engine.py",
    "static/addons/batch_ro/batch_ro.svg",
    "static/addons/batch_ro/batch_ro_addon.js",
    "docs/BATCH_RO_ENGINEERING_BASIS.md",
    "tests/test_batch_ro_addon.py",
}
UI_SCRIPT = "/static/addons/batch_ro/batch_ro_addon.js"
UI_SCRIPT_PATH = ROOT / UI_SCRIPT.lstrip("/")

_OLD_HOST_PROBE = """const required=['FEATURE_REGISTRY','MODE_FEATURE','WORKSPACE_META','defaults','sections','processModeConfigured','renderFields','changeMode','processPerformanceBody'];
    const missing=required.filter(name=>{try{return typeof eval(name)==='undefined'}catch(_){return true}});
    if(missing.length){console.error('Batch RO add-on not activated; incompatible Total RO Design UI hooks:',missing);return;}"""

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
    if(missing.length){console.error('Batch RO add-on not activated; incompatible Total RO Design UI hooks:',missing);return;}"""


def _validated_payload_bytes() -> bytes:
    parts = [PAYLOAD_DIR / name for name in PAYLOAD_PARTS]
    missing = [p.name for p in parts if not p.is_file()]
    if missing:
        raise RuntimeError(f"Batch RO feature payload is incomplete: missing {missing}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    raw = base64.b64decode(encoded, validate=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        names = set(tf.getnames())
        if names != EXPECTED_MEMBERS:
            raise RuntimeError(f"Batch RO feature payload member mismatch: {sorted(names ^ EXPECTED_MEMBERS)}")
        for member in tf.getmembers():
            target = (ROOT / member.name).resolve()
            if ROOT.resolve() not in target.parents:
                raise RuntimeError(f"Unsafe Batch RO payload path: {member.name}")
    return raw


def _patch_batch_ro_ui_host_probe() -> None:
    """Adapt the specialist UI probe to current RO cross-script lexical bindings.

    The specialist v0.1 UI used ``eval(name)`` inside an array callback to probe
    host symbols.  In current browsers that nested eval cannot reliably resolve
    the host script's top-level lexical bindings, so it falsely reports every
    Total RO Design hook as missing.  CCRO already uses direct ``typeof`` probes.
    Apply the same compatibility pattern here without changing Batch inputs,
    equations, API calls, result schema, or engineering behavior.
    """
    text = UI_SCRIPT_PATH.read_text(encoding="utf-8")
    if _NEW_HOST_PROBE in text:
        return
    if _OLD_HOST_PROBE not in text:
        raise RuntimeError(
            "Batch RO UI compatibility probe no longer matches the validated specialist payload; "
            "return this contract change to the Batch RO specialist owner before integration."
        )
    UI_SCRIPT_PATH.write_text(text.replace(_OLD_HOST_PROBE, _NEW_HOST_PROBE, 1), encoding="utf-8")


def materialize_batch_ro_files() -> None:
    """Extract the exact specialist payload, then apply the RO-owned UI adapter."""
    raw = _validated_payload_bytes()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
        tf.extractall(ROOT)
    _patch_batch_ro_ui_host_probe()


def register_batch_ro_runtime(app, calculations) -> None:
    """Register Batch RO and add its UI loader to Total RO Design."""
    materialize_batch_ro_files()
    from addons.batch_ro import register_batch_ro

    register_batch_ro(app, calculations)

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
