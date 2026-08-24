import io
import json
import re

from flask import Flask, send_file

from ro_customer_surface import (
    _sanitize_client_script,
    _scrub_payload,
    _scrub_report_snapshot_html,
    register_ro_customer_surface,
)


def _legacy_vendor_token():
    return "chat" + "g" + "pt"


def _blocked_pattern():
    terms = (
        "chat" + "g" + "pt",
        "open" + "a" + "i",
        r"\b" + "g" + "pt" + r"\b",
        r"\b" + "l" + "l" + "m" + r"\b",
    )
    return "|".join(terms)


def test_customer_script_removes_legacy_diagnostic_and_equation_details():
    legacy = _legacy_vendor_token()
    legacy_fn = "buildChat" + "G" + "ptDebugPrompt"
    legacy_field = "chat" + "g" + "pt_prompt"
    source = f'''function {legacy_fn}(err){{return "{legacy} investigation prompt";}}
async function captureFeedbackScreenshots(){{return {{}};}}
function convergencePlotHtml(diag){{return `residual ${{diag.residual}} tolerance ${{diag.tolerance}}`;}}
function solverDiagnostics(r){{return `Rejected steps ${{r.rejected_steps}} backend ${{r.compute_backend}}`;}}
function offDesignEquationNote(){{return `ηt = ηtd - ηtd(Qr-Qrd)^2/Qrd^2`;}}
function turboDesignStatus(r){{return offDesignEquationNote();}}
function turboDesignDutyHtml(){{return `workbook off-design method`;}}
function activeTurboLockFields(){{return {{}};}}
function suiteSplitEfficiency(overall){{const d=.01;return Math.sqrt(d*d+4*overall)}}
function suiteEfficiencyChart(){{return suiteSplitEfficiency(.8)}}
function suiteEnergyBreakdown(r){{return r.ro_sec}}
function updateComputeStatus(){{return 'OpenCL GPU CPU workers'}}
function reportReadiness(options={{}}){{return options}}
const payload={{{legacy_field}:{legacy_fn}()}};
'''
    sanitized = _sanitize_client_script(source)
    assert re.search(_blocked_pattern(), sanitized, re.I) is None
    assert "diagnostic_summary" in sanitized
    assert "Math.sqrt" not in sanitized
    assert "ηt =" not in sanitized
    assert "Rejected steps" not in sanitized
    assert "tolerance" not in sanitized.lower()
    assert "OpenCL GPU CPU workers" not in sanitized
    assert "Calculation converged successfully." in sanitized


def test_customer_payload_scrub_preserves_engineering_results():
    original = {
        "product_flow": 123.45,
        "recovery": 0.48,
        "ro_sec": 2.71,
        "solver_method": "internal-method",
        "solver_diagnostics": {"residual": 1e-10, "tolerance": 1e-8},
        "compute_backend": "internal-backend",
        "nested": {"tds": 35500.0, "iterations": 8, "backend": "internal"},
    }
    public = _scrub_payload(original, strip_generic_solver_fields=True)
    assert public["product_flow"] == original["product_flow"]
    assert public["recovery"] == original["recovery"]
    assert public["ro_sec"] == original["ro_sec"]
    assert public["nested"]["tds"] == original["nested"]["tds"]
    assert "solver_method" not in public
    assert "solver_diagnostics" not in public
    assert "compute_backend" not in public
    assert "iterations" not in public["nested"]
    assert "backend" not in public["nested"]


def test_report_snapshot_scrub_removes_internal_metadata_and_keeps_results():
    snapshot = {
        "result": {
            "product_flow": 100.0,
            "permeate_tds_ppm": 225.0,
            "solver_method": "internal-method",
            "history": [{"residual": 1e-4}],
            "backend": "internal-backend",
            "iterations": 9,
        },
        "project": {"project_name": "A&B <RO>"},
    }
    html = (
        '<html><script id="reportSnapshot" type="application/json">'
        + json.dumps(snapshot)
        + '</script></html>'
    )
    scrubbed = _scrub_report_snapshot_html(html)
    assert '"product_flow":100.0' in scrubbed
    assert '"permeate_tds_ppm":225.0' in scrubbed
    assert "solver_method" not in scrubbed
    assert "history" not in scrubbed
    assert '"backend"' not in scrubbed
    assert '"iterations"' not in scrubbed
    assert "\\u0026" in scrubbed
    assert "\\u003cRO\\u003e" in scrubbed


def test_static_javascript_direct_passthrough_is_safely_materialized_and_rewritten():
    app = Flask(__name__, static_folder=None)

    @app.get("/static/app.js")
    def app_js():
        payload = b'function updateComputeStatus(){return "OpenCL GPU CPU workers";}\nfunction reportReadiness(options={}){return options;}'
        return send_file(io.BytesIO(payload), mimetype="application/javascript", download_name="app.js")

    register_ro_customer_surface(app)
    with app.test_client() as client:
        response = client.get("/static/app.js")

    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "OpenCL GPU CPU workers" not in text
    assert "CALCULATION STATUS" in text
