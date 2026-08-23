from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Source" / "web"
html = (WEB / "index.html").read_text(encoding="utf-8")
adapter = (WEB / "suite_contract_adapter.js").read_text(encoding="utf-8")
css = (WEB / "suite_contract_v1.css").read_text(encoding="utf-8")
app = (WEB / "app.js").read_text(encoding="utf-8")
combined = "\n".join((html, adapter, css, app))

assert "Total Water Design Suite" in html
assert "Total Bio Design" in html
assert "Part of the Total Water Design Suite" in html
assert "#0E7A55" in combined
for token in ("New Project", "Project Library", "Save", "Save As", "Revision", "Duplicate", "Handoff", "Report"):
    assert token in html, token
for state in ("Calculate", "Validating…", "Calculating…", "Converging…", "Converged", "Needs attention", "Calculation failed", "Recalculate"):
    assert state in adapter, state
for severity in ("Information", "Review", "Warning", "Calculation error", "Critical/system error"):
    assert severity in adapter, severity
for origin in ("User Input", "Calculated", "Database", "Constraint"):
    assert origin in combined, origin
for section in ("System Summary", "Process / Unit Summary", "Detailed Results", "Warnings & Constraints", "Energy"):
    assert section.lower() in combined.lower(), section
for theme in ("system", "light", "dark"):
    assert f'value="{theme}"' in html
for forbidden in ("Isobaric Chamber", "DWEER", "BiTurbo", "Hydraulic Envelope"):
    assert forbidden not in html, forbidden
for shared in ("/static/suite_ui_tokens.css", "/static/suite_application_shell.css", "/static/suite_application_shell.js"):
    assert shared in adapter, shared
assert "aria-live=\"polite\"" in html
assert "data-twds-calculate-state" in html
assert "beforeunload" in adapter
assert '<dialog id="handoffDialog"' in html
assert "maxIterations:400,maxOuterIterations:35,tolerance:1e-5,outerTolerance:1e-4,relaxation:0.8" in app
print("Total Bio Design UI/UX Contract v1.0 static validation: PASS")
