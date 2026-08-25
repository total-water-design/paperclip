# Total Water Academy — Early Multilingual Release Contract v1.0

## Scope

Total Water Academy is the **only Total Water Design Suite application authorized for the initial multilingual release**.

Supported learner-facing locales:

- `en` — English — left-to-right (LTR)
- `es-419` — neutral Latin-American Spanish — left-to-right (LTR)
- `ar` — Modern Standard Arabic — right-to-left (RTL)

All other Total Water Design Suite applications remain English-only until separately approved by their owners and Suite Core.

This is an Academy presentation/localization capability. It does **not** authorize Academy to localize, fork, or alter specialist engineering calculations.

---

## One Academy, not three separate applications

The multilingual release uses:

**one canonical curriculum → one set of stable IDs and answer keys → one user progress record → three presentation languages**.

English remains the canonical authored/scoring source for the current milestone.

Spanish and Arabic change presentation only. They must never change:

- course, level, module, step, question, answer or competency IDs;
- answer indexes or scoring logic;
- pass criteria;
- guided-hour values;
- calculations or equations;
- numbers or units;
- chemical formulae;
- membrane/product identifiers;
- P&ID/instrument tags;
- specialist-engine owner identifiers;
- certificate verification tokens;
- entitlement/product identifiers.

---

## Web and mobile/PWA architecture

The existing TWDS mobile experience is an installable Progressive Web App (PWA) using the same hosted application as desktop/mobile web.

Therefore Academy does **not** maintain a second independent mobile translation library.

Desktop web, mobile web and installed PWA use the same:

- server-side locale selection;
- localized curriculum objects;
- templates;
- API presentation layer;
- CSS/RTL behavior;
- interactive JavaScript labels;
- course pricing presentation;
- learner progress state.

The localization implementation must remain compatible with the Suite PWA's network-first/security model. Engineering/project API responses are not turned into offline authoritative calculations merely because the Academy has translated static assets.

---

## Language selector contract

The Academy shows a compact globe-language selector in its learning/application bar.

Display choices:

- English
- Español
- العربية

Do **not** use national flags. Languages are not equivalent to countries.

Selection precedence:

1. saved Academy session preference;
2. browser/device `Accept-Language` preference;
3. English fallback.

Do **not** select language from geographic location.

The language-selection endpoint:

- is Academy-scoped;
- accepts only approved locale codes;
- uses CSRF protection through the Suite framework;
- accepts only an Academy-local return path;
- must not create an open redirect;
- must not change the global language of other Suite applications.

A later Suite Core milestone may persist the Academy locale preference on the user account for cross-device synchronization. Academy must not independently modify Suite Core's user schema to achieve that.

---

## Spanish translation standard

Use neutral technical Spanish suitable for Latin America (`es-419`).

Prefer clear engineering terminology over country-specific slang.

International water-industry acronyms remain visible, e.g.:

- Ósmosis inversa (RO)
- Ultrafiltración (UF)
- Microfiltración (MF)
- Nanofiltración (NF)
- Biorreactor de membranas (MBR)
- Descarga líquida cero (ZLD) where useful, while retaining `ZLD`
- Variador de frecuencia (VFD)
- Controlador lógico programable (PLC)

Do not replace internationally used engineering acronyms with invented localized acronyms.

---

## Arabic translation standard

Use Modern Standard Arabic suitable for technical education.

Arabic learner-facing prose and UI use RTL layout.

Engineering expressions remain isolated LTR where needed, including:

- `RO`, `UF`, `MF`, `NF`, `MBR`, `ZLD`;
- `PLC`, `VFD`, `PID`;
- `CAPEX`, `OPEX`;
- `CaCO₃`, `SO₄²⁻`, `HCO₃⁻` and other chemical notation;
- `Q = A·J` and other equations;
- `25 mg/L`, `10 m³/h`, `4–20 mA` and other values/units;
- P&ID tags and equipment identifiers;
- verification tokens and source identifiers.

RTL must not automatically reverse the engineering meaning of a process train, PFD, graph axis, equation, instrumentation tag, or left-to-right numeric expression.

When an original Academy diagram is authored in the future, its process direction must be explicit rather than assumed from text direction.

---

## Canonical scoring and audit trail

Assessment evaluation remains canonical and language-independent.

The same answer must produce the same:

- correctness result;
- numeric score;
- competency update;
- completed-step state;
- module state;
- diploma eligibility result

in English, Spanish and Arabic.

Audit/progress records retain canonical identifiers and canonical engineering meaning. Localized feedback can be returned to the learner without changing the scoring evidence.

---

## Translation coverage for the initial executable Academy

The early multilingual release must cover all currently learner-facing executable Academy content:

- Academy navigation and responsive shell;
- course catalog and Alpha pricing messages;
- all 10 level titles and missions;
- all 50 current module/course titles;
- competencies displayed in the current curriculum;
- entry/placement diagnostic;
- self-rating labels and learning-track presentation;
- complete `L01-M01` pilot:
  - concepts;
  - all three quizzes;
  - choices;
  - correct/incorrect feedback;
  - hints;
  - interactive treatment-train practical;
  - process labels;
  - module test;
  - client-side validation/feedback;
- access-denied/student-entitlement messaging;
- course-pricing labels;
- PDH/CEH disclaimers;
- progress/completion messaging;
- Diploma title, completion screen and disclaimer;
- localized curriculum API presentation.

Internal development/source-map documents do **not** need to be translated simply because they exist. When material from those documents becomes learner-facing course content, the learner-facing content must enter the translation workflow.

---

## Research references and provenance

Scientific paper, book, standard, manufacturer and agency titles may remain in their canonical published language in `Research Basis / Sources & Further Reading`.

A short translated description may be added, but citation identity must not be changed.

Do not create translated quotations that are presented as verbatim source text unless a verified published translation exists.

---

## Professional-development / PDH safeguards

Translation does not alter the continuing-education status of a course.

If a course is `completion_only` in English, its Spanish and Arabic versions are also `completion_only` unless the applicable provider/jurisdiction approval explicitly recognizes the translated delivery.

Do not claim:

- PDH;
- CEH;
- CEU;
- license-renewal credit;
- accreditation

for a translated course solely because its English version is later approved.

Approval/acceptance requirements for translated delivery must be verified separately where required.

---

## Quality assurance before public multilingual release

Automated regression must verify:

1. supported locale codes and directions;
2. all current 50 module titles have Spanish/Arabic presentation;
3. the 12-question placement diagnostic preserves IDs and answer keys;
4. the full pilot preserves step IDs, kinds, answers and pass scores;
5. hours/numeric values do not change;
6. specialist owner identifiers do not change;
7. technical acronyms/units remain intact;
8. Arabic enables RTL;
9. technical spans can remain LTR inside Arabic;
10. language switching is CSRF-protected and Academy-scoped;
11. localized pricing still uses the same price catalog;
12. PDH/CEH disclaimers remain present in every locale.

Before a commercial multilingual release, engineering terminology should also receive human review by technically competent Spanish and Arabic reviewers. Automated translation coverage is not, by itself, the final professional-language quality gate.

---

## Current implementation boundary

This milestone intentionally does **not**:

- localize Total RO Design, Total Bio Design, Total ZLD Design, Total Pretreatment Design or other Suite applications;
- alter Suite Core authentication/billing;
- create a separate Arabic or Spanish calculation engine;
- translate proprietary source code for educational display;
- claim that all future 360-hour Academy lesson content has already been authored or translated;
- persist locale to a new Suite Core account field;
- change current PDH/CEH approval state.

It provides a multilingual-ready Academy shell and translated presentation for the learner-facing content currently implemented, with a controlled translation architecture ready for future authored modules.
