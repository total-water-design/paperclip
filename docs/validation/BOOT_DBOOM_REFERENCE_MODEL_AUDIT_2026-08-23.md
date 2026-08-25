# BOOT / DBOOM Desalination Reference Model Audit

**Date:** 2026-08-23  
**Application branch:** `app/total-water-economics`  
**Reference workbook:** `BOOT_DBOOM_Desalination_Base_Financial_Model.xlsx`  
**Purpose:** Use the workbook as a reference/golden financial model for future Total Water Economics project-finance and BOOT development. Do not port it sheet-for-sheet.

## Executive conclusion

The workbook contains a useful and materially deeper project-finance layer than the current Total Water Economics engine. Its strongest reusable concepts are the time-phased construction spend profile, debt/equity construction funding, IDC, debt amortization, yearly revenue/OPEX escalation, working-capital movement, tax/book depreciation, annual DSCR, project/equity IRRs, WACC/NPV, fixed/variable DBOOM tariff structure, take-or-pay/offtake assumptions, and terminal/pre-termination concepts.

However, several legacy sheets contain broken references and stale conventions. The workbook should therefore be treated as a **reference model and numerical benchmark**, not as production code.

## Base case observed in workbook

- Construction period: 24 months
- Operating/concession period: 300 months / 25 years
- Design production: 9,125,000 m3/year
- Contracted production: 8,668,750 m3/year
- Plant availability: 95%
- Debt / equity: 70% / 30%
- Senior debt rate after COD: 7.0%
- Construction-period debt rate: 8.75%
- Upfront bank fee: 3.0%
- Senior debt tenor: 18 years / 216 monthly installments
- Revenue escalation: 2.0% p.a.
- OPEX escalation: 2.0% p.a. by major category
- SEC: 3.8 kWh/m3
- Power price: 0.08 USD/kWh
- Corporate tax rate: 25.8%
- Terminal value assumption: 5% of EPC turnkey cost at the end of the 25-year concession
- Base water tariff / DBOOM charge: approximately 1.278 USD/m3
- Year-1 DBOOM revenue: approximately 11.079 million USD
- Total capital expenditure: approximately 42.514 million USD
- Senior debt: approximately 29.760 million USD
- Equity: approximately 12.754 million USD

### Independently cross-checked headline returns

Using the workbook's final cash-flow rows:

- Post-tax unlevered project IRR: **9.6226%**
- Pre-tax unlevered project IRR: **11.8703%**
- Post-tax leveraged/equity IRR: **14.1441%**
- Pre-tax leveraged/equity IRR: **17.1211%**
- Average post-tax DSCR over the 18-year senior-debt period: **2.0709x**
- WACC: **9.6358%**

The final IRRs were independently recalculated from the workbook cash-flow series and matched the workbook results to floating-point precision.

## What should be preserved conceptually in Total Water Economics

### 1. Monthly construction cash-flow and funding schedule

The workbook has a 24-month EPC payment profile split across PDB/site work and supply milestones. Debt and equity are drawn against project cost rather than applying only a single financing percentage to final CAPEX.

**Recommendation:** Total Water Economics should add a period-based construction spend curve and funding schedule while retaining its own canonical CAPEX/CBS/provenance architecture.

### 2. Construction-period IDC

The workbook capitalizes IDC by applying the construction-period debt rate to debt-funded monthly EPC draws for the remaining months to COD. This is materially better than the current Total Water Economics percentage IDC allowance.

**Recommendation:** replace the current financing/IDC allowance with a schedule-linked financing engine when construction scheduling is enabled. Keep the allowance path for Class 5/4 estimates.

### 3. Revenue / tariff architecture

The workbook distinguishes:

- fixed facility/capital-recovery payment;
- fixed O&M payment;
- variable O&M/output payment;
- power/client-scope pass-through concepts;
- guaranteed offtake / take-or-pay;
- annual tariff escalation.

This is useful for DBOOM/BOOT commercial structures and should become configurable tariff components rather than one generic tariff input.

### 4. OPEX escalation by category

Manpower, chemicals, consumables, maintenance, spares and project-company costs have separate escalation inputs.

**Recommendation:** specialist application OPEX summaries should retain physical quantities where possible; Total Water Economics should then apply project-specific price/escalation curves by category without double counting.

### 5. Detailed working capital

The workbook models receivables, spares/consumables inventory, payables, yearly net working capital and annual working-capital movements, with release at concession end.

**Recommendation:** replace the current simple working-capital percentage with an optional days-based working-capital module.

### 6. Debt amortization and annual DSCR

The workbook carries opening balance, principal, interest, closing balance and annual debt-service coverage. This is a stronger foundation than the current Total Water Economics level-debt-service screen.

**Recommendation:** introduce an explicit debt schedule with multiple repayment modes: straight-line principal, annuity, sculpted debt service, balloon and custom schedule.

### 7. Tax and depreciation

The workbook distinguishes tax depreciation and book depreciation and includes a jurisdiction-specific MAT/surcharge module.

**Recommendation:** Total Water Economics should implement a jurisdiction-neutral tax interface with country-specific adapters. Do not copy the workbook's tax regime as a universal default.

### 8. Project and equity return separation

The workbook distinguishes unlevered project returns from leveraged equity returns and also contains sponsor/financial-investor/O&M-JV return views.

**Recommendation:** preserve separate project IRR, equity IRR, sponsor IRR and partner/JV return concepts.

### 9. Terminal / handback / pre-termination economics

The workbook contains both end-of-concession terminal value and a contractual pre-termination compensation schedule.

**Recommendation:** Total Water Economics must separate:

- normal residual / handback value;
- early-termination compensation;
- sale/terminal value;
- client deposits/security deposits;
- concession transfer value.

These should not be represented as one generic terminal-value field.

## Workbook defects / limitations that must NOT be copied

### A. Legacy broken-reference sheets — HIGH RISK

The workbook's own Template Notes state that hundreds of cached errors were inherited from the source model and concentrate in legacy return sheets. The audit surfaced errors in:

- `FI Return Pre-tax Monthly CF`
- `PostTax Terurns + TV`
- `Returns (Pre-Tax)` progressive IRR cells
- `Returns` progressive IRR cells

The `PostTax Terurns + TV` sheet contains actual `#REF!` formulas and is referenced by Terminal Value and Revenue scenario cells. Cached values may still display, but those post-tax-with-terminal-value outputs should not be treated as independently validated until the sheet is rebuilt.

The early `#NUM!` IRR cells in the main `Returns` and `Returns (Pre-Tax)` sheets are mostly benign progressive-IRR calculations before the cash-flow series has sufficient sign changes; the final full-period IRRs calculate correctly.

### B. DSCR presentation sheet has a unit mismatch — DEFECT

The standalone `DSCR` sheet converts numerator components to USD millions but leaves bank principal repayment in full USD before dividing. This produces displayed Gross/Net DSCR values near zero (for example ~0.0000027x), which are dimensionally wrong.

The main `Returns` sheet's DSCR calculation is dimensionally consistent and the Key Outputs average DSCR of 2.0709x matches the 18-year post-tax DSCR series.

**Do not copy the standalone DSCR-sheet formulas.**

### C. MAT module is not actually active in the main post-tax return — IMPORTANT

The main `Returns` tax formula references the `MAT (New)` output multiplied by zero and instead applies `MAX(PBT × corporate tax rate, 0)`.

Therefore the headline post-tax returns do **not** currently include the MAT model even though the workbook retains detailed MAT sheets and Template Notes describe the jurisdiction-specific MAT regime.

**Decision required per project:** either activate an audited jurisdiction-specific tax module or remove dormant tax logic.

### D. Debt moratorium / repayment labels are inconsistent

The workbook contains conflicting conventions:

- operation begins 1-Jul-2025;
- senior repayment commencement assumption shows 1-Jul-2026;
- loan tenor is 18 years / 216 installments;
- a loan-schedule moratorium field references `MPCP = 0`;
- the Means of Finance narrative still mentions a 2-year moratorium and 12-year repayment / 14-year door-to-door structure.

This appears to be stale model text and/or incomplete date logic.

**Recommendation:** Total Water Economics should use explicit dated debt periods rather than text assumptions disconnected from the schedule.

### E. Straight-line debt only; no debt sculpting

The base workbook repays equal principal over the 18-year tenor. It does not use a target DSCR to sculpt debt service.

Missing lender-grade metrics/mechanics include:

- minimum DSCR covenant;
- debt sculpting;
- LLCR;
- PLCR;
- cash sweeps;
- distribution lock-up tests;
- reserve waterfalls;
- refinancing schedule;
- multiple senior tranches;
- hedging.

### F. DSRA logic is internally inconsistent / inactive

Base assumptions set minimum cash balance/DSRA to 0 months, while the loan schedule contains a separate 3-month DSRA calculation and BG financing rows. The main Returns cash flow currently carries zero DSRA movement.

**Recommendation:** make DSRA an explicit enabled/disabled module with a single source of truth.

### G. O&M workbook linkage was removed

Template Notes state that four O&M cost build-up cells were previously linked to an external O&M workbook and now contain cached hardcoded inputs.

These are useful placeholders but must not become default cost data in Total Water Economics.

### H. Tariff is evaluated, not solved

The workbook uses an entered tariff of approximately 1.278 USD/m3 and evaluates project/equity returns. It does not appear to dynamically solve tariff against a selected financing/return objective.

**Recommendation:** Total Water Economics should support tariff solving against one or more selected constraints, e.g. minimum DSCR, target equity IRR, target project IRR, concession NPV or blended criteria.

### I. Power terminology needs normalization

The tariff schedule treats power as a client-scope/pass-through concept in the base case, while some scenario labels refer to tariff "with Power". This can be commercially misleading.

Total Water Economics should explicitly classify each utility as:

- SPV cost embedded in tariff;
- indexed pass-through;
- client direct cost;
- shared/capped cost.

### J. Pre-termination compensation is not normal terminal value

The workbook's pre-termination schedule uses recovery factors that can make termination compensation exceed the remaining net book value. This is contractual compensation, not ordinary residual plant value.

These concepts must remain separate in TWDS.

## Comparison with current Total Water Economics

| Capability | Current TWDS | Workbook | Target |
| --- | --- | --- | --- |
| Suite app CAPEX/OPEX aggregation | Strong | Not applicable | Keep TWDS |
| Cost provenance / estimate maturity | Strong | Limited | Keep TWDS |
| CAPEX hierarchy | Strong | Project-specific | Keep TWDS hierarchy |
| Monthly construction spend curve | Missing | Strong | Add |
| Debt/equity construction draws | Missing | Present | Add |
| Schedule-linked IDC | Missing | Present | Add |
| Upfront financing fees | Simple allowance | Present | Add explicit fees |
| Revenue escalation | Missing | Present | Add |
| OPEX escalation by category | Missing | Present | Add |
| Take-or-pay / minimum offtake | Missing | Present | Add |
| Fixed + variable DBOOM tariff | Missing | Present | Add |
| Detailed working capital | Simple allowance | Present | Add |
| Year-by-year debt schedule | Screening only | Present | Add |
| Annual DSCR series | Single screening value | Present | Add correctly |
| Debt sculpting / LLCR / PLCR | Missing | Missing | New TWDS capability |
| Tax depreciation / book depreciation | Missing | Present | Add via tax adapter |
| Tax jurisdiction modules | Missing | India-like legacy logic | Build generic + adapters |
| Project IRR / equity IRR | Missing/limited | Present | Add |
| WACC / NPV | Partial | Present | Strengthen |
| Sponsor/FI/JV economics | Missing | Partial | Add optional layer |
| Terminal / handback | Missing | Present but mixed concepts | Add with clean separation |
| Early termination compensation | Missing | Present | Add optional commercial module |
| VAT/GST financing | Missing | Present | Add jurisdiction-specific module |
| Multi-currency + FX provenance | Architecture prepared | USD-only | TWDS should be stronger |
| Suite lineage / app provenance | Strong | Not applicable | Keep TWDS |
| Automated sensitivity / scenario matrix | Planned | Manual scenarios | Build in TWDS |

## Recommended implementation order

### P0 — before serious finance use

1. Keep canonical `twds.economic_summary` aggregation and cost ownership.
2. Close current Total Water Economics project-save and entitlement dependencies.
3. Enforce native/reporting currency handling for every manual project cost item.
4. Prevent specialist summaries from owning project-level contingency/financing buckets unless explicitly allowed.
5. Establish the workbook base case as a golden regression dataset.

### P1 — project-finance core

1. Period model: monthly construction + annual operating periods.
2. Construction spend curve.
3. Debt/equity draw schedule.
4. Schedule-linked IDC and financing fees.
5. Year-by-year revenue/OPEX escalation.
6. Detailed working capital.
7. Debt amortization schedule.
8. Period DSCR.
9. Tax/book depreciation.
10. Project and equity IRR / NPV.

### P2 — DBOOM / BOOT commercial layer

1. Fixed availability/capital-recovery charges.
2. Fixed and variable O&M charges.
3. Utility pass-through structures.
4. Take-or-pay/minimum offtake.
5. Tariff indexation/escalation.
6. Tariff solver.
7. Sponsor/FI/JV returns.
8. Terminal/handback economics.
9. Early-termination compensation.
10. VAT/GST/tax adapters.

### P3 — lender / transaction-grade project finance

1. Debt sculpting to target DSCR.
2. Minimum/average DSCR covenant tests.
3. LLCR / PLCR.
4. DSRA and other reserve accounts.
5. Cash waterfall and distribution lock-up.
6. Cash sweep.
7. Refinancing.
8. Multiple debt tranches.
9. FX/inflation/hedging assumptions.
10. Scenario/sensitivity/Monte Carlo.

## Golden regression outputs to preserve

When the future TWDS project-finance engine is configured to the same base assumptions, it should reproduce the following before additional sophistication is enabled:

- Total capital expenditure ≈ 42.514174 million USD
- Debt ≈ 29.759922 million USD
- Equity ≈ 12.754252 million USD
- WACC ≈ 9.6358%
- Year-1 tariff ≈ 1.278 USD/m3
- Year-1 revenue ≈ 11.078663 million USD
- Post-tax unlevered IRR ≈ 9.6226%
- Pre-tax unlevered IRR ≈ 11.8703%
- Post-tax equity IRR ≈ 14.1441%
- Pre-tax equity IRR ≈ 17.1211%
- Average post-tax DSCR over the 18-year senior debt period ≈ 2.0709x

These figures are reference-model benchmarks, not universal defaults.

## Release judgment

**Workbook as a reference model: APPROVED WITH CONDITIONS.**  
**Workbook as production finance engine: NOT APPROVED.**

Use it to define and regression-test the next Total Water Economics finance layer. Do not copy its broken legacy sheets, jurisdiction-specific tax assumptions, stale debt narrative, or mixed terminal/pre-termination concepts into production code.
