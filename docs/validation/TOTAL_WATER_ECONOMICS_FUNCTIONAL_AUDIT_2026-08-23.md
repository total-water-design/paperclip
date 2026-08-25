# Total Water Economics — Functional Validation & Gap Audit

**Date:** 2026-08-23  
**Branch:** `app/total-water-economics`  
**Audited starting head:** `f4fa44fa29e93e1fa262a7f3bd9b81543736e38f`  
**Scope:** Current Total Water Economics cost aggregation, lifecycle economics, project-finance screening, Suite handoff contract, UI/project integration and readiness for future BOOT modeling.

## Executive assessment

The current application is a credible **project-cost aggregator + lifecycle-cost model + debt-service screening foundation**. It is not yet a full project-finance or BOOT model.

The strongest current capabilities are:

- canonical project CAPEX hierarchy;
- one/many specialist-application economic summary aggregation;
- project-level allowance ownership;
- annual specialist + project OPEX aggregation;
- capital annualization and simple lifecycle NPV / LCOW;
- source/provenance scoring;
- AACE-informed project-definition maturity heuristic;
- estimate-to-estimate reconciliation;
- simple debt/equity split, level debt service, DSCR and target-DSCR tariff screening;
- common Suite UI/UX shell and lineage presentation;
- forward-compatible economic-summary currency metadata.

The largest missing layer is a **time-phased cash-flow model**. Without annual/monthly construction and operating periods, the application cannot correctly model true IDC, debt draws, taxes, depreciation, cash waterfalls, equity returns, reserves, tariff indexation, BOOT concession economics or handback.

## Validation status

### Source-level validation completed

Reviewed:

- `total_economic_design.py`
- `economic_aggregator.py`
- `economic_summary_contract.py`
- `economics.py` dispatch compatibility
- `/api/economics` routing / entitlement boundary
- Suite project-storage compatibility
- Total Water Economics UI project/report behavior
- `tests/test_total_economic_design.py`
- `tests/test_economic_summary_contract.py`
- Total RO Design `twds.economic_summary v1.0` producer

### Arithmetic cross-check

The existing target-DSCR test logic was independently cross-checked. For the published test case:

- capital = 15,000,000
- debt fraction = 70%
- debt rate = 6%
- tenor = 20 years
- annual OPEX = 900,000
- capacity = 20,000 m3/day
- availability = 95%
- target DSCR = 1.30x

The level-debt-service calculation gives annual debt service of approximately 915,437.85 and a required tariff of approximately 0.30138 per m3. Reapplying that tariff returns DSCR = 1.30 exactly within floating-point precision.

### Hosted CI

The repository contains regression tests and the Total Economic Design CI workflow, but the connected GitHub status endpoint does not expose a push-triggered hosted run for the audited head. This audit therefore does **not** claim a remotely proven CI pass.

## What is working now

### 1. CAPEX hierarchy — GOOD FOUNDATION

Current hierarchy:

1. Purchased Equipment
2. Direct Installation
3. Total Direct Cost
4. Construction Indirects
5. Total Installed Cost (TIC)
6. Engineering / Procurement / PM
7. Owner Costs
8. Project Cost Before Contingency
9. Contingency
10. Escalation
11. Total Project Cost
12. Financing / IDC
13. Working Capital
14. Total Capital Requirement

This creates a useful separation between process-scope direct cost, project-wide cost and funding-related additions.

### 2. Specialist application aggregation — WORKING

`economic_aggregator.py` accepts zero, one or many `twds.economic_summary` sources, prepends their CAPEX to project-level cost items and adds source annual OPEX exactly once to the lifecycle model.

Current integration modes:

- `manual_project_estimate`
- `single_application`
- `combined_applications`

This supports the intended architecture where a user can economically evaluate one specialist application or combine several applications.

### 3. OPEX aggregation — WORKING AT ANNUAL SUMMARY LEVEL

The common categories are:

- fixed
- variable
- energy
- chemicals
- labor
- maintenance
- replacement
- disposal
- other

Specialist annual OPEX is kept separately in the result and is added once to project-level OPEX.

### 4. Lifecycle screening — WORKING, SIMPLE

Current lifecycle logic calculates:

- annual production;
- annual fixed / variable / energy / other OPEX;
- capital recovery factor;
- annualized capital;
- lifecycle NPV using a level annual OPEX annuity;
- LCOW.

This is appropriate as an early screening model.

### 5. Finance screening — MATHEMATICALLY CONSISTENT, LIMITED SCOPE

Current finance model calculates:

- debt fraction;
- debt amount;
- equity amount;
- level annual debt service;
- annual revenue from a single tariff;
- CFADS = revenue - annual OPEX;
- DSCR;
- tariff required to achieve target DSCR.

This should continue to be described as a **finance / DSCR screen**, not a BOOT tariff model.

### 6. Estimate maturity / provenance — GOOD FOUNDATION

The application distinguishes source quality and calculates a transparent Suite-defined estimate maturity score. It explicitly states that the maturity weights / thresholds are not AACE-prescribed accuracy ranges.

### 7. Total RO Design producer — AVAILABLE

Total RO Design currently produces `twds.economic_summary v1.0`, including RO-scope CAPEX/OPEX and provenance. RO is therefore the first real specialist economic producer.

## Critical / high-priority technical gaps

### CRITICAL 1 — Manual project cost items can currently bypass the multi-currency guard

`economic_summary_contract.py` safely rejects unconverted specialist-source currencies that differ from the project reporting currency.

However, `total_economic_design.py::CostItem.from_payload()` accepts a per-item `currency`, while `_cost_hierarchy()` simply sums `amount` values. There is currently no equivalent FX guard or conversion for locally entered project `cost_items`.

Therefore an API payload can contain, for example:

- USD project
- USD 1,000,000 item
- EUR 1,000,000 item

and the current project engine can numerically add the two amounts without FX conversion.

The current UI does not expose per-row currency, which reduces immediate customer risk, but the engine/API contract must be fixed before native multi-currency project costing is enabled.

**Required direction:** project cost items need the same native/reporting currency + FX snapshot model as specialist summary items. Until the shared FX service exists, non-reporting-currency local items must be rejected rather than summed.

### CRITICAL 2 — Specialist summaries can still contain project-wide CAPEX buckets

The common contract recognizes all CAPEX buckets, including:

- construction indirect
- engineering/procurement
- owner cost
- contingency
- escalation
- financing
- working capital

This is useful for migration, but specialist applications should normally own only their defined process scope.

`total_economic_design.py::_build_cost_items()` suppresses a percentage allowance whenever an explicit cost exists in that bucket. Therefore, if one specialist summary accidentally imports a contingency amount, it can suppress the intended project-level contingency calculation for the combined project.

**Required direction:** enforce economic ownership. Specialist-source summaries should be restricted to approved scope buckets (normally equipment purchase + direct installation, with any exceptions explicitly identified), or project-level imported costs must be tagged so they do not globally suppress the project allowance incorrectly.

### HIGH 3 — Detailed OPEX items are preserved but are not an authoritative aggregation source

The contract preserves `details.opex_items`, but `_opex()` primarily aggregates the annual category summary.

If a future specialist producer sends detailed OPEX items but omits the annual category totals, those item amounts are not currently summed into the project OPEX result.

There is also no reconciliation test comparing:

`sum(opex_items by category)`

against:

`opex.annual / opex_annual`.

**Required direction:** derive category totals from detailed items when present or validate annual totals against them, with an explicit authority rule.

### HIGH 4 — Duplicate OPEX item IDs are not currently enforced across summaries

Duplicate CAPEX item IDs are checked during aggregation. OPEX item IDs are preserved but are not included in the same global uniqueness check.

**Required direction:** apply item-ID uniqueness and duplicate-source protection consistently to both CAPEX and OPEX detail items.

### HIGH 5 — `system_integration` identifier is inconsistent with the common contract

The Suite catalog/UI uses `system_integration` for System Integration & Optimization. The current economic-summary `APPLICATION_NAMES` does not include `system_integration`; an incoming summary using that application ID can normalize to `other`.

**Required direction:** align the controlled application ID vocabulary with Suite Core/catalog before System Integration becomes an economic producer.

### HIGH 6 — Economics API is still inside the RO entitlement architecture

`/api/economics` calls `_require_feature('economics')`, and the current global API gate treats most `/api/*` requests as RO requests. The `economics` feature is also defined in the Total RO Design tier registry.

This is acceptable only as a temporary administrator-development bridge.

**Required direction:** Total Water Economics needs product-specific authorization/entitlement routing rather than requiring RO Gold/preview semantics.

### HIGH 7 — Project Save is not complete for Economics

The Suite project model already defines the `TWECO` visible-ID prefix. However, the shared project snapshot validator currently does not accept `Total Water Economics Project`.

The UI correctly fails safely and retains Snapshot Export instead of masquerading as an RO project.

**Required Suite Core dependency:** add the Economics project format to the common project snapshot validator and default project naming.

## Project-finance / BOOT gaps

The following are **not calculation defects**; they are not implemented yet.

### 1. No time-phased construction cash flow

Missing:

- construction months/years;
- engineering/procurement/construction spend curve;
- milestone payments;
- commissioning/start-up period;
- COD;
- capitalized pre-COD operating costs where applicable.

This is the key prerequisite for true project finance.

### 2. IDC is not calculated from debt draws

Current financing/IDC can be an explicit amount or percentage allowance. It is not calculated from:

- debt draw timing;
- opening debt balance;
- periodic interest;
- capitalized interest;
- commitment fees;
- unused debt fees;
- financing fees.

### 3. No debt draw / repayment schedule

Missing:

- construction debt draws;
- equity-first / pari-passu / target gearing logic;
- grace period;
- repayment start date;
- amortization schedule;
- annuity / straight-line / sculpted debt;
- bullet / balloon repayments;
- refinancing;
- mandatory prepayment / cash sweep.

### 4. No debt-service reserves or lender accounts

Missing:

- DSRA;
- minimum cash;
- maintenance reserve;
- major-maintenance reserve;
- reserve funding / releases;
- letters of credit or guarantee costs.

### 5. No period-by-period CFADS waterfall

Current CFADS is a steady-state annual expression.

A project-finance model needs period cash flow containing at least:

- revenue;
- operating expenses;
- taxes or tax-adjusted CFADS policy;
- working-capital changes;
- reserve movements;
- debt service;
- distributions.

### 6. No taxes / depreciation

Missing:

- depreciation method and asset classes;
- taxable income;
- interest deductibility;
- corporate tax;
- tax-loss carryforward;
- withholding taxes where relevant;
- tax holidays / incentives;
- deferred tax treatment if required by model purpose.

### 7. No project IRR / equity IRR / NPV model

Current finance output is DSCR-focused.

Missing:

- unlevered project cash flow;
- project IRR;
- project NPV;
- levered equity cash flow;
- equity IRR;
- equity NPV;
- dividend/distribution logic;
- sponsor return requirements.

### 8. No LLCR / PLCR

For lender-style project-finance analysis, missing:

- Loan Life Coverage Ratio;
- Project Life Coverage Ratio;
- minimum / average DSCR across periods;
- covenant tests.

### 9. No WACC / explicit cost-of-capital structure

The lifecycle discount rate is a user input. It is not derived from debt/equity cost, gearing, taxes or target returns.

### 10. Tariff is a DSCR floor, not a BOOT tariff

The current required tariff solves:

`Annual OPEX + Target DSCR × Level Debt Service`

over annual product volume.

It does **not** yet solve for:

- target equity IRR;
- project IRR;
- taxes;
- concession length;
- inflation / indexation;
- variable production;
- reserve requirements;
- handback obligations;
- development fees;
- sponsor costs;
- availability penalties;
- take-or-pay / minimum offtake;
- step tariffs.

The UI/output should continue to call this a required tariff for target DSCR or finance screen, not a bankable BOOT tariff.

### 11. No revenue/indexation model

Missing:

- base tariff date;
- CPI/PPI escalation;
- electricity / chemical pass-through;
- FX indexation;
- local/foreign tariff components;
- minimum contracted volume;
- capacity payment + volumetric payment structures;
- availability adjustment;
- penalties / liquidated damages;
- bonuses.

### 12. No BOOT concession / transfer mechanics

Missing:

- development period;
- construction period;
- operating/concession period;
- concession expiry;
- transfer / handback date;
- residual value;
- handback reserve / required rehabilitation CAPEX;
- asset transfer assumptions.

### 13. No replacement / major maintenance schedule

Current replacement economics are annualized OPEX amounts. A finance model needs time-specific:

- membrane replacement;
- major pump/compressor overhaul;
- media replacement;
- membrane/MBR/ZLD replacement cycles;
- major maintenance CAPEX;
- reserve funding.

### 14. No working-capital cycle

Current working capital is a capital allowance. Missing:

- receivable days;
- payable days;
- inventory;
- operating cash minimum;
- initial funding;
- annual changes;
- release at concession end.

### 15. No sensitivity / scenario / Monte Carlo finance engine

Missing finance sensitivities such as:

- CAPEX +/- %;
- delay to COD;
- interest rate;
- debt gearing;
- production / availability;
- power price;
- chemical price;
- OPEX inflation;
- FX;
- tariff / indexation;
- replacement cycles;
- concession duration.

Also missing probabilistic risk / Monte Carlo for cost and finance outcomes.

## Lifecycle metric decision required

Current LCOW annualizes **Total Project Cost**, while the finance model sizes debt/equity from **Total Capital Requirement** (which also includes Financing/IDC and Working Capital).

This is not automatically wrong. Economic LCOW often should avoid double-counting financing costs if the discount rate already represents the cost of capital. However, the product needs explicit metric definitions so users can distinguish:

- economic LCOW / lifecycle unit cost;
- fully loaded cash requirement;
- finance tariff / bankability tariff;
- customer water price.

Do not collapse these into one metric.

## Suite integration gaps

### Producer availability

Current confirmed producer:

- Total RO Design — `twds.economic_summary v1.0`

No equivalent producer module was found at the obvious branch locations for:

- Total Bio Design
- Total Pretreatment Design
- Total ZLD Design

Therefore the aggregator contract is ahead of the complete producer ecosystem. Manual rows / JSON import remain necessary for those applications until their specialist branches implement the producer.

### Automatic project linkage

Total Water Economics can consume `source_summaries` and import JSON, but it does not yet automatically query the Suite Project Library for linked specialist economic summaries by common project family / selected revision.

Future desired behavior:

1. choose/open a TWECO project;
2. identify the shared Suite project family;
3. show available specialist project revisions/scenarios;
4. select or refresh the economic summary from each source;
5. retain immutable lineage to the exact source revision;
6. warn when a newer specialist revision exists;
7. require an explicit refresh rather than silently changing a saved estimate.

## Multi-currency future architecture

The current contract correctly preserves the intended direction:

- multiple native currencies may exist across the Suite;
- one reporting currency is selected for the economic model;
- no silent 1:1 conversion;
- future shared FX service;
- saved estimate FX snapshots for reproducibility.

Still required:

- shared FX service;
- online rate source integration;
- four-times-daily current-rate refresh/cache;
- historical/saved rate snapshots;
- explicit conversion methodology (direct/cross rates);
- stale-rate handling;
- native-currency project cost item support;
- FX sensitivity;
- optional tariff / debt currency mismatch analysis.

## Reporting gaps

Current Economics report behavior is a print-optimized Results view plus JSON Snapshot Export.

Still desirable:

- dedicated Economics report provider in the Suite report framework;
- estimate basis / assumptions schedule;
- source/provenance appendix;
- application contribution table;
- lifecycle cash-flow chart;
- financing summary;
- sensitivity tornado / scenario table;
- estimate reconciliation waterfall;
- BOOT cash-flow / debt-service schedules once implemented;
- immutable report snapshot tied to saved TWECO project revision.

## Recommended priority

### P0 — Before wider reconciliation / beta reliance

1. Guard or convert currencies for manual/project-level cost items.
2. Enforce specialist-vs-project CAPEX ownership so source contingency/financing cannot suppress project allowances accidentally.
3. Reconcile OPEX detail items with annual category totals and enforce OPEX item uniqueness.
4. Add `system_integration` to the common economic application vocabulary.
5. Move `/api/economics` out of RO entitlement semantics.
6. Enable `Total Water Economics Project` in Suite Core project persistence.
7. Obtain a proven hosted CI pass for the integrated branch.

### P1 — Next economics milestone

1. Automatic Project Library source-summary discovery/selection.
2. Complete Bio / Pretreatment / ZLD producer contracts.
3. Shared FX service and frozen FX snapshots.
4. Schedule-linked escalation.
5. Annual/periodic lifecycle cash-flow structure.
6. Explicit economic LCOW vs finance tariff metric definitions.
7. Dedicated Economics report provider.

### P2 — Project-finance foundation

1. Construction schedule and spend curve.
2. Debt/equity draw schedule.
3. True IDC and financing fees.
4. Operating-year cash flow.
5. Debt amortization options / sculpting.
6. Taxes and depreciation.
7. CFADS / DSCR series.
8. LLCR / PLCR.
9. Project/equity IRR and NPV.
10. Working-capital schedule and reserves.
11. Sensitivities.

### P3 — BOOT capability

1. Concession timeline / COD / expiry.
2. Tariff and indexation mechanisms.
3. Take-or-pay / capacity payment / availability structures.
4. Sponsor development costs and fees.
5. Major maintenance and replacement schedules.
6. Handback reserve / residual / transfer logic.
7. Cash waterfall and distribution restrictions.
8. Scenario / downside cases and covenant compliance.
9. BOOT tariff solver targeting lender constraints + sponsor returns.
10. Probabilistic risk analysis where appropriate.

## Overall conclusion

**Current status:** technically useful and architecturally promising, but not yet a bankable BOOT/project-finance engine.

The current application should be described as:

> Project-level CAPEX/OPEX aggregation, estimate maturity, lifecycle-cost analysis and preliminary finance screening.

It should not yet be described as:

> Full project-finance, BOOT tariff or bankability modeling.

A detailed BOOT spreadsheet is therefore highly valuable as the next reference artifact. The main purpose should be to map its period-by-period cash-flow, debt, tax, tariff, reserve, IRR and concession mechanics into a transparent engine architecture—not to copy spreadsheet cells or introduce unexplained fudge factors.
