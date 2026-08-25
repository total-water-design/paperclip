# Total Economic Design — Foundation Audit and Canonical Cost Schema Milestone

Date: 2026-08-23  
Repository: `total-water-design/total-water-design-suite`  
Branch: `app/total-water-economics`  
Starting branch SHA: `f4fa44fa29e93e1fa262a7f3bd9b81543736e38f`

## Purpose

This milestone follows the Total Economic Design development order by auditing the existing economic calculations first, then establishing the canonical project-cost object, formal Cost Breakdown Structure (CBS), and provenance rules before expanding project-finance functionality.

No deployment, merge to `alpha`, merge to `main`, or AWS change is part of this milestone.

## Existing implementation audited

### `economics.py`

The file contains two intentionally separate paths:

1. the legacy Total RO Design ERD economic comparison; and
2. dispatch to the project-level Total Economic Design engine when `model=total_economic_design`.

The legacy path remains a technology comparison driven by an entered baseline installed CAPEX rate, workbook-derived allocation fractions, selected turbo savings assumptions, energy cost, annualization, LCOW and NPV. It is not a general project estimate and should remain isolated from the canonical Total Economic Design cost model.

### `economic_summary_contract.py`

The current `twds.economic_summary` v1.0 handoff already provides useful migration behavior:

- application/source lineage;
- scope keys and overlap warnings;
- CAPEX bucket normalization;
- OPEX category normalization;
- native/reporting currency metadata;
- explicit rejection of silent cross-currency aggregation while the shared FX service is not active;
- duplicate source/item protection.

This is the correct architectural direction: specialist applications own engineering and scope economics; Total Economic Design owns project-level aggregation and economic consequences.

### `economic_aggregator.py`

The aggregator combines one or more specialist summaries, appends local project cost items, then passes the assembled estimate to the project-level engine. Specialist OPEX is preserved as annual source OPEX and is not recalculated from plant capacity.

### `total_economic_design.py`

The current project-level engine already distinguishes:

- Purchased Equipment;
- Direct Installation;
- Construction Indirects;
- Engineering / Procurement / PM;
- Owner Costs;
- Contingency;
- Escalation;
- Financing / IDC;
- Working Capital.

It also distinguishes Total Direct Cost, Total Installed Cost, Project Cost Before Contingency, Total Project Cost, and Total Capital Requirement.

The engine includes:

- explicit allowance generation;
- source-quality scoring;
- a Suite-defined estimate-maturity heuristic;
- annual OPEX and LCOW screening;
- lifecycle NPV screening;
- simple debt/equity and DSCR screening;
- a required-tariff calculation for target DSCR;
- a one-step prior-estimate reconciliation field.

## Main audit findings

### 1. Canonical cost object was not yet sufficiently explicit

The existing `CostItem` contains the minimum fields needed for calculations, but not enough metadata for a defensible estimate audit trail. In particular, it does not formally encode:

- schema identity/version;
- formal CBS system/code;
- native versus reporting cost basis;
- FX provenance;
- source document identity;
- quotation number;
- price/base date;
- cost location;
- escalation-index metadata;
- source application/project/scenario/calculation lineage;
- estimate/revision context;
- source-specific provenance completeness.

This milestone addresses that gap with `economic_cost_schema.py`.

### 2. Cost taxonomy is duplicated

Cost bucket and source-quality definitions currently exist in more than one module. The new canonical schema is intended to become the single shared definition in a later integration step. This milestone does not prematurely rewrite the validated calculation modules; that migration should be made under regression tests.

### 3. Estimate revision architecture is not yet a revision ledger

The existing reconciliation object accepts one prior Total Project Cost and a text change summary. It does not yet persist immutable estimate snapshots or item-level movement categories. A later milestone should introduce an estimate revision object/ledger so E01, E02, E03, etc. can be reconciled without overwriting historical basis.

### 4. Escalation is not schedule-linked yet

Current escalation is an explicit percentage allowance. This is acceptable for early conceptual work only. The target architecture should use base/price date, cost index/source, execution period and spend curve before financing-grade use.

### 5. IDC is not draw-schedule based yet

Current financing/IDC can be entered as an allowance and the finance screen uses level annual debt service. It does not yet calculate IDC from construction spending and debt draw timing.

### 6. Project-finance model is intentionally preliminary

Current debt/equity, DSCR and required tariff calculations are screening tools. They do not yet include full construction-period debt draws, fees, grace periods, amortization variants, taxes, depreciation, reserves, refinancing, project IRR, equity IRR or LLCR.

### 7. Estimate-class logic requires a separate validation milestone

The current maturity algorithm correctly states that its weights and thresholds are Suite-defined rather than AACE-prescribed. That distinction must remain customer-visible.

Before tightening Class 5 → Class 1 gates, the implementation should map the Suite deliverables to the applicable AACE project-definition deliverable maturity guidance and validate industry context. It should not equate estimate class, accuracy, contingency and project risk.

## Canonical cost schema introduced

`economic_cost_schema.py` defines:

- schema: `twds.cost_item`
- version: `1.0`
- default CBS: `TWDS-CBS-1.0`
- explicit top-level cost families `1000` through `9000`
- owner/EPC custom CBS support through a separate `cbs_system`
- native and reporting currency fields
- explicit FX rate/source requirement for cross-currency conversion
- source quality and source-type aliases
- source-specific provenance requirements
- project/application/estimate lineage
- price/base-date and escalation-index metadata
- provenance completeness score and warnings
- duplicate item-ID validation

The TWDS CBS codes are Suite conventions. They are not represented as AACE or DBIA codes.

## Reference validation

Reference check performed on 2026-08-23 against current official sources.

### AACE International

Official AACE material currently surfaces:

`Recommended Practice 18R-97 — Cost Estimate Classification System — As Applied in Engineering, Procurement, and Construction for the Process Industries`, revision August 7, 2020.

The official material states that classification is based on maturity/quality of project-definition deliverables and that estimate accuracy is influenced by additional variables and risks. The application must therefore continue to separate estimate class from accuracy and risk.

Official source:
`https://web.aacei.org/docs/default-source/toc/toc_18r-97.pdf`

### DBIA

DBIA's current Design-Build Done Right® resources include the 2023 Universal Best Practices and a Progressive Design-Build Best Practices resource released in 2026. Current DBIA descriptions emphasize owner readiness, qualifications-focused procurement, phased contracting, and transparent cost development/validation.

Official sources:
`https://dbia.org/best-practices/`
`https://dbia.org/blog/new-pdb-best-practices-now-available-free-in-the-dbia-bookstore/`

No copyrighted standard or primer text is copied into the software.

## Validation performed for this milestone

Local static/runtime validation of the new schema:

- Python compilation: pass
- canonical CBS assignment: pass
- source-specific provenance assessment: pass
- native/reporting currency identity conversion: pass
- explicit cross-currency FX guard: pass
- FX source requirement: pass
- source lineage preservation: pass
- estimate context preservation: pass
- custom owner CBS support: pass
- TWDS CBS family validation: pass
- duplicate item-ID rejection: pass

The dedicated GitHub Actions workflow is updated to compile the new module and run its regression tests on pushes to `app/total-water-economics`.

Hosted CI status must be checked after the final push; connector access to post-push check results may be limited.

## Next controlled development step

After this schema milestone is green, the next development step should integrate the canonical cost object into:

1. `economic_summary_contract.py`;
2. `economic_aggregator.py`;
3. `total_economic_design.py`;

while preserving legacy `economics.py` ERD behavior.

Then build the immutable estimate revision/snapshot architecture before schedule-linked escalation, risk/contingency, project finance, or BOOT tariff expansion.
