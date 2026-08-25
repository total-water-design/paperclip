# Total Water Economics — Application UI/UX Contract v1.0 Validation

## Scope

Application: **Total Water Economics**  
Working branch: `app/total-water-economics`  
Suite Core UI/UX milestone: `12d18dadced75f3fb8acefc1faa9e93a067a773b`  
Contract: **Total Water Design Suite Application UI/UX Contract v1.0**

This milestone migrates the existing economics application onto the Suite Core application shell while preserving the economic calculation and aggregation engines.

## Shared components consumed

The following files are copied at their canonical shared paths and are byte-identical to the Suite Core milestone:

- `templates/shared/application_shell.html` — blob `8e536c4078b81d934c434c96cee35d02c990750c`
- `templates/shared/suite_components.html` — blob `1b7fdcece49c5e07e0dc5f935bf50853047dd47e`
- `static/suite_ui_tokens.css` — blob `f825da7c17f3712c88903be934dcc4965d2c2f7d`
- `static/suite_application_shell.css` — blob `6f5daa590f9cb2169a03e28d4fe640be00ef1f3d`
- `static/suite_application_shell.js` — blob `161e8422137b6e418521e1b6fce486ab337db42c`

No Economics-specific copy or fork of the common shell is retained.

## Economics-specific UI retained

The application retains its own workflow and economic personality:

- Application Summaries / Suite economic handoffs
- Estimate Overview
- Estimate Basis and source provenance
- Project Cost Build-Up
- AACE-informed estimate maturity
- Estimate Reconciliation
- Project OPEX Adders
- Project Finance
- Progressive Design-Build estimate development
- Total project cost / TIC / total capital requirement hierarchy
- lifecycle and LCOW results
- DSCR and required tariff screening
- economic-summary JSON import and project snapshot export

The application does not introduce RO stages, Bio reactors, crystallizers, or other specialist process-navigation concepts.

## Contract hierarchy

The rendered application uses:

`Suite → Total Water Economics → Project → Workspace → Inputs / Results`

Common controls are supplied by the shared shell:

- Suite return
- application identity and endorsement
- account menu
- System / Light / Dark appearance control
- Project Bar
- workspace navigation
- standardized calculation state control
- shared guidance hierarchy

## Approved identity

- Name: `Total Water Economics`
- Short name: `Water Economics`
- Accent: `#985A00`
- Icon: `branding/suite/total_water_economics_icon_512.png`
- Endorsement: `Part of the Total Water Design Suite`

The catalog remains `in_development`; this UI milestone does not release the application to customers.

## Results architecture

The Results workspace follows the Economics adaptation of the Suite contract:

1. **System Summary** — TPC, TIC, capital requirement, annual OPEX, lifecycle cost, LCOW, estimate class and required tariff.
2. **Process / Alternative Summary** — contribution by connected application/project/scenario.
3. **Detailed Results** — cost hierarchy and source-quality basis.
4. **Warnings & Constraints** — integration/methodology warnings and estimate-definition gaps.
5. **Energy / Economics** — annualized CAPEX, annualized cost, DSCR, annual production, OPEX contribution and finance assumptions.

## Data origin and lineage

The UI distinguishes:

- User input
- Inherited Suite values
- Database / reference values
- Calculated outputs
- Overridden inherited values

Imported `twds.economic_summary` values remain read-only until the user explicitly chooses **Override**. Overrides retain the original summary identifier in `source.override_of_summary_id`. Handoff cards preserve source application, project, project revision, scenario, calculation revision and summary lineage where supplied.

## Calculation interaction

Primary economic calculation sequence:

`Inputs → Validate → Calculate → Results → Report`

The UI uses Suite calculation states `validating`, `calculating`, `failed`, and `idle`. It does **not** use a fake `converging` state for the normal economics calculation.

## Calculation-engine preservation

Compared with the pre-migration Economics head `1370b00beac92c3f52cc2e67d494d510a32a6a97`, this UI migration does not modify:

- `total_economic_design.py`
- `economic_aggregator.py`
- `economic_summary_contract.py`
- `economics.py`

Therefore the economic equations, CAPEX/OPEX hierarchy, lifecycle calculations, estimate-maturity logic, aggregation behavior, finance screening, legacy RO economic dispatch and multi-currency guard/metadata are unchanged by this UI milestone.

## Project controls

The shared Project Bar is wired to the existing Suite project API and `economics` product ID. The shared project model already defines the `TWECO` visible-ID prefix.

### Suite Core dependency

The current shared `_project_snapshot_payload` validator does not yet include `Total Water Economics Project` in its accepted project-format set. This chat does not modify Suite Core/auth infrastructure. Until Suite Core adds that format:

- Project Library browsing is wired through the common API.
- New Economics project save attempts fail safely and show a Review message.
- The application does not masquerade as an RO/Bio/ZLD project to bypass the validator.
- `Export Snapshot` remains available to preserve the complete economics assessment.

Requested Suite Core follow-up: add `Total Water Economics Project` to the shared project snapshot contract and provide the corresponding generic default project name. No Economics-private project database should be introduced.

## Report behavior

The common **Report** control switches to the Results workspace and invokes a print-optimized report view. `Export Snapshot` remains available for the full JSON input/result state. The UI migration does not introduce a second calculation/report engine.

## Responsive and keyboard design validation

Static contract validation confirms:

- shared shell responsive breakpoints at 1050, 760 and 440 px are retained unchanged;
- Economics-specific grids collapse from multi-column to single-column layouts at narrow widths;
- economic tables remain horizontally scrollable;
- project/account menus use native `details` controls;
- Project Library uses the native `dialog` element;
- workspace and project controls are real buttons with keyboard focus styling from Suite Core;
- shared focus-visible behavior is preserved;
- print media removes application chrome and prints the Results workspace.

No browser screenshot runner is available through the connected GitHub environment, so this milestone does not claim pixel-level screenshot validation.

## Automated validation

CI workflow: `.github/workflows/total-economic-design-ci.yml`

Checks configured:

- Python compile of existing economic engines
- `test_total_economic_design.py`
- `test_economic_summary_contract.py`
- `test_water_economics_ui_ux.py`
- `node --check static/economics.js`

The GitHub connector used by this development session does not expose push-triggered Actions check results through its available status endpoint. Hosted CI must therefore be confirmed by Reconciliation/Actions before promotion. Absence of a connector status is not treated as a pass.

## Reconciliation risks

1. Shared component files should reconcile against Suite Core by blob identity, not be independently edited from the Economics branch.
2. `suite_catalog.py` may conflict with other catalog/status work; retain the approved `Total Water Economics` identity/accent while reconciling newer product-release state.
3. `templates/economics_suite.html`, `static/economics.js`, and Economics CSS are specialist-owned and should be preserved as the app adaptation layer.
4. The temporary `/api/economics` RO-entitlement compatibility bridge remains outside this UI milestone and should not become the permanent Economics authorization architecture.
5. Suite Core must add the Economics project snapshot format before Project Save is considered complete.
6. The future shared FX service remains a separate dependency; this UI preserves one reporting currency while the economic contract retains native-currency/FX metadata and blocks silent cross-currency conversion.

## Release boundary

This milestone is ready for reconciliation review only. It does not merge to `alpha`, does not modify `main`, and does not deploy AWS.
