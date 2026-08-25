# Total Water Academy — Guided Engineering Solution Mode v1.0

Owner: `app/total-water-academy`

## Purpose

For difficult engineering exercises, Total Water Academy should teach the **method of solving the problem**, not only grade the final answer. Complex practice problems should therefore support a Guided Engineering Solution Mode that walks the learner through a curated, explicit engineering workflow and calls out common mistakes and misconceptions at the point where they normally occur.

This is learner-facing instructional reasoning. It is a deliberately authored explanation of the engineering method, not hidden/internal reasoning and not a substitute for the authoritative Suite calculation engines.

## Where to use it

Use Guided Engineering Solution Mode primarily for advanced practicals and design missions involving multiple linked decisions, for example:

- component and energy balances;
- heat-transfer and mass-transfer problems;
- membrane transport and concentration polarization;
- RO staging, recovery and tail-element risk;
- biological process sizing and interpretation;
- pump/hydraulic/electrical integration;
- PLC/interlock troubleshooting;
- EDI/electromembrane transport;
- brine concentration, crystallization and crystallizer sizing;
- integrated treatment-train and capstone problems.

Simple recall questions do not need this mode.

## Student experience

A difficult practice exercise should normally offer three paths:

1. **Try it yourself** — student solves without guidance.
2. **Give me a hint** — reveal only the next conceptual cue.
3. **Solve it with me** — enter the full Guided Engineering Solution Mode.

The learner should always be able to attempt the problem before the worked path is exposed.

## Standard step-by-step engineering workflow

The guided solution should use a repeatable structure so students build habits they can carry into professional practice.

### Step 1 — Define the design question

State exactly what must be determined and what would constitute an acceptable engineering answer.

**Common mistake callout:** solving for a convenient variable instead of the actual design question.

### Step 2 — Establish the design basis

List feed conditions, product requirements, boundary conditions, assumptions, operating limits and the authoritative Suite inputs.

**Common mistake callout:** starting calculations before confirming the feed basis, temperature, pressure, units, recovery basis or water composition.

### Step 3 — Draw the physical picture / control volume

Show the relevant streams, equipment, driving forces and boundaries using an original Academy diagram.

**Common mistake callout:** losing a recycle, purge, concentrate, vapor, solids or energy stream because it was never placed on the diagram.

### Step 4 — Inventory knowns, unknowns and units

Separate given values, values obtained from validated Suite owners, unknowns and assumptions. Convert units before calculation.

**Common mistake callout:** mixing mass and volumetric flow, mg/L and mass fraction, gauge and absolute pressure, °C and K, kW and kWh, or inconsistent time bases.

### Step 5 — Select the governing engineering principle

Identify the principle before inserting numbers: mass conservation, energy conservation, momentum/headloss, equilibrium, transport, kinetics, electrical power, control logic, population balance, etc.

**Common misconception callout:** choosing an equation because it contains the desired unknown rather than because its assumptions match the physical system.

### Step 6 — Predict the direction before calculating

Ask what should happen qualitatively if the input changes. Examples: increasing recovery should normally increase concentrate salinity; increasing hydraulic resistance should require more pressure for a fixed flux; increasing residence time may allow larger crystals if the assumed growth model is valid.

**Common mistake callout:** accepting a numerically tidy result that contradicts basic physical behavior.

### Step 7 — Calculate using the correct authority

Where a validated Suite engine exists, the guided exercise should call it rather than recreate professional equations in Academy. The lesson should explain what is being calculated and what assumptions matter.

**Common mistake callout:** treating an educational screening equation as a validated project model.

### Step 8 — Interpret the result physically

Explain what the numerical result means for the plant, not merely whether the arithmetic is correct.

**Common misconception callout:** believing that a mathematically feasible result is automatically an operable or safe design.

### Step 9 — Check constraints and close the balances

Run sanity checks appropriate to the problem: mass closure, charge/electroneutrality where relevant, energy closure, pressure hierarchy, equipment limits, saturation/scaling constraints, current/voltage limits, residence time, solids loading, turndown, control permissives, etc.

**Common mistake callout:** stopping at the first converged answer without checking whether it violates another engineering constraint.

### Step 10 — Compare against a common wrong path

Show one realistic wrong solution path and explain:

- why a student might choose it;
- exactly where the reasoning becomes invalid;
- what symptom would reveal the mistake;
- how an engineer would recover.

Do not caricature wrong answers. Use mistakes that practicing engineers and students genuinely make.

### Step 11 — Transfer the lesson

Change one important condition and ask the learner to predict how the solution strategy changes. This prevents memorization of one worked example.

## Common Mistake card schema

Every advanced guided exercise should be able to display a card with:

- **Mistake / misconception**
- **Why it is tempting**
- **Why it fails**
- **How to detect it**
- **How to correct it**
- **Related competency**

Example:

**Mistake:** using bulk RO concentration when checking the membrane-surface scaling condition.

**Why it is tempting:** the bulk concentration is directly visible in the stream table.

**Why it fails:** concentration polarization can make the membrane-surface concentration higher than the bulk concentration.

**How to detect it:** scaling risk appears inconsistent with local flux/recovery or tail-element behavior.

**How to correct it:** use the validated local membrane/chemistry outputs and distinguish bulk from membrane-surface conditions.

## Progressive hint ladder

Hints should be progressive rather than revealing the whole solution at once.

- Hint 1: identify the physical principle.
- Hint 2: identify the relevant control volume / stream / governing variable.
- Hint 3: point to the required Suite result or equation family.
- Hint 4: show the next calculation step.
- Guided mode: show the complete worked solution with misconception callouts.

The system should record hint usage for learning analytics, but hint use during practice must not be treated as failure.

## Assessment policy

### Practice and design missions

Full guided mode may be available. The purpose is learning.

### Module tests

Do not reveal the full worked solution while the attempt is active. After submission, provide a structured step-by-step debrief for missed questions and misconceptions.

### Capstone / final assessment

Require an independent attempt first. After grading, provide an engineering review that identifies the student's reasoning gaps and directs them back to the relevant guided exercises.

## Adaptive behavior

Use placement results, prior attempts and recurring errors to adjust guidance:

- Foundation Builder: more intermediate steps, diagrams and unit checks.
- Engineering Refresher: concise steps with targeted misconception callouts.
- Accelerated Review: fewer scaffolds initially; deeper model/assumption challenges when guidance is requested.

Repeated mistakes should trigger a targeted misconception reminder before the next related problem.

## Domain-specific mistake libraries

Academy should maintain curated mistake libraries. Examples:

### Mass and energy balances

- forgetting a recycle/purge stream;
- mixing mass and volumetric bases;
- assuming steady state when accumulation exists;
- omitting latent heat during evaporation;
- using inconsistent reference states.

### Membranes / RO

- confusing rejection with recovery;
- using feed rather than local/tail conditions;
- ignoring concentration polarization;
- confusing applied pressure with net driving pressure;
- assuming higher recovery is always better;
- comparing membrane ratings without matching test conditions.

### Biological systems

- confusing HRT and SRT;
- treating BOD/COD as interchangeable;
- ignoring oxygen/alkalinity requirements;
- sizing from average load only when peak/design conditions control.

### Pumps / electrical

- confusing head with pressure without density basis;
- reading the wrong point on a pump curve;
- ignoring NPSH/cavitation;
- confusing kW with kWh;
- assuming a VFD removes every motor-starting/protection requirement;
- confusing line and phase quantities in three-phase systems.

### Controls / PLC

- confusing a permissive with an alarm;
- starting equipment without proving upstream/downstream readiness;
- ignoring fail-safe valve state;
- treating PID tuning as a substitute for correct process design.

### EDI / electromembranes

- treating ED and CEDI limiting-current behavior as identical;
- increasing voltage without considering water splitting, precipitation or energy consequences;
- ignoring flow/residence-time tradeoffs;
- treating historical vendor/feed limits as universal current limits.

### Crystallization / ZLD

- sizing a crystallizer from feed flow alone;
- confusing solubility with supersaturation;
- assuming all supersaturation becomes useful crystal growth;
- ignoring secondary nucleation/attrition;
- applying `Lpd = 3 G tau` outside ideal MSMPR/McCabe assumptions;
- ignoring mother-liquor chemistry, impurities, CSD and dewatering requirements.

## UI direction

Use visually distinct but Suite-consistent components:

- **Engineering Step** card
- **Common Mistake** callout
- **Misconception** callout
- **Sanity Check** card
- **Why this matters in a real plant** card
- **Try the next step yourself** checkpoint
- **Show me the next hint** control
- **Solve it with me** control

Do not use shaming language such as “obvious mistake.” Use neutral language such as “common mistake,” “common misconception,” or “check this assumption.”

## Engineering authority boundary

Guided explanations may show equations and educational calculations, but project-grade results must continue to come from the validated specialist owner when one exists. Academy owns the teaching sequence and misconception explanations, not parallel professional solvers.

## Success criterion

A student completing a difficult guided exercise should be able to answer three questions:

1. **What engineering principle did I use?**
2. **What mistake was I most likely to make, and how would I detect it?**
3. **How would I change the approach if the design basis changed?**

That is the desired Academy outcome: not memorizing an answer, but learning a repeatable engineering way of thinking.