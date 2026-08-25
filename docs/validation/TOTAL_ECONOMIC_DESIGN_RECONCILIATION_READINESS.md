# Total Economic Design — Reconciliation Readiness Audit

Date: 2026-08-22

## Decision

**GO WITH CONDITIONS for reconciliation into `integration/alpha-next`.**

This is **not** a production/deployment approval. The economic framework is ready to be reconciled and tested with the recent Total RO Design producer, but shared routing/entitlement and future FX-service work remain integration dependencies.

## Reviewed branches

- Total Economic Design: `app/total-water-economics`
- Total RO Design: `app/total-ro-design`
- Integration target: `integration/alpha-next`

Reviewed Total RO Design head during audit:

`664e1c8d3762373c690f9aa8ea1cd2825d232aa2`

Reviewed integration head during audit:

`4cebe2bef4aab0d3fffd2fc28fd4ab2c7531147f`

## Ready items

### Canonical economic-summary contract

The economics branch defines:

- `contract_id = twds.economic_summary`
- `contract_version = 1.0`
- controlled application IDs
- controlled CAPEX buckets
- controlled annual OPEX categories
- legacy migration adapters with warnings
- duplicate summary protection
- duplicate economic-item protection
- scope-overlap detection
- provenance normalization
- native/reporting currency metadata

### Total RO Design compatibility

The recent RO implementation uses the same contract/version and application ID `ro`.

The economics normalizer now specifically supports the RO producer's:

- already-namespaced item IDs without double-prefixing
- `user_entered_estimate` provenance alias
- `project_revision`
- `calculation_revision`
- `opex.annual`
- detailed scope keys

The common contract also supports the prompt-style `opex_annual` structure intended for future Bio/Pretreatment/ZLD implementations.

### Ownership boundary

Specialist applications own their process-scope CAPEX/OPEX.

Total Economic Design owns cross-application aggregation and project-level:

- construction/project indirects as assigned
- owner costs
- contingency
- escalation
- financing / IDC
- working capital
- annualized capital
- lifecycle economics
- LCOW
- DSCR
- tariff / project-finance metrics

### Legacy RO economics

The existing RO ERD economic comparison remains behind the original `economics.py` path unless `model=total_economic_design` is explicitly requested.

## Multi-currency readiness

The contract is now forward-compatible with multiple native currencies.

Normalized cost items preserve or expose:

- native amount
- native currency
- reporting currency
- FX rate metadata when available
- converted amount when available

For same-currency amounts the current engine records identity conversion metadata.

The future architecture requires one shared Suite FX service, current rates refreshed four times daily, and frozen FX snapshots for saved estimate revisions.

**The shared FX service is not implemented in this milestone.** Until it exists, non-zero native currencies that differ from the selected reporting currency are rejected. No silent 1:1 conversion is permitted.

## Reconciliation conditions

### 1. Do not merge the economics branch wholesale

Relative to `integration/alpha-next`, `app/total-water-economics` also carries an unrelated advanced-chemistry workflow inherited from branch history:

`.github/workflows/wire-advanced-chemistry-work.yml`

Reconcile the intended economic files/commits selectively. Do not use whole-branch replacement as the integration method.

### 2. Run the end-to-end RO -> Total Economic Design integration test

Reconciliation must generate a real RO `twds.economic_summary v1.0` payload and pass it directly into the Total Economic Design aggregator.

Verify CAPEX and OPEX enter once, scope IDs remain traceable, project contingency is added once, and legacy RO economics remains unchanged.

### 3. Dedicated Total Economic Design API/entitlement before customer release

The current administrator-preview UI still uses the legacy `/api/economics` route and a Total RO compatibility entitlement header.

This is acceptable as a temporary branch bridge but is **not** the intended permanent Suite architecture.

Reconciliation should either establish a dedicated Total Economic Design API/product entitlement or record that work as a release blocker. Do not expose the compatibility header as the final customer authorization model.

### 4. Hosted CI status is not observable through the current connector

The branch includes GitHub Actions checks for:

- Python compile
- Total Economic Design regression tests
- economic-summary contract readiness tests
- JavaScript syntax

The GitHub connector returned no combined status/workflow run for the reviewed push commit, so a hosted CI pass is not claimed. Reconciliation must run the tests on the integrated branch.

### 5. Bio / Pretreatment / ZLD are not yet common-contract producers

Do not call the economic framework fully Suite-wide until those applications implement/validate the canonical shared contract.

The contract is ready for them to consume after reconciliation centralizes it.

## Readiness classification

- Economic engine foundation: **GREEN**
- Cross-application aggregator: **GREEN**
- Canonical contract: **GREEN**
- RO contract compatibility: **GREEN, pending integrated regression execution**
- Duplicate/scope protection: **GREEN**
- Multi-currency schema direction: **GREEN**
- Live FX conversion service: **NOT IMPLEMENTED / planned dependency**
- Dedicated economics entitlement/API: **YELLOW / reconciliation or release dependency**
- Hosted CI confirmation: **YELLOW / must rerun on integration branch**
- Production deployment: **NOT APPROVED by this audit**

## Required reconciliation conclusion

Reconciliation may proceed now.

Do not promote to `alpha`/`main` or deploy solely on the basis of this audit. Promotion should occur only after the integrated RO -> Total Economic Design test, economic regression tests, authorization/routing review, and reconciliation conflict review pass.
