# Total Water Academy — Modular Commerce & PDH/CEH Readiness Roadmap v1.0

Owner: `app/total-water-academy`

Status: product/commercial/credential architecture

## 1. Product decision

Total Water Academy must support two simultaneous learner journeys:

1. **Full Diploma Journey** — the existing 10-level / 360-guided-hour progression for learners who want the complete Applied Water Treatment Design diploma.
2. **Choose-Your-Course Journey** — learners may take individual Academy modules without enrolling in the complete diploma path.

The purchasable unit is the **module/course**, not the entire Academy application.

A learner may accumulate individually completed courses over time. If the learner later satisfies all Diploma requirements, those completed courses count toward the Diploma; the learner does not repeat a course merely because it was originally purchased individually.

Suite Core remains the owner of authentication, entitlements, billing, payment provider integration, refunds, taxation, discounts and subscription/payment enforcement. Academy owns course catalog metadata, educational completion criteria and learner-facing course/price presentation.

## 2. Access model

### 2.1 Permanently free foundation

The following Academy levels are intended to remain free because they teach the basic science and engineering literacy that allows students to use the rest of the Suite responsibly:

- **Level 1 — Water Treatment Foundations & Water Quality**
- **Level 2 — Core Unit Operations, Balances & Transport Fundamentals**

All modules in L01 and L02 therefore have:

- `commercial_class = foundation_free`
- `target_price_usd = 0`
- `always_free = true`

This is a product-access decision, not a statement that the subjects have low educational value.

### 2.2 Commercial courses

Modules in Levels 3–10 are designed as individually purchasable professional/advanced courses.

During Alpha:

- all Academy courses remain free to eligible Alpha testers;
- no learner is charged;
- the target commercial price is visible;
- the UI must clearly separate **current Alpha price = $0** from **target launch price**;
- testers should be encouraged to give feedback on value and price.

After commercial activation, individual-course access must be enforced through Suite Core granular entitlements. Academy must not create an independent payment or entitlement database to bypass Suite Core.

### 2.3 Granular entitlement contract

Future Suite Core support should allow an entitlement key such as:

`academy.course.<MODULE_ID>`

Examples:

- `academy.course.L03-M02`
- `academy.course.L04-M03`
- `academy.course.L08-M04`

A broader `academy.full` entitlement may later grant all courses if a full-program bundle is approved, but individual course purchase is the primary commercial requirement defined here.

Until Suite Core supports granular course entitlements, Alpha Academy entitlement grants access to all Alpha courses.

## 3. Target individual-course pricing

These are **target launch prices for pricing research**, not active charges and not promises of final pricing. Billing cadence for individual courses is **one-time purchase** when commerce is eventually activated.

### Free foundation

| Module | Course | Hours | Alpha | Target launch |
|---|---|---:|---:|---:|
| L01-M01 | Build Your First Treatment Train | 7 | $0 | **FREE** |
| L01-M02 | Water Sources, Constituents and Design Objectives | 7 | $0 | **FREE** |
| L01-M03 | Reading Water Analyses and Process Flow Diagrams | 7 | $0 | **FREE** |
| L01-M04 | Engineering Assumptions, Limits and Safety | 7 | $0 | **FREE** |
| L02-M01 | Engineering Units, Dimensions and Process Variables | 6 | $0 | **FREE** |
| L02-M02 | Mass, Component and Water Balances | 8 | $0 | **FREE** |
| L02-M03 | Energy Balances and Heat Transfer | 7 | $0 | **FREE** |
| L02-M04 | Fluid Flow, Momentum, Pressure and Headloss | 7 | $0 | **FREE** |
| L02-M05 | Mass Transfer, Diffusion and Separation Fundamentals | 7 | $0 | **FREE** |
| L02-M06 | Solutions, Solubility, Crystal Basics & Water Chemistry | 7 | $0 | **FREE** |

### Level 3 — Pretreatment

| Module | Course | Hours | Alpha | Target launch |
|---|---|---:|---:|---:|
| L03-M01 | Screens, Strainers and Disc Filters | 7 | $0 | $59 |
| L03-M02 | Coagulation, Flocculation, Clarification and DAF | 9 | $0 | $79 |
| L03-M03 | Multimedia, Depth and Cartridge Filtration | 8 | $0 | $69 |
| L03-M04 | MF/UF Pretreatment and Fouling Risk | 8 | $0 | $79 |
| L03-M05 | Pretreatment Design Challenge | 4 | $0 | $49 |

### Level 4 — Membranes

| Module | Course | Hours | Alpha | Target launch |
|---|---|---:|---:|---:|
| L04-M01 | Membrane Transport and Separation | 8 | $0 | $99 |
| L04-M02 | RO/NF Configuration, Arrays and Staging | 10 | $0 | $129 |
| L04-M03 | Concentration Polarization, Activity, Scaling & Fouling | 9 | $0 | $129 |
| L04-M04 | Pumps, Energy Recovery and Hydraulic Limits | 9 | $0 | $99 |
| L04-M05 | Membrane Design Mission in Total RO Design | 8 | $0 | $149 |

### Level 5 — Biological Treatment & Reuse

| Module | Course | Hours | Alpha | Target launch |
|---|---|---:|---:|---:|
| L05-M01 | Wastewater Characteristics and Biological Kinetics | 8 | $0 | $79 |
| L05-M02 | Activated Sludge, SRT, HRT and Oxygen | 10 | $0 | $99 |
| L05-M03 | Nutrients, MBR and Advanced Biological Treatment | 9 | $0 | $109 |
| L05-M04 | Reuse Treatment Trains and Polishing | 8 | $0 | $89 |
| L05-M05 | Biological Design Mission | 5 | $0 | $69 |

### Level 6 — Pumps, Energy & Electrical

| Module | Course | Hours | Alpha | Target launch |
|---|---|---:|---:|---:|
| L06-M01 | Pumps, Curves, Duty Points and Efficiency | 8 | $0 | $69 |
| L06-M02 | Single-Phase and Three-Phase Power | 6 | $0 | $59 |
| L06-M03 | Motors, Contactors, Overloads and Y/Delta Starting | 7 | $0 | $69 |
| L06-M04 | Soft Starters, VFDs and Process Energy | 7 | $0 | $79 |
| L06-M05 | Electrical/Mechanical Troubleshooting Mission | 6 | $0 | $59 |

### Level 7 — Instrumentation, Controls & PLC

| Module | Course | Hours | Alpha | Target launch |
|---|---|---:|---:|---:|
| L07-M01 | Sensors, Transmitters, Valves and Signals | 7 | $0 | $69 |
| L07-M02 | Control Loops, PID and Process Dynamics | 7 | $0 | $79 |
| L07-M03 | PLC Fundamentals, Ladder Logic and Sequencing | 7 | $0 | $89 |
| L07-M04 | Permissives, Interlocks, Trips and Alarms | 6 | $0 | $79 |
| L07-M05 | Write a Water Plant Control Narrative | 5 | $0 | $69 |

### Level 8 — Brine, Crystallization & ZLD

| Module | Course | Hours | Alpha | Target launch |
|---|---|---:|---:|---:|
| L08-M01 | Residuals and Brine as Evolving Process Streams | 6 | $0 | $89 |
| L08-M02 | Concentrated Solutions, Solubility, Solid Phases & Crystal Habit | 7 | $0 | $99 |
| L08-M03 | Nucleation, Crystal Growth & Crystal-Size Distribution | 9 | $0 | $129 |
| L08-M04 | Evaporation, Industrial Crystallizers & MLD/ZLD Train Design | 8 | $0 | $149 |
| L08-M05 | ZLD Design Mission | 4 | $0 | $79 |

### Level 9 — Integrated Design / Economics / Project Development

The executable Level 9 curriculum is still being reconciled with the newer Project Development / EPC / PDB / Finance / WPA source architecture. Prices below apply to the current five-module slots and must be reviewed when final Level 9 authoring is frozen.

| Module | Current course slot | Hours | Alpha | Target launch |
|---|---|---:|---:|---:|
| L09-M01 | From Design Basis to Alternatives | 7 | $0 | $89 |
| L09-M02 | CAPEX, OPEX and Lifecycle Cost Fundamentals | 8 | $0 | $99 |
| L09-M03 | Energy, Reliability, Redundancy and Risk | 7 | $0 | $99 |
| L09-M04 | Integrated Treatment-Train Comparison | 8 | $0 | $119 |
| L09-M05 | Design Review Board Challenge | 4 | $0 | $79 |

### Level 10 — Capstone

| Module | Course | Hours | Alpha | Target launch |
|---|---|---:|---:|---:|
| L10-M01 | Capstone Design Basis and Feed Characterization | 6 | $0 | $99 |
| L10-M02 | Pretreatment + Biological + Membrane Train | 9 | $0 | $149 |
| L10-M03 | Residuals/ZLD, Crystallization, Water Balance & Energy | 7 | $0 | $129 |
| L10-M04 | Controls, Electrical Philosophy and Operability | 6 | $0 | $99 |
| L10-M05 | Economics, Final Design Review and Defense | 8 | $0 | $199 |

The aggregate target value of all 40 paid modules purchased individually is **$3,810**, representing approximately 290 guided advanced/professional hours after the 70-hour free foundation. This is intentionally a per-course catalog benchmark, not a required upfront payment.

## 4. Pricing rationale

Pricing should reflect:

- guided instructional hours;
- technical depth;
- quantity and quality of interactive engineering exercises;
- use of validated TWDS calculation environments;
- assessment depth;
- specialist source/research depth;
- instructor/SME review burden;
- future CE/PDH recordkeeping and credential administration;
- market positioning against specialist industrial water training.

The target catalog is intentionally priced below premium specialist training on a per-hour basis while allowing high-value advanced courses such as RO design, concentration polarization, crystallizer design and capstone defense to carry a higher price than introductory process modules.

Pricing is **not** derived from one competitor alone.

## 5. Alpha pricing feedback presentation

Every paid-course card should show three separate concepts:

- `ALPHA ACCESS: FREE`
- `TARGET LAUNCH PRICE: $XX ONE-TIME`
- `Pricing is being tested. No charge during Alpha.`

Foundation cards should show:

- `FOUNDATION COURSE`
- `FREE NOW & PLANNED TO REMAIN FREE`

Do not use strike-through pricing that could misleadingly imply an actual prior sale price.

Do not say “normally $99” before commercial launch. Say **target launch price**.

## 6. Course-level certificates

Academy should eventually issue two different credentials:

### Course Completion Certificate

May be issued once an authored module has:

- defined learning outcomes;
- defined completion requirements;
- required assessment(s);
- a configured passing score;
- verified learner identity where required;
- recorded completion date;
- auditable engagement/activity record;
- certificate verification token.

This certificate may show Academy **guided/learning hours**, but must not call those hours PDH, CEH or IACET CEU until the relevant continuing-education approval/quality requirements are satisfied.

### Full Diploma

The existing `Total Water Academy Diploma in Applied Water Treatment Design` remains the completion credential for the complete 10-level program.

It is not professional licensure, engineering registration or university accreditation.

## 7. PDH / CEH strategy

### 7.1 Do not self-declare universal PDH approval

Professional Development Hour / Continuing Education Hour acceptance varies by licensing jurisdiction and profession.

Academy must never state:

- `PDH approved in all 50 states`;
- `CEH accepted everywhere`;
- `guaranteed license-renewal credit`;
- or equivalent language

unless that claim is actually verified for the jurisdictions and period stated.

Before approval, learner-facing wording should be:

> **Continuing-education status: Course completion certificate only. PDH/CEH approval is planned and is not yet claimed.**

### 7.2 Build the platform PDH-ready now

Every candidate professional course should be authored with:

1. documented needs analysis / intended audience;
2. measurable learning outcomes;
3. course outline and content owner;
4. qualified subject-matter reviewer/instructor;
5. revision/version date;
6. source/provenance record;
7. countable instructional activities;
8. auditable learner participation;
9. knowledge checks and final assessment;
10. defined passing criteria;
11. identity/completion controls appropriate to delivery mode;
12. end-of-course learner evaluation;
13. completion record/transcript;
14. course certificate with unique verification token;
15. retention of completion records for the period required by applicable regulators;
16. process for course updates and withdrawal;
17. conflict-of-interest / commercial-bias controls where appropriate.

### 7.3 Do not equate guided hours automatically with PDH

The current Academy `hours` field is a **guided engagement target**.

A future PDH/CEH value must be separately approved/calibrated as `credit_hours` based on the applicable definition of qualifying instruction/participation.

For self-paced learning, merely leaving a browser page open cannot earn professional-development credit.

Countable participation should require meaningful interaction such as:

- instructional content progression;
- knowledge checks;
- interactive engineering exercises;
- required design work;
- assessments;
- monitored learner progress/feedback.

## 8. IACET pathway

IACET can be considered as a broad organizational continuing-education quality pathway.

Planning assumptions:

- IACET accredits **providers/organizations**, not an isolated course;
- applicant organizations must meet IACET eligibility and quality-system requirements;
- Academy should not call a course an **IACET CEU course** unless/ until the provider has the required accreditation and the learning event complies with the applicable ANSI/IACET standard;
- one CEU is conventionally based on ten qualifying contact hours, but Academy must calculate/award it only under an approved compliant process.

The IACET route is complementary to engineering-board PDH acceptance; it does not automatically replace jurisdiction-specific engineering-board requirements.

## 9. Engineering-board pathway

Start with selected jurisdictions rather than attempting all U.S. states at once.

Recommended pilot jurisdictions:

1. Florida
2. Texas
3. California
4. New York
5. another state with strong water/desalination/industrial-water market presence after legal/compliance review

For each jurisdiction maintain a matrix with:

- provider approval required?;
- course approval required?;
- self-paced online acceptable?;
- definition of PDH/CEH/contact hour;
- assessment requirements;
- certificate fields;
- provider reporting requirements;
- learner reporting requirements;
- record-retention period;
- ethics/law special-course restrictions;
- renewal cycle;
- approval/registration number and expiration date.

Do not expose a jurisdiction badge until this matrix is verified.

## 10. Florida readiness example

Florida is a useful first target because it has clear PE continuing-education rules and a defined provider process.

Academy architecture should be capable of storing, when applicable:

- learner name;
- learner PE/license number;
- course number;
- course topic;
- presenter/instructor;
- completion date;
- approved continuing-education hours;
- brief course description;
- provider identifier;
- certificate verification token.

This is a **readiness requirement**, not a statement that Academy is currently a Florida-approved CE provider.

The Florida Laws & Rules course is a special case and must never be offered for Florida Laws & Rules credit unless the specific provider/course approval has been obtained.

## 11. Learner-facing continuing-education status

Each course card should eventually expose one of:

- `FOUNDATION — NO PROFESSIONAL CREDIT CLAIMED`
- `COMPLETION CERTIFICATE`
- `PDH CANDIDATE — APPROVAL IN PROGRESS`
- `PDH ELIGIBLE — VERIFY JURISDICTION`
- `APPROVED: <JURISDICTION / PROVIDER / COURSE ID>`
- `IACET CEU ELIGIBLE` only when legitimately applicable

During Alpha, use:

**Course completion / PDH architecture in development — no PDH/CEH claim yet.**

## 12. Recommended course hierarchy in the UI

Academy home should no longer force the learner to think only in terms of the diploma path.

Primary choices:

- **Explore Courses** — pick an individual topic.
- **Follow the 10-Level Diploma Journey** — complete the whole program.
- **Start with Free Foundations** — L01/L02.

Within a Level page, every module is presented as an independent course card with:

- course title;
- level/module ID;
- guided hours;
- target price;
- Alpha price/status;
- completion credential status;
- diploma applicability;
- launch/open button.

## 13. Pricing-feedback data to collect during Alpha

When Suite Feedback integration is available, ask optional questions after course completion or preview:

- Would you personally pay the displayed target price?
- Too low / fair / slightly high / much too high?
- Would your employer pay?
- Would PDH/CEH eligibility materially increase the value?
- Would you prefer individual purchase, employer bundle or annual Academy access?
- What price would feel fair for this course?

Do not block learning on pricing feedback.

## 14. DHP / specialist-training market benchmark principle

Specialist membrane-training providers such as David H. Paul, Inc. demonstrate that professional water-treatment learners and utilities will pay substantial amounts for recognized, applied technical training, especially when training includes certification, operator relevance and hands-on elements.

Use competitor information only as a market reference. Do not copy course descriptions, certifications, curriculum, branding or proprietary material.

Academy differentiators should be:

- broad water-treatment system coverage rather than RO only;
- engineering reasoning;
- interactive calculations through Total Water Design Suite;
- progressive beginner-to-advanced path;
- cross-discipline integration (process, electrical, controls, commercial/project delivery);
- transparent technical sourcing;
- eventual auditable continuing-education credentials.

## 15. Implementation boundary

This roadmap authorizes Academy to:

- display individual course target prices;
- label Foundation courses as planned permanently free;
- label all Alpha courses as currently free;
- expose future course entitlement keys;
- issue ordinary completion credentials when module authoring is complete;
- collect pricing feedback;
- store CE-readiness metadata.

This roadmap does **not** authorize Academy to:

- charge learners directly;
- build an independent payment gateway;
- bypass Suite Core entitlements;
- claim PDH/CEH/IACET CEU approval before approval exists;
- equate current guided hours automatically to approved PDH;
- represent the Diploma as licensure/accreditation.

## 16. Next implementation milestone

1. Add target price / Alpha-free presentation to Academy course cards.
2. Keep all L01/L02 courses permanently-free in catalog metadata.
3. Define Suite Core granular course-entitlement contract.
4. Add course-completion certificate architecture separate from Diploma.
5. Add `credit_status`, `credit_hours`, `jurisdictions`, `provider_id`, `course_approval_id` and `credit_disclaimer` metadata without making an approval claim.
6. Add Alpha price-feedback capture through the Suite Feedback owner.
7. Build a CE/PDH compliance checklist and record-retention service contract.
8. Select the first engineering jurisdiction(s) and complete provider/course approval work.
9. Consider IACET Accredited Provider readiness once organizational eligibility and quality-system requirements are met.
10. Only after approved: turn on learner-facing PDH/CEH badges and approved credit values.
