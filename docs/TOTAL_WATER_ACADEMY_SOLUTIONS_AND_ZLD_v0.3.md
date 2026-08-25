# Total Water Academy — Solutions, Solution Properties & ZLD Learning Thread v0.3

**Owner:** `app/total-water-academy`  
**Course version:** 0.3.0  
**Guided engagement:** remains 360 hours across ten levels

## Purpose

Total Water Academy should teach physical chemistry as an engineering tool rather than as an isolated chemistry course. Solution behavior is therefore taught progressively and then reused in membrane and ZLD design.

The intended progression is:

`concentration → solution properties → solubility → activity → saturation → membrane concentration → supersaturation → nucleation → crystallization → ZLD`

This gives beginners enough foundation to understand what the Suite is calculating while giving advanced students a route into non-ideal concentrated solutions and industrial crystallization.

## Technical source basis

This curriculum extension was prompted by user-provided photographed excerpts from an authoritative industrial-crystallization reference covering solutions and solution properties. The supplied material includes concepts such as concentration bases, solubility, electrolyte solution behavior, physical properties, diffusion/mass transfer, thermal properties, supersaturation, hydrates and phase behavior.

The Academy uses those concepts as a **content-development basis**, not as copied course text. Scanned pages, long quotations and proprietary book content are not committed to the repository. Academy lessons should paraphrase concepts, add water-treatment context, and progressively cross-check the engineering treatment against additional authoritative references and validated Suite logic.

## Level 2 — foundation

Level 2 introduces solution literacy inside Core Unit Operations, Balances & Transport Fundamentals.

Students should learn:

- concentration bases: mass fraction, mole fraction, molarity and molality;
- how temperature and density affect concentration reporting and process calculations;
- solubility and how to read a basic solubility curve;
- unsaturated, saturated and supersaturated states;
- the difference between analytical concentration and thermodynamic activity;
- activity coefficients and ionic-strength concepts at an introductory level;
- why solution density, viscosity and other physical properties are engineering inputs rather than decorative data;
- how these concepts connect to mass balance, heat transfer and separation operations.

The goal is conceptual fluency plus practical calculation literacy, not advanced electrolyte-model derivation.

## Level 4 — membrane/scaling application

Level 4 reuses the same ideas in RO/NF rather than teaching an unrelated scaling chapter.

Students should connect:

- recovery and concentration polarization;
- local versus bulk concentration;
- activity versus analytical concentration;
- ion-activity products and saturation reasoning;
- common-ion and pH effects;
- why increasing recovery can increase scaling risk nonlinearly;
- why validated Shared Water Chemistry / Total RO Design calculations are required for professional predictions.

This is the bridge from physical chemistry to membrane-design judgment.

## Level 8 — advanced concentrated-brine and crystallization depth

Level 8 revisits the subject at ZLD depth. The student should now be comfortable with the idea that a highly concentrated brine is **not simply dilute water multiplied by a concentration factor**.

Advanced topics include:

- density, viscosity and diffusivity of concentrated electrolyte solutions;
- heat capacity, latent heat, heats of solution/crystallization and enthalpy implications;
- changing transport behavior as concentration increases;
- supersaturation ratio and metastable-zone concepts;
- nucleation and crystal-growth fundamentals;
- hydrate formation and solid-phase stability;
- temperature-composition and phase-diagram reasoning;
- how evaporation changes both thermodynamic and transport constraints;
- why crystallizer selection and ZLD operating strategy depend on phase behavior and solution properties.

## Interactive learning direction

Future authored exercises should make these concepts visible rather than relying on multiple-choice questions alone. Examples:

1. **Concentration ladder:** start with a dilute stream and change water removal while tracking concentration basis and density.
2. **Solubility-curve mission:** heat, cool or evaporate a solution and identify unsaturated, saturated and supersaturated regions.
3. **RO scaling bridge:** increase recovery and observe how concentrate chemistry and saturation tendency change through validated Suite calculations.
4. **Brine-property mission:** compare dilute and concentrated streams and reason about viscosity, diffusivity, pumping and heat-transfer consequences.
5. **Crystallization mission:** move a brine across a solubility boundary, identify supersaturation, then reason about nucleation/crystal-growth control.
6. **Hydrate/phase selection challenge:** interpret a simplified phase diagram and determine which solid phase is stable under given temperature/composition conditions.

## Engineering-authority rule

Academy owns the pedagogy, sequencing, scenarios, hints and explanation. It does **not** own a competing electrolyte, scaling, membrane or crystallizer solver.

Where calculations are authoritative:

- common aqueous chemistry → `engine/shared-water-chemistry`;
- canonical streams / mass flow → `engine/shared-waterstream`;
- plant balances → `app/total-water-balance`;
- membrane application → `app/total-ro-design`;
- brine/ZLD application → `app/total-zld-design`.

Until a validated Academy adapter exists, educational numerical examples must be clearly labeled as teaching assumptions and must not be presented as professional design predictions.

## Future high-quality source intake

Additional advanced references can be incorporated into this same learning-thread architecture. For each new source:

1. identify the engineering concepts it strengthens;
2. map each concept to beginner, applied or advanced depth;
3. connect it to the relevant Suite calculation owner;
4. add practical learning activities rather than only prose;
5. preserve source provenance internally;
6. paraphrase copyrighted material rather than reproducing it;
7. add regression tests for any curriculum structure that should remain stable.

This allows the Academy to grow in technical depth without becoming a disconnected collection of lectures.