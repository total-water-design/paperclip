# Total Bio Design — Suite Application UI/UX Contract v1.0

Implementation branch: `app/total-bio-design`.

## Runtime boundary

Total Bio Design remains a separate loopback-only Go service with an embedded HTML/JavaScript/CSS frontend. Suite Core's shared Jinja macros cannot be imported directly by this runtime. In hosted Suite mode Bio therefore consumes the shared Suite Core CSS and JavaScript assets directly (`suite_ui_tokens.css`, `suite_application_shell.css`, `suite_application_shell.js`) and uses the same DOM/interaction vocabulary through a Bio-owned static adapter.

No Suite Core-owned files are modified by this implementation.

## Preserved engineering source

The following files were recovered byte-for-byte from the running Total Bio Design v0.2.3 service before the UI migration and are protected by SHA-256 regression checks:

- `Source/web/engine.js`
- `Source/web/process_network.js`
- `Source/web/compliance_advisor.js`
- `Source/web/model.json`
- `Source/web/unit_catalog.js`

The coupled process-network numerical settings remain exactly `maxIterations:400`, `maxOuterIterations:35`, `tolerance:1e-5`, `outerTolerance:1e-4`, `relaxation:0.8`.

## Canonical identity and typography

The Suite catalog is authoritative for Bio identity. The application uses the same canonical Bio artwork as the Suite landing page: `static/branding/suite/total_bio_design_icon_512.png`. A byte-identical local copy is packaged with the Bio frontend so the standalone Go runtime and hosted Suite presentation use the same icon.

The canonical Suite application font stack is `Inter, "Segoe UI", Arial, sans-serif`. Both the Bio legacy stylesheet and Suite-contract layer are aligned to this stack; engineering symbols intentionally retain their monospace treatment.

## Contract mapping

- Total Water Design Suite master identity and Suite return control.
- Total Bio Design application identity, canonical BIO icon and catalog accent `#0E7A55`.
- “Part of the Total Water Design Suite” endorsement.
- Suite → Application → Project → Workspace → Inputs / Results hierarchy.
- Standard project wording: New Project, Project Library, Save, Save As, Revision, Duplicate, Handoff and Report. Unsupported hosted Save As / Duplicate operations are visibly unavailable rather than being simulated incorrectly.
- Shared `twds-theme` system/light/dark preference.
- Common workflow: Inputs → Validate → Calculate → Converge → Results → Report.
- Customer calculation states: Calculate, Validating…, Calculating…, Converging…, Converged, Needs attention, Calculation failed and Recalculate.
- Common guidance vocabulary: Information, Review, Warning, Calculation error and Critical/system error.
- Input origins: User Input, Calculated, Database and Constraint.
- Bio results mapped to System Summary, Process / Unit Summary, Detailed Results, Warnings & Constraints and Energy where applicable.
- Existing Bio treatment-train, recycle, process mass-balance, residuals, sludge/dewatering, compliance, compact-report and Bio→RO handoff workflows retained.

## Suite Core dependency

A runtime-neutral shared shell/component package would eliminate the remaining static DOM duplication for non-Flask applications such as Total Bio Design. Until then, direct consumption of the shared CSS/JS plus this static adapter is the lowest-risk implementation.
