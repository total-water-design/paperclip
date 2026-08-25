# Total Water Academy — Engineering PDH Provider Path v1.0

Owner: `app/total-water-academy`

Status: credential/compliance planning; **no current PDH/CEH approval claim**

## Objective

Prepare Total Water Academy so selected professional courses can eventually award continuing-education credit that licensed engineers may legitimately claim where accepted.

The preferred sequence is:

**PDH-ready course architecture → RCEP provider pathway → selected state/jurisdiction verification → optional broader IACET CEU accreditation.**

This document does not authorize any learner-facing statement that Academy courses are currently approved for PDH, CEH or IACET CEU credit.

## 1. Primary engineering path — RCEP

The Registered Continuing Education Program for Engineers and Surveyors (RCEP), managed by the American Council of Engineering Companies (ACEC), is specifically designed for engineering/surveying continuing education and PDH management.

Academy should prepare for RCEP provider registration because the framework aligns well with the product:

- technical engineering content;
- self-paced/on-demand learning;
- defined PDH values;
- qualified developers/instructors;
- learning outcomes;
- course outline;
- assessments for asynchronous learning;
- participant records/transcripts;
- course evaluations;
- professional-development-hour reporting.

### Academy RCEP-readiness data model

Each candidate PDH course should eventually store:

- Academy module/course ID;
- commercial SKU / Suite Core entitlement key;
- course title;
- course purpose;
- intended audience;
- technical discipline;
- functional discipline/category;
- delivery method;
- development date;
- revision date/version;
- learning objectives;
- detailed outline;
- qualified developer/SME credentials;
- instructor/presenter credentials when applicable;
- assessment method;
- passing score;
- learner evaluation;
- validated qualifying duration;
- PDH value only after approved/verified;
- provider/activity number where applicable;
- participant/completion record;
- certificate/transcript identifier;
- jurisdiction acceptance notes.

### Self-paced duration

Do not simply assign the current Academy guided-hour target as PDH.

For self-paced/on-demand activities, duration must be defensible and auditable. The Academy should maintain evidence from pilot learners and actual completion behavior, excluding idle/browser-open time.

Count only meaningful learning activity that supports stated learning objectives.

## 2. State/jurisdiction verification

RCEP recognition is useful but does not eliminate the need to understand each licensing jurisdiction.

Maintain an approval matrix for each target state containing:

- board/provider rules;
- provider registration requirement;
- course approval requirement;
- whether RCEP registration is recognized;
- asynchronous/self-study rules;
- qualifying PDH definition;
- assessment requirements;
- certificate requirements;
- provider reporting requirements;
- learner reporting requirements;
- records-retention requirement;
- ethics/laws special rules;
- approval expiration/renewal dates.

Academy must expose a PDH badge only when the course/jurisdiction combination is supported by this matrix.

## 3. Florida as first engineering-jurisdiction pilot

Florida is a strong first implementation target because the continuing-education framework is explicit and supports professional/technical education beyond the special Florida Laws & Rules requirement.

Architecture should support Florida certificate fields including:

- participant/licensee name;
- PE/license number;
- course number if applicable;
- course topic;
- presenter;
- date of class/completion;
- continuing-education hours awarded;
- brief course description;
- provider identity;
- unique Academy verification token.

Provider/completion records must be retained according to the current Florida requirement in force at the time of delivery.

### Special restriction

The Florida Laws & Rules course is not an ordinary technical course. Do not offer or label a Florida Laws & Rules course for credit until the specific required provider/course approval exists.

## 4. IACET as broader quality/accreditation path

IACET should remain a later or parallel option where broader CEU recognition is commercially useful.

Important distinctions:

- IACET accredits the **provider organization**, not one isolated Academy course;
- applicant eligibility and operating-history requirements apply;
- an IACET CEU is not the same thing as a professional license or engineering-board approval;
- the conventional IACET unit is 1 CEU per 10 qualifying contact hours;
- Academy may not call a course an IACET CEU course before the provider and learning event comply with the applicable requirements.

IACET is therefore a quality/accreditation framework that can complement RCEP/state engineering approval, not replace it.

## 5. Course credit states

Use explicit states in Academy/Suite Core metadata:

- `completion_only`
- `pdh_candidate`
- `rcep_ready`
- `rcep_registered`
- `jurisdiction_review`
- `pdh_eligible_verified`
- `iacet_candidate`
- `iacet_ceu_eligible`
- `expired_or_suspended`

Default for every Academy course is:

`completion_only`

No automated process may promote a course to a professional-credit state merely because a target number of hours exists.

## 6. Learner-facing wording

### Current Alpha

> **Completion certificate architecture. PDH/CEH approval is planned; no professional-development credit is currently claimed.**

### After RCEP/state verification

Use precise language such as:

> **1.0 PDH — RCEP-recognized activity. Verify acceptance with your licensing jurisdiction.**

or, where a state-specific provider/course approval exists:

> **Approved for X PDH in <jurisdiction>, provider/course ID <ID>, valid through <date>.**

Never use:

- approved everywhere;
- universally accepted;
- guaranteed renewal credit;
- accredited engineering course;

unless the exact statement is legally and factually supportable.

## 7. Certificate / transcript architecture

Each professional-credit certificate should be independently verifiable and include, as applicable:

- learner name;
- license number when required;
- Academy course ID/title;
- provider legal name;
- instructor/content director;
- completion date;
- PDH/CEH/CEU value and unit;
- approval/registration identifiers;
- course description;
- unique verification token;
- credit-status disclaimer;
- course version/revision.

Keep course-completion certificates distinct from the full Academy Diploma.

## 8. Anti-gaming requirements for self-paced PDH

A professional-credit course must not grant credit solely from elapsed browser time.

Require a combination of:

- authenticated learner;
- sequential/meaningful content interaction;
- periodic knowledge checks;
- interactive engineering work;
- final assessment;
- minimum passing score;
- plausible active-engagement time;
- anomaly/idle detection;
- completion attestation where required;
- auditable attempt and progress records.

The Academy should be capable of demonstrating why the credited duration is reasonable.

## 9. Recommended launch sequence

### Phase A — now / Alpha

- modular target prices visible;
- all Alpha access free;
- Foundation courses permanently free;
- ordinary course-completion tracking;
- no PDH/CEH claim;
- collect pricing/value feedback;
- complete course content and assessment quality.

### Phase B — PDH readiness

- freeze first 3–5 professional courses;
- formalize outcomes/outlines/assessments;
- establish instructor/SME credential files;
- validate actual learner duration;
- implement course certificates/transcripts;
- implement record retention;
- implement learner evaluations;
- complete RCEP provider readiness review.

Recommended first candidate professional courses:

1. L04-M01 — Membrane Transport and Separation
2. L04-M03 — Concentration Polarization, Activity, Scaling & Fouling
3. L03-M02 — Coagulation, Flocculation, Clarification and DAF
4. L08-M03 — Nucleation, Crystal Growth & Crystal-Size Distribution
5. L07-M03 — PLC Fundamentals, Ladder Logic and Sequencing

These span several engineering disciplines and provide a useful test of the Academy's continuing-education quality system.

### Phase C — registration / jurisdiction pilot

- apply for RCEP provider status;
- verify Florida technical-course pathway;
- add additional states based on commercial demand;
- expose only verified PDH claims.

### Phase D — broader accreditation

- assess IACET eligibility and business value;
- apply only when the organization and quality system meet the current eligibility standard;
- activate IACET CEU language only after accreditation.

## 10. Ownership boundary

Academy owns:

- instructional design;
- course metadata;
- assessments;
- learning records;
- completion/certificate educational logic;
- CE-readiness documentation.

Suite Core owns:

- identity;
- entitlements;
- payment;
- commercial activation;
- user profile/license-number storage contract if centralized;
- secure certificate-verification infrastructure if shared Suite-wide.

Compliance/legal review owns final statements about professional-credit eligibility.
