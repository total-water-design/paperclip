# Total Water Academy Architecture v0.1

**Owner branch:** `app/total-water-academy`  
**Application:** Total Water Academy  
**Course:** Applied Water Treatment Design  
**Course architecture:** 10 levels / 360 guided engagement hours  
**Credential:** Total Water Academy Diploma in Applied Water Treatment Design

## 1. Product intent

Total Water Academy teaches water-treatment engineering by making the learner use the same mental model as the Total Water Design Suite:

`Feed water → design basis → process selection → unit design → stream handoff → controls/energy/economics → integrated plant`

The Academy is educational. It never becomes the authoritative owner of specialist engineering equations and must not fork professional models merely to create easier training calculations.

The central learning strategy is **learn engineering by designing with the Suite**. Early levels use simplified teaching scenarios. Later levels progressively call validated Suite application/engine adapters so the learner becomes familiar with the professional workflow before entering industry.

## 2. Ten-level curriculum

| Level | Topic | Guided hours |
| --- | --- | ---: |
| 1 | Water Treatment Foundations & Water Quality | 30 |
| 2 | Units, Balances, Chemistry & Hydraulics | 34 |
| 3 | Pretreatment & Solids Separation | 38 |
| 4 | Membrane Systems — MF, UF, NF & RO | 46 |
| 5 | Biological Treatment & Water Reuse | 42 |
| 6 | Pumps, Energy & Electrical Systems | 34 |
| 7 | Instrumentation, Process Control & PLC | 32 |
| 8 | Residuals, Brine Management & ZLD | 34 |
| 9 | Integrated Design, Treatment Selection & Economics | 34 |
| 10 | Capstone — Design a Complete Water Treatment Plant | 36 |
| **Total** |  | **360** |

The hours are guided engagement targets, not academic-credit equivalencies.

## 3. Electrical and process-control scope

Level 6 introduces practical plant electrical literacy without representing the Academy as an electrician qualification. Topics include:

- pump duty points and efficiency;
- motor fundamentals;
- single-phase versus three-phase power;
- three-phase motor connections and Y/Delta starting concepts;
- contactors and overload protection concepts;
- soft starters;
- variable-frequency drives (VFDs);
- basic one-line and motor-control interpretation;
- energy consequences of process/control decisions.

Level 7 introduces plant automation and control:

- sensors, transmitters and final control elements;
- common analog/digital signal concepts;
- P&ID interpretation;
- control loops and PID concepts;
- PLC sequencing and ladder-logic literacy;
- permissives, interlocks, trips and alarms;
- control narratives and cause/effect reasoning;
- operability and safe-state thinking.

Detailed electrical design, code compliance, arc-flash studies, protection coordination and licensed engineering remain outside the Academy training credential unless separately developed and reviewed by qualified owners.

## 4. Learning-unit contract

The standard authored unit is:

`Concept → Quiz 1 → Concept → Quiz 2 → Concept → Quiz 3 → Practical → Module Test`

Each assessed activity records:

- attempt;
- submitted answer/design;
- score;
- correct/pass state;
- explanation shown;
- competency tags;
- timestamp.

The learner receives an engineering explanation rather than only correct/incorrect status. Wrong answers provide a principle and hint, then allow another attempt where appropriate.

## 5. Practical contract

Practicals are not ordinary multiple-choice questions. Supported/future interaction types include:

- assemble a treatment train;
- order process barriers;
- calculate and close a water balance;
- inspect a water analysis and identify design risks;
- select/swap a pretreatment technology;
- size a basic filter using a validated adapter;
- configure RO/NF stages and membrane selections;
- build a biological process train;
- diagnose an unstable or incorrect train;
- compare energy and lifecycle-cost consequences;
- construct a controls narrative / permissive sequence;
- identify appropriate motor-start/control approaches;
- route residual/brine streams toward MLD/ZLD;
- complete an integrated capstone plant design.

Every numerical practical must declare one of:

1. `validated Suite adapter` — preferred for professional engineering calculations;
2. `fundamental teaching arithmetic` — only for transparent first-principles concepts such as unit conversion, with assumptions shown;
3. `non-numerical reasoning` — process selection, sequencing, diagnosis or design review.

Academy must never hide a fudge factor or create a competing membrane/chemistry/bio/ZLD model.

## 6. Pilot module

The first complete module is `L01-M01 — Build Your First Treatment Train`.

It proves the full learning contract:

1. concept — plants as chains of barriers;
2. quiz — purpose of pretreatment;
3. concept — design from water quality rather than habit;
4. quiz — respond to changed feed conditions;
5. concept — every unit has a downstream customer;
6. quiz — sequencing logic;
7. practical — assemble a surface-water-to-RO treatment train using an interactive process toolbox;
8. module test — five-question reasoning assessment.

The practical is deliberately non-numerical for the first pilot so no duplicate engineering equations are introduced before specialist adapter contracts are available.

## 7. Learning-progress schema

### `academy_module_progress`

Per-user/per-module rollup:

- `user_id`;
- `level_id`;
- `module_id`;
- `state` (`not_started`, `in_progress`, `completed`);
- completed step IDs;
- demonstrated competency IDs;
- best score;
- attempt count;
- credited engagement seconds;
- start/completion/update timestamps.

### `academy_attempts`

Immutable assessment history:

- user/level/module/activity IDs;
- activity kind;
- submitted answer/design JSON;
- correct/pass state;
- score;
- explanation shown;
- timestamp.

### `academy_awards`

Future-safe award record:

- user;
- course version;
- award type;
- diploma title;
- verification token;
- issue status/time.

## 8. Diploma rules

The architecture supports a final course-completion diploma only after:

- every module in all ten levels is complete;
- each module/level satisfies configurable pass criteria;
- the final capstone assessment meets the higher capstone threshold (initial architecture: 80%).

Credential wording:

**Total Water Academy Diploma in Applied Water Treatment Design**

Mandatory disclaimer:

> This diploma records completion of Total Water Academy educational requirements. It is not professional licensure, engineering registration, or third-party accreditation.

Future PDF/verification presentation is a separate milestone. The current implementation stores the award and verification token but does not claim external accreditation.

## 9. Suite dependency boundary

| Suite owner | Academy use |
| --- | --- |
| `platform/suite-core` | identity, account, approved-student entitlement, theme, shared shell, feedback |
| `engine/shared-waterstream` | stream literacy and future integrated-train exercises |
| `engine/shared-water-chemistry` | authoritative common chemistry exercises |
| `app/total-water-balance` | water/material-balance labs |
| `app/total-pretreatment-design` | pretreatment selection/sizing labs |
| `app/total-ro-design` | RO/NF, membrane, hydraulics and energy labs |
| `app/total-bio-design` | biological-treatment labs |
| `app/total-zld-design` | brine concentration/ZLD labs |
| `app/total-water-economics` | CAPEX/OPEX/lifecycle comparison labs |

Academy may consume validated contracts from these owners. It must not modify their authoritative code from `app/total-water-academy`.

## 10. Access and commercial dependency

Suite Core remains authoritative for Academy access. The current Suite policy already defines:

- pre-commercial commercial state = off;
- target price = USD 5;
- billing cadence = undefined/configurable;
- free pre-commercial access = enabled for admin-approved eligible students;
- no `.edu`-only student assumption.

Academy consumes that entitlement and contains no independent billing/authentication system.

## 11. Content-source policy

Academy content must be traceable to:

1. validated Total Water Design Suite logic and documented assumptions;
2. authoritative owner documentation for each Suite engine/application;
3. recognized water/wastewater engineering texts, standards and guidance appropriate to the lesson;
4. recognized electrical/control standards and manufacturer-neutral engineering principles for Level 6/7;
5. explicit teaching assumptions where a professional design model is intentionally simplified.

Recommended source families for content review include AWWA, WEF/Metcalf & Eddy, US EPA, WHO, ASTM/ISO where applicable, IEC electrical/control standards (including PLC programming-language standards), and manufacturer-neutral pump/motor/drive references. Exact editions/clauses must be reviewed when each lesson is authored rather than copied generically into the Academy.

## 12. Engagement design

"Fun" means active engineering work, not cosmetic gamification. The UI uses:

- levels and design missions;
- visible progress;
- immediate explanatory feedback;
- retry loops;
- process toolboxes;
- design-review scoring;
- competency accumulation;
- future badges only when tied to demonstrated skills;
- capstone design defense.

Engagement heartbeats are capped and only credited while the module is actively visible; passive background time should not inflate course completion records.

## 13. Initial milestone acceptance criteria

- [x] current Suite Core UI/access capability audited;
- [x] ten-level curriculum architecture defined;
- [x] lesson/quiz/practical/test content schema defined;
- [x] learning-progress/attempt/award schema defined;
- [x] Suite Core entitlement integration defined;
- [x] one complete pilot module authored;
- [x] pilot interactive UI built;
- [x] curriculum structural validator included;
- [ ] runtime validation against reconciled deployment branch;
- [ ] specialist calculation adapter contracts;
- [ ] full course-library authoring;
- [ ] diploma PDF/verification presentation.

The branch must remain independent and must not be merged directly to `alpha` or `main` by the Academy owner.
