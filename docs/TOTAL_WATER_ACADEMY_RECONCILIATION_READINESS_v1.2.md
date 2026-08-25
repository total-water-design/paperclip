# Total Water Academy — Reconciliation Readiness Audit v1.2

**Repository:** `total-water-design/total-water-design-suite`  
**Source branch:** `app/total-water-academy`  
**Audited Academy source head before this audit-record commit:** `86d6fa1852f13e8135ac6eeb338576763d894771`  
**Current target Alpha observed during audit:** `8b9fa427d279ea3520a27b6acbfe93995b29dc34`  
**Target integration branch:** `alpha`, through the dedicated reconciliation workflow only

## Verdict

**ACADEMY-OWNED SOURCE / ARCHITECTURE / MULTILINGUAL AUDIT: PASS after corrective loop.**

**SELECTIVE RECONCILIATION READINESS: YES, with mandatory target-side access composition and post-composition runtime tests.**

**GITHUB CI / RUNTIME EXECUTION: NOT CONFIRMED.** GitHub exposes no completed commit status/check for the audited Academy source head. Do not describe this milestone as CI-confirmed. The reconciled Alpha candidate must execute the Academy and relevant Alpha regression suites as a hard gate before the reconciliation milestone is accepted.

No deployment or promotion to `main` is authorized by this audit.

---

## Corrective loop performed in this audit

The audit began from multilingual Academy milestone:

`67ae223ac0e07e6891b38fa4d744598d8c1d3551`

Seven corrective commits were added before the source head frozen above. The resulting diff is restricted to Academy-owned placement/localization surfaces and their regression tests.

### Correction 1 — placement return-path boundary

The original placement helper accepted any same-origin internal return path. That was not an open redirect, but it was broader than the Academy contract.

Corrected behavior now accepts only:

- `/academy`
- `/academy/...`
- `/academy?...`

and rejects/falls back from paths such as:

- `/ro`
- `/admin`
- `/academyevil`
- protocol-relative URLs
- external URLs
- non-HTTP schemes

Regression coverage was added.

### Correction 2 — first-entry namespace matching

The original placement hook used a broad `startswith('/academy')` test that could classify a near-match path such as `/academyevil` as Academy.

It now uses an exact Academy namespace helper: exact `/academy` or `/academy/...` only.

Regression coverage was added.

### Correction 3 — complete Academy-page multilingual chrome

The initial multilingual implementation translated Academy-owned learner content but left visible shared-shell labels in English while the learner was inside Academy.

An Academy-only client presentation layer now localizes, on Academy pages only:

- Feedback button;
- Appearance control;
- System / Light / Dark labels;
- Suite-return label;
- Application heading;
- My account / Manage users / Project database / Sign out actions;
- feedback dialog title/copy;
- feedback categories;
- description/placeholder;
- screenshot option;
- cancel/submit actions;
- client progress messages;
- successful feedback receipt/reference message.

The shared Suite Core shell itself was not modified. Other TWDS applications remain English-only.

Regression coverage verifies that the Academy translation overlay does not write account state, entitlements, billing, engineering data, or specialist calculations.

---

## Multilingual release audit

Supported locales remain exactly:

- `en` — English — LTR
- `es-419` — neutral Latin-American Spanish — LTR
- `ar` — Modern Standard Arabic — RTL

English remains the canonical authored/scoring source. Spanish and Arabic are presentation layers only.

The current executable learner surface includes localized presentation for:

- Academy navigation and responsive shell;
- all 10 level titles and missions;
- all 50 current module/course titles;
- current displayed competencies;
- course catalog and Alpha target-price labels;
- placement/self-assessment UI;
- all 12 placement diagnostic questions;
- complete `L01-M01` pilot content;
- three pilot quizzes and choices;
- correct/incorrect feedback and hints;
- treatment-train practical and unit labels;
- module test;
- progress/completion feedback;
- access-denied messaging;
- Diploma title/status/disclaimer;
- Academy curriculum API presentation;
- shared visible Suite chrome while on Academy pages.

Localization must not alter:

- IDs;
- answer indexes;
- scoring;
- pass criteria;
- guided hours;
- prices;
- engineering equations;
- numeric values or units;
- chemical formulae;
- RO/UF/MF/NF/MBR/ZLD/PLC/VFD/PID/CAPEX/OPEX identifiers;
- specialist-owner identifiers;
- entitlement IDs;
- verification tokens.

Arabic RTL must not reverse engineering process meaning, equations, P&ID tags, numeric values, or technical acronyms.

Technically competent human Spanish and Arabic review remains a pre-commercial language-quality gate. It is not an Alpha reconciliation blocker.

---

## Curriculum integrity

PASS.

The executable curriculum still preserves:

- 10 levels;
- 360 guided hours;
- 50 current modules/courses;
- Level/module hour reconciliation;
- `Concept → Quiz → Concept → Quiz → Concept → Quiz → Practical → Test` pilot flow;
- 75% default module pass architecture;
- 80% capstone requirement;
- user-scoped progress/attempt/competency/engagement records;
- diploma verification-token architecture;
- explicit non-licensure/non-accreditation disclaimer.

The advanced project-development/commercial/finance material remains a source/authoring specification that must be reconciled into the existing Level 9 34-hour envelope before full Level 9 learner authoring. This is not a runtime reconciliation blocker for the current pilot milestone.

---

## Engineering-authority audit

PASS.

Academy owns pedagogy, learning content, quizzes, progress, educational practical interfaces and learner-facing explanation.

Academy does not become authoritative for professional engineering calculations. Project-grade calculations remain with their owners, including Shared Water Chemistry, Shared WaterStream, Total Water Balance, Total Pretreatment Design, Total RO Design, Total Bio Design, Total ZLD Design and Total Water Economics.

No correction in this audit modified those specialist engines.

---

## Current Alpha divergence — critical rule

At this audit, comparison of `alpha` to `app/total-water-academy` reports:

- Academy **215 commits ahead** of Alpha;
- Academy **132 commits behind** Alpha;
- merge base `273f5834b1cfe69c75b516f7dd4486cb5171b121`;
- target Alpha `8b9fa427d279ea3520a27b6acbfe93995b29dc34`.

**DO NOT MERGE `app/total-water-academy` WHOLESALE INTO `alpha`.**

The Academy branch carries stale historical shared-platform/runtime files. A normal merge can regress current Alpha chemistry, CCRO, Batch RO, ZLD, RO economics, mobile access, Suite Metrics, feedback hardening, MFA or deployment/runtime behavior.

---

## Academy-owned payload for selective reconciliation

Selectively reconcile Academy-owned files only, including:

- `academy.py`
- `academy_content.py`
- `academy_i18n.py`
- `academy_placement.py`
- `templates/academy/**`
- `static/academy.css`
- `static/academy.js`
- `static/academy_i18n.css`
- `static/academy_i18n.js`
- `static/academy_i18n_boot.js`
- `static/academy_pricing.js`
- `static/branding/suite/total_water_academy_icon.svg`
- `static/branding/suite/total_water_academy_logo.svg`
- `docs/TOTAL_WATER_ACADEMY_*.md`
- `tests/test_total_water_academy*.py`
- `.github/workflows/academy-validation.yml`

Do not infer that similarly named shared Suite files are Academy-owned.

---

## Shared target files — explicit authority decisions

### `suite_commercial.py`

**DO NOT COPY FROM ACADEMY.**

Current Alpha and Academy resolve to the same observed blob for this file:

`f0a83857f02116e548a5b92c07ed1db72c5f41fe`

Alpha therefore already has the Academy pre-commercial policy infrastructure.

The existing product-level `price_usd_cents=500` is a legacy pre-commercial placeholder from the original Academy concept. The current Academy commercial direction is modular course purchasing with Levels 1–2 free and visible per-course target prices for Alpha feedback. Because `commercial_active=False`, the old $5 value must not be interpreted or exposed as the price of the current 50-course Academy catalog.

Before commercial billing is activated, Suite Core must implement/approve course-level entitlement/pricing semantics or otherwise supersede that product-level placeholder. That future billing schema is not an Alpha reconciliation blocker.

### `suite_catalog.py`

**DO NOT COPY FROM ACADEMY. USE CURRENT ALPHA AUTHORITY.**

Current Alpha already contains the Academy product entry with:

- `product_id='academy'`
- category `education`
- route `/academy`
- status `in_development`
- accent `#1A7F8E`
- Academy icon/logo assets.

The Academy branch copy is stale in unrelated catalog details. One observed example is the ZLD route: current Alpha uses `/zld/` while the Academy branch copy uses `/zld`.

Therefore reconciliation should normally make **no `suite_catalog.py` change** unless target Alpha changes again before composition.

### shared application shell / shared Suite assets

**DO NOT COPY FROM ACADEMY.**

The Academy templates extend the target shared application shell. The multilingual shared-chrome translation is implemented in Academy-owned `static/academy_i18n.js`; no global Suite localization modification is required.

### `wsgi.py`

**NEVER REPLACE CURRENT ALPHA WSGI.**

Current Alpha WSGI owns the validated composition for runtime chemistry, CCRO, Batch RO, RO customer surface/UI contract, mobile access, ZLD integration, RO economics, Suite Metrics hardening/audit, feedback hardening, communications, reports, commercial policy and MFA.

Reconciliation should add only the Academy imports/initializers at the appropriate point after Suite Core prerequisites:

```python
from academy import init_total_water_academy
from academy_placement import init_academy_placement
```

and later:

```python
init_total_water_academy(app)
init_academy_placement(app)
```

Do not remove, reorder broadly, or replace existing Alpha registrations merely to integrate Academy.

### `requirements.txt`, deployment files, shared auth/templates/static files

**DO NOT COPY FROM ACADEMY.**

The multilingual Academy milestone introduces no new Python runtime dependency that requires replacing Alpha requirements. Preserve target dependency/deployment authority.

---

## Mandatory target-side launch composition

This audit found one current-Alpha integration issue that must be resolved during selective reconciliation.

Academy's own route guard correctly allows:

- administrators;
- active users with current administrator-granted Academy entitlement under the pre-commercial policy;
- future current Academy entitlements when commercial policy changes.

However current Alpha `auth.py` / `serialized_product_entitlements()` marks an application `accessible` only when:

- the product is `available` and has a current entitlement; or
- it is the special Bio administrator-preview case.

Because Academy intentionally remains `in_development`, current Alpha therefore reports Academy `accessible=False` even for an approved Academy student, and the dashboard presents no active launch control. Administrators likewise do not receive an Academy preview through this generic accessibility result.

This mismatch is also present on the observed `platform/suite-core` branch and is not an Academy-owned file to patch here.

### Required reconciliation behavior

During reconciliation, align the target Suite launch/access presentation with the Academy route contract without making Academy generally public.

At minimum validate all of the following:

1. active administrator → Academy launch control available;
2. active approved student/user with enabled current Academy entitlement → Academy launch control available;
3. active user without Academy entitlement → no Academy launch control and direct route denied;
4. unauthenticated hosted user → login flow;
5. Academy stays `in_development`; do not solve this by setting catalog status `available`;
6. current RO/Bio/ZLD/other application accessibility behavior is not regressed;
7. web/PWA/API representations of Academy accessibility do not contradict each other;
8. dashboard wording for an entitled non-admin Academy learner must not incorrectly say `Administrator preview`.

Because Suite Core owns account/entitlement semantics, implement this as a narrow target-side composition consistent with current Suite Core architecture. Do not introduce an Academy-owned parallel entitlement database.

This is a **mandatory reconciliation integration step**, not authorization to copy stale Academy `auth.py` or `suite_dashboard.html` wholesale.

---

## Mobile / PWA audit

Academy multilingual delivery uses the existing hosted responsive application/PWA path. It does not introduce a second mobile curriculum or calculation engine.

The Academy-specific locale files are loaded only on Academy pages. The rest of TWDS remains English-only.

Current Alpha mobile enforcement does not need to be replaced to reconcile Academy. Validate phone browser/PWA/native-access-channel behavior according to the target's current mobile policy after composition.

---

## Test and validation hard gate

The Academy workflow is configured to run:

```text
python -m pytest -q tests/test_total_water_academy*.py tests/test_ui_ux_contract.py
```

The source milestone includes regression coverage for:

- curriculum integrity;
- placement profile safety;
- strict Academy-local return paths;
- exact Academy namespace matching;
- entitlements/source ownership;
- pricing/PDH safeguards;
- all three locales;
- all 50 course-title translations;
- diagnostic answer-key invariance;
- pilot answer/scoring invariance;
- Arabic RTL contract;
- Academy-only shared-shell localization;
- shared feedback localization;
- branding;
- source-map evidence boundaries;
- specialist-engine non-ownership.

GitHub exposes no completed status check for the audited source head, so these tests must be executed on the reconciled Alpha candidate.

### Mandatory reconciliation smoke tests

Test at minimum:

- `/academy`
- `/academy/placement`
- safe placement return path
- explicit placement retake
- `/academy/levels/L01` through `/academy/levels/L10`
- `/academy/modules/L01-M01`
- all three pilot quizzes
- treatment-train practical
- module test
- progress/attempt/competency persistence
- engagement heartbeat
- `/academy/diploma`
- `/academy/api/curriculum`
- `/academy/language`
- English → Spanish → Arabic → English switching
- browser-language fallback
- Arabic RTL
- technical token direction/isolation
- Academy-only translated shared chrome
- course-price invariance across locales
- administrator Academy launch
- entitled learner Academy launch
- unentitled learner denial
- unauthenticated login redirect
- CSRF behavior
- direct Academy API isolation from legacy RO API gates
- light/dark themes
- responsive/PWA layout.

Then execute relevant current Alpha regression suites for startup, authentication/MFA, Suite landing/dashboard, Project Library, Suite Metrics, Shared Chemistry, conventional RO, CCRO, Batch RO, ZLD, RO economics, feedback and other already integrated target applications.

Any failure is a reconciliation blocker. Fix only in the correct owner/integration layer, then repeat validation before declaring the reconciled candidate complete.

---

## Reconciliation decision

The Academy source branch is now **prepared for selective reconciliation**.

There are no remaining known Academy-owned source blockers after the corrective loop.

Reconciliation is responsible for:

- composing Academy-owned payload onto current Alpha;
- preserving all target authority;
- performing the mandatory narrow Suite launch/access composition described above;
- executing the full runtime/regression hard gate;
- stopping if any failure remains.

Do not deploy and do not promote to `main` as part of this reconciliation.