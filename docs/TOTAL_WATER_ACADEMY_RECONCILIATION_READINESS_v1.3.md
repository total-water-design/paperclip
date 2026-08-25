# Total Water Academy — Reconciliation Readiness Audit v1.3

**Repository:** `total-water-design/total-water-design-suite`  
**Source branch:** `app/total-water-academy`  
**Audited Academy source head before this audit-record commit:** `ad4931a32053c1bf3e232e5a5f82bf526c50f37d`  
**Previous reconciliation-ready branch head:** `e11568ec768b86cf8aa65706553787da48512f05`  
**Current target Alpha observed during this audit:** `f0e5a2df9b97de74b5866766f61c9e60be347709`  
**Target integration branch:** `alpha`, through the dedicated selective reconciliation workflow only

## Verdict

**ACADEMY SOURCE / CURRICULUM / MULTILINGUAL / EVIDENCE-GUARD VALIDATION: PASS.**

**GITHUB ACTIONS: PASS.**

Authoritative source-branch validation run:

- workflow: `Total Water Academy validation`
- run ID: `32797611250`
- run number: `132`
- validated SHA: `ad4931a32053c1bf3e232e5a5f82bf526c50f37d`
- command: `python -m pytest -q tests/test_total_water_academy*.py tests/test_ui_ux_contract.py`
- result: **382 passed in 1.68 s**
- conclusion: **success**

**SELECTIVE RECONCILIATION READINESS: YES.**

This source-branch pass does **not** replace the mandatory post-composition Alpha regression and smoke-test gate. Current Alpha has newer runtime, engineering and Suite Core composition that is not present on the Academy owner branch.

No deployment or promotion to `main` is authorized by this audit.

---

# 1. Why this audit was refreshed

The prior exact reconciliation-ready branch head was:

`e11568ec768b86cf8aa65706553787da48512f05`

After that milestone, the user supplied 105 photographed pages from Guillem Gilabert-Oriol's specialist UF membrane-cleaning material. The Academy source library was extended with:

- `docs/TOTAL_WATER_ACADEMY_UF_MEMBRANE_CLEANING_GILABERT_ORIOL_SOURCE_MAP_v1.0.md`
- `tests/test_total_water_academy_uf_membrane_cleaning_gilabert_oriol_source_map.py`

The source map is a major curriculum/evidence addition but **does not change executable Academy runtime behavior**.

The initial GitHub Actions validation after that addition exposed 11 failures in older regression guards. The new Gilabert-Oriol regression file itself was not among the failures.

The 11 failures were audited individually and determined to be stale/brittle test assertions involving exact typography, capitalization or wording rather than broken engineering/source contracts. Nine regression files were corrected so they test the intended invariant rather than accidental prose formatting.

No engineering source document was weakened to obtain the green result.

The final source validation then passed **382/382 tests**.

---

# 2. Exact Gilabert-Oriol addition

From the prior reconciliation-ready SHA `e11568ec768b86cf8aa65706553787da48512f05` to the first Gilabert-Oriol source milestone `b018c235e9ed2c5f894e209dbd84f77ef5065f84`, the branch added exactly two files:

1. `docs/TOTAL_WATER_ACADEMY_UF_MEMBRANE_CLEANING_GILABERT_ORIOL_SOURCE_MAP_v1.0.md` — 947 lines
2. `tests/test_total_water_academy_uf_membrane_cleaning_gilabert_oriol_source_map.py` — 259 lines

No Academy route, Flask model, template, JavaScript runtime, localization implementation, price catalog, entitlement behavior, WSGI registration, Suite Core service or specialist calculation engine changed in that two-file source addition.

The subsequent commits through audited SHA `ad4931a...` repair only pre-existing regression guards so that the complete Academy validation suite is green.

---

# 3. Gilabert-Oriol evidence classification and curriculum authority

The new source map treats the uploaded material as a **high-value expert/practitioner and research-grounded specialist reference** for UF/MF cleaning science, cleaning optimization methodology, operational diagnosis and SWRO pretreatment integration.

It does **not** convert source-specific Tarragona / Dow / DuPont experimental conditions into universal current design rules.

The Academy teaching center is the engineering method:

**fouling diagnosis → hydraulic cleaning → CEB → CIP → quantify recovery → account for downtime/water/chemical cost → validate changes experimentally → monitor long-term TMP/permeability behavior**.

The source map explicitly protects these distinctions:

- reversible versus persistent fouling;
- hydraulic backwash versus chemically enhanced backwash (CEB);
- CEB versus full cleaning-in-place (CIP);
- gross flux versus net productive availability;
- immediate TMP recovery versus long-term baseline drift;
- cleaning intensity versus total plant productivity;
- empirical model fit versus model applicability envelope;
- oxidant indication versus exact chlorine measurement;
- experimental brine backwash versus a project default.

## Prohibited universalizations

The new guard prevents Academy from silently teaching claims such as:

- more frequent backwash is always better;
- more backwash steps are always safer;
- a two-step backwash is a universal optimum;
- the highest chemical concentration is the best cleaning condition;
- CEB and CIP are interchangeable;
- a model developed at one plant is automatically valid at another;
- ORP is an exact free-chlorine concentration measurement;
- RO brine is proven safe as a universal UF backwash source;
- an experimentally observed Tarragona cleaning interval is a 2026 design setpoint.

## Brine-backwash case

RO-brine backwashing remains classified as:

**RESEARCH / SITE-SPECIFIC VALIDATION CASE — NOT A DEFAULT TWDS RECOMMENDATION**.

A learner must evaluate at minimum:

- brine chemistry and saturation state;
- pH;
- antiscalant/reductant carryover;
- precipitation during mixing;
- membrane/module compatibility;
- hydraulics and integrity;
- subsequent filtrate quality;
- controlled side-by-side evidence.

## Downstream RO interface

The source map also teaches that UF cleaning chemistry can affect downstream RO if residual chemical remains because of sequencing, dead volume, backflow, diffusion, rinse inadequacy or control failures.

Current project-grade RO membrane oxidant tolerance, membrane chemistry, residual limits and manufacturer restrictions remain owned by current Total RO Design / manufacturer authority. Academy does not invent a chlorine-compatibility rule.

## Curriculum placement

Primary curriculum home:

- `L03-M04 — MF/UF Pretreatment and Fouling Risk`

Cross-links:

- Level 2 — transport/fouling mechanisms;
- Level 6 — hydraulics, pumps, transitions and energy;
- Level 7 — cleaning state machines, instrumentation and PLC logic;
- Level 9 — lifecycle cost / availability optimization;
- Level 10 — complete UF operating and cleaning philosophy defense.

The 360 guided-hour total is unchanged.

The source map is curriculum/source architecture, not a claim that every learner screen is already authored.

When this material becomes learner-facing, it must enter the existing English / `es-419` / Arabic translation workflow.

---

# 4. Regression repair loop performed

The first validation run after the Gilabert-Oriol addition failed with:

- **371 passed**
- **11 failed**

The failures were traced to nine older test files. Examples included:

- matching `Academy does not` when the source intentionally used Markdown emphasis `Academy does **not**`;
- matching straight quotation marks when the source used typographic quotation marks;
- requiring `PLC` inside a placement question that was intentionally about an interlock rather than the PLC acronym;
- requiring English shared-shell labels to appear in the Academy translation overlay instead of in the canonical shared shell;
- matching `must not` when an approved roadmap used `should not` with the same explicit prohibition/condition;
- matching one exact EPC sentence instead of the protected `responsibility bundle` / `not automatically lump sum` distinction;
- requiring the noun `crystallization` when executable Level 8 already explicitly contained `crystallizer` / crystal-growth coverage;
- matching `increase TMP development` where the approved source used `accelerate TMP development`;
- case-sensitive matching of a Pearce age safeguard.

The tests were corrected to protect semantics rather than formatting.

The final workflow passed all 382 tests.

---

# 5. Current Alpha divergence — hard merge rule

At the audit freeze, current target Alpha is:

`f0e5a2df9b97de74b5866766f61c9e60be347709`

Comparison reports the Academy branch as:

- **227 commits ahead** of Alpha;
- **134 commits behind** Alpha;
- diverged from merge base `273f5834b1cfe69c75b516f7dd4486cb5171b121`.

Therefore:

> **DO NOT MERGE `app/total-water-academy` WHOLESALE INTO `alpha`.**

The branch carries historical Suite Core/platform/runtime history that must not overwrite newer Alpha composition.

Reconciliation remains selective.

---

# 6. Academy-owned selective payload

The reconciliation should source Academy-owned files from the final exact source SHA associated with this readiness record.

Core runtime/content:

- `academy.py`
- `academy_content.py`
- `academy_i18n.py`
- `academy_placement.py`

Templates:

- `templates/academy/**`

Academy static assets:

- `static/academy.css`
- `static/academy.js`
- `static/academy_i18n.css`
- `static/academy_i18n.js`
- `static/academy_i18n_boot.js`
- `static/academy_pricing.js`
- `static/branding/suite/total_water_academy_icon.svg`
- `static/branding/suite/total_water_academy_logo.svg`

Academy source/provenance documentation:

- `docs/TOTAL_WATER_ACADEMY_*.md`

This includes the new Gilabert-Oriol source map.

Academy regression coverage:

- `tests/test_total_water_academy*.py`

This includes the new Gilabert-Oriol evidence guard and the corrected semantic regression guards.

Workflow:

- `.github/workflows/academy-validation.yml`

---

# 7. Shared files that must NOT be copied wholesale from Academy

Use current target Alpha / Suite Core authority for shared files.

Do **not** replace from the Academy branch:

- `auth.py`
- `suite_catalog.py`
- `suite_commercial.py`
- `wsgi.py`
- `templates/shared/**`
- `templates/suite_dashboard.html`
- shared Suite static assets
- `requirements.txt`
- deployment files
- Suite feedback / metrics / communications / MFA implementations
- specialist application integrations

Current Alpha is authoritative for these areas.

---

# 8. Current catalog and commercial policy

Current Alpha already contains the Academy product definition with:

- product ID `academy`;
- category `education`;
- status `in_development`;
- route `/academy`;
- accent `#1A7F8E`;
- Academy icon/logo.

Therefore the reconciliation must preserve current Alpha `suite_catalog.py`; do not overwrite it from the divergent Academy branch.

Current Suite commercial policy still contains a legacy inactive Academy product-level `$5` placeholder. That value predates the modular individual-course pricing model and must **not** be interpreted as the current Academy course price.

Current Academy commercial intent is:

- Levels 1–2 foundation courses planned to remain free;
- advanced modules/courses have individual target one-time prices;
- all Academy courses remain free during Alpha;
- target prices are shown to collect tester pricing feedback;
- commercial billing remains inactive;
- future course-level billing/entitlement implementation remains Suite Core authority.

Do not create an Academy-owned payment or parallel entitlement database during reconciliation.

---

# 9. Mandatory target-side Suite Core access composition

This remains the principal known reconciliation integration requirement.

Current Alpha / current Suite Core `auth.py` still implements normal product accessibility approximately as:

- product status must be `available`;
- entitlement must be enabled/current;
- with a special administrator exception for Bio.

Academy intentionally remains:

`status = in_development`

Academy's own route-level access contract, however, allows:

- active administrators;
- active users with a valid/current Academy entitlement under pre-commercial policy.

Therefore an approved Academy learner can be authorized by Academy while current Suite dashboard serialization still reports the product as not accessible.

This must be corrected **narrowly in the target/Suite Core composition layer during reconciliation**.

Required final behavior:

1. Active administrator → Academy launch available.
2. Active approved Academy learner/student with enabled/current Academy entitlement → Academy launch available.
3. Active user without Academy entitlement → no Academy launch; direct route denied.
4. Unauthenticated hosted user → login flow.
5. Academy remains `in_development`; do not solve this by falsely setting status to `available`.
6. RO, Bio, ZLD and all other product-access behavior must remain unchanged.
7. `serialized_product_entitlements()` / Suite dashboard and Academy direct-route authorization must agree.
8. An entitled non-admin Academy learner must **not** be labeled `Administrator preview`.
9. Use an appropriate status such as `Approved Alpha learner` / `Approved student access` consistent with the final Suite UI contract.

This is a target-side composition requirement, not an Academy owner-branch defect.

---

# 10. WSGI integration rule

Current Alpha `wsgi.py` contains newer runtime composition for chemistry, Conventional RO, CCRO, Batch RO, mobile access, ZLD, RO economics, metrics, feedback hardening, MFA and other production integrations.

**Never replace current Alpha `wsgi.py` with the Academy copy.**

Add only the Academy imports:

```python
from academy import init_total_water_academy
from academy_placement import init_academy_placement
```

and initialize them at the appropriate point after their required Suite Core services are available:

```python
init_total_water_academy(app)
init_academy_placement(app)
```

Preserve all current Alpha startup sequencing and engineering registrations.

---

# 11. Multilingual reconciliation contract

Total Water Academy is the only TWDS application authorized for the current early multilingual release.

Supported locales:

- `en`
- `es-419`
- `ar`

English remains canonical for engineering/scoring meaning.

Translation may change presentation only. It must not change:

- level/module/activity/question IDs;
- answer keys;
- scores;
- pass thresholds;
- guided hours;
- price catalog values;
- equations;
- units;
- chemical formulas;
- engineering acronyms;
- specialist-owner identifiers;
- entitlements;
- verification tokens.

Arabic uses RTL for learner prose/UI while technical expressions remain correctly isolated LTR where needed.

The Academy-only translation overlay may translate visible shared-shell labels while the learner is inside Academy. It must not make other Suite applications multilingual.

---

# 12. Engineering-authority boundary

Academy owns pedagogy, explanations, exercises, learning progression, evidence literacy and educational scenarios.

It does not own project-grade calculation engines.

Authoritative project calculations remain with validated owners including:

- `engine/shared-water-chemistry`
- `engine/shared-waterstream`
- `app/total-water-balance`
- `app/total-pretreatment-design`
- `app/total-ro-design`
- `app/total-bio-design`
- `app/total-zld-design`
- `app/total-water-economics`

The new UF cleaning source map does not authorize Academy to hard-code current UF chemical compatibility, cleaning concentrations, module limits or RO oxidant tolerance.

---

# 13. Source-branch validation result

The source branch has now passed its configured Academy validation workflow.

Validated command:

```text
python -m pytest -q tests/test_total_water_academy*.py tests/test_ui_ux_contract.py
```

Result:

```text
382 passed in 1.68s
```

Workflow run:

`32797611250`

Conclusion:

`success`

This is materially stronger than the earlier v1.2 audit, where source CI was not confirmed.

---

# 14. Mandatory reconciliation hard gate

After selectively composing Academy onto the latest Alpha, rerun:

```text
python -m pytest -q tests/test_total_water_academy*.py tests/test_ui_ux_contract.py
```

Then run all relevant current Alpha regression suites.

The source-branch 382/382 pass does not prove the composed Alpha runtime is healthy.

Any failure after composition is a reconciliation blocker.

---

# 15. Mandatory Academy smoke matrix after composition

At minimum test:

- `/academy`
- `/academy/placement`
- saved placement profile
- explicit placement retake
- safe placement return-path behavior
- `/academy/levels/L01` through `/academy/levels/L10`
- `/academy/modules/L01-M01`
- all three pilot quizzes
- practical treatment-train exercise
- module test
- attempts / competency / progress persistence
- engagement heartbeat
- `/academy/diploma`
- diploma gating and unique verification token
- `/academy/api/curriculum`
- `/academy/language`
- CSRF behavior
- responsive/mobile/PWA rendering

Multilingual smoke:

`English → Español → العربية → English`

Validate:

- navigation;
- level/course catalog;
- pricing;
- placement diagnostic;
- complete pilot;
- feedback/hints;
- practical;
- module test;
- diploma;
- access denied;
- Academy-local shared chrome;
- Arabic RTL;
- technical LTR isolation;
- identical scoring/answer keys in every locale.

---

# 16. Mandatory access matrix after composition

Explicitly test:

A. unauthenticated user  
B. active user without Academy entitlement  
C. approved Academy learner with enabled/current Academy entitlement  
D. administrator

For each, test:

- Suite dashboard Academy card;
- direct `/academy` access;
- Academy API behavior where relevant.

Dashboard accessibility and route-level authorization must agree.

---

# 17. Current Alpha regression boundary

After Academy composition, preserve and validate relevant existing Alpha behavior including:

- application startup;
- authentication;
- MFA;
- Suite dashboard;
- Project Library;
- Suite feedback;
- Suite Metrics;
- current chemistry runtime;
- Conventional RO;
- CCRO;
- Batch RO;
- ZLD;
- RO economics;
- mobile access;
- reporting;
- current deployment/runtime wiring.

Do not alter another application's engineering implementation merely to make Academy pass.

---

# 18. Reconciliation decision rule

Only declare:

**ACADEMY RECONCILED / VALIDATED**

when:

1. Academy payload is selectively composed onto current Alpha;
2. shared Alpha/Suite Core authority is preserved;
3. Academy access serialization/dashboard composition is corrected;
4. Academy test suite passes on the composed candidate;
5. multilingual/access smoke tests pass;
6. relevant current Alpha regressions pass;
7. resulting Alpha SHA is recorded.

If a gate fails, fix the defect in the correct ownership/integration layer and repeat the affected validation/audit loop.

Do not deploy.

Do not promote to `main`.

Stop after producing the validated reconciled Alpha SHA.
