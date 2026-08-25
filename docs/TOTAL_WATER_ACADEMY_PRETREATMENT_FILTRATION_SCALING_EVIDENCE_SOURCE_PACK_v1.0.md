# Total Water Academy — Pretreatment, Filtration, Coagulation & Scaling Evidence Source Pack v1.0

Owner: `app/total-water-academy`

Status: educational/source architecture

## Purpose

This source pack strengthens Total Water Academy with additional material on:

- coagulation and flocculation;
- organic polyelectrolytes;
- granular-media and multi-media filtration;
- filter media selection and backwashing;
- cartridge/depth filtration;
- catalytic oxidation media;
- pathogen removal through coagulation/filtration;
- chlorine/NOM/bromide/disinfection-by-product chemistry;
- RO scaling and antiscalant mechanisms;
- induction time / nucleation inhibition;
- evidence-based evaluation of vendor and emerging technology claims.

The supplied material is deliberately treated as a **mixed-evidence source pack**. It contains peer-reviewed papers, government/agency research reports, operator-training material, manufacturer data sheets, historical membrane-vendor guidance and research/innovation studies.

The Academy must therefore teach not only the water-treatment content, but also **how an engineer judges the strength and applicability of a source**.

---

# 1. Evidence-classification contract

Every technical claim derived from this source pack must be classified internally before it becomes learner-facing content.

Use the following labels.

## 1.1 `FUNDAMENTAL_PRINCIPLE`

A well-supported physical, chemical or engineering principle that is sufficiently general to teach without attaching it to one product or plant.

Examples from this pack include:

- particle attachment to granular media is not explained by simple sieving alone;
- polymer bridging and charge neutralization are distinct coagulation mechanisms;
- filter head loss tends to increase as solids accumulate;
- backwashing must provide enough hydraulic/mechanical action to detach retained solids without unacceptable media loss;
- free chlorine reacts with natural organic matter and can form disinfection by-products;
- chlorine speciation between HOCl and OCl- is pH dependent;
- bromide changes halogenation chemistry;
- higher RO recovery generally increases concentration of retained solutes and therefore can increase scaling risk;
- antiscalants can inhibit nucleation and/or crystal growth without eliminating thermodynamic supersaturation;
- tail-end RO elements can experience higher inorganic-scaling risk than lead elements because feed becomes progressively concentrated.

Fundamental principles may be taught strongly, but the Academy should still state important assumptions and boundaries.

## 1.2 `PEER_REVIEWED_FINDING`

An observation or interpretation supported by a peer-reviewed study or review.

It may be technically strong while still being condition-specific.

Required learner wording where numerical values matter:

> “In the conditions studied…”

or equivalent.

A peer-reviewed number is **not automatically a universal design criterion**.

## 1.3 `AGENCY_CASE_STUDY`

A field/pilot result published by a government, research centre, utility or other credible agency.

These are valuable because they show actual engineering behavior, but the result remains tied to:

- source water;
- process configuration;
- membrane/media/product;
- temperature;
- chemistry;
- operating history;
- instrumentation;
- test protocol.

Never convert one successful dose, recovery, loading or operating point into a general rule.

## 1.4 `PRODUCT_SPECIFICATION`

A physical/property value that applies to the named manufacturer's product at the date/version of the data sheet.

Examples:

- the stated effective size of a named grade of anthracite;
- the stated specific gravity of a named garnet product;
- a manufacturer's nominal product mesh range;
- a stated product certification.

It may be factual **for that product/version**, but must not be generalized to all anthracite, all garnet or all filter media.

## 1.5 `VENDOR_RECOMMENDATION`

A manufacturer's suggested operating range, design criterion, chemical dose, media proportion, filtration rate, backwash rate, trigger or process arrangement.

These values are useful to teach how technical data sheets are read, but must remain labelled as manufacturer guidance unless independently validated.

Examples in this pack that MUST NOT become universal Academy rules include:

- fixed multimedia service-flow ranges;
- fixed backwash rates;
- fixed bed-depth percentages;
- fixed SDI/turbidity triggers for selecting multi-media filtration;
- a universal cartridge sequence such as 20 µm → 5 µm → 1 µm;
- a universal garnet/anthracite/sand proportion;
- a fixed GreensandPlus chlorine-contact time or loading criterion;
- historical FilmTec LSI/S&DSI antiscalant operating limits;
- historical SHMP dosing guidance;
- historical recovery cutoffs for when antiscalant should be used.

## 1.6 `HISTORICAL_PRACTICE`

A design or operating recommendation from older manuals/training material that is useful for context but may no longer represent current practice.

Historical practice should help students understand *why* current engineering developed as it did, but cannot be silently presented as 2026 TWDS design guidance.

## 1.7 `RESEARCH_OR_INNOVATION_CASE`

A promising mechanism, laboratory method, natural coagulant, emerging process or technology requiring additional validation before production adoption.

Academy should teach:

- hypothesis;
- evidence;
- test conditions;
- limitations;
- scale-up questions;
- safety/regulatory questions;
- technology readiness.

## 1.8 `CLAIM_REQUIRING_VERIFICATION`

A commercial or technical claim for which the supplied source does not provide enough independent evidence for Academy to teach it as fact.

The appropriate Academy behavior is to ask:

- What is the mechanism claimed?
- What evidence supports it?
- Is there a control?
- Is the study independent?
- Is the effect statistically/operationally meaningful?
- Does it apply to the actual water?
- Has it been validated at relevant scale?

---

# 2. Rule-of-thumb safeguard

The Academy must avoid converting convenient numbers into false universal rules.

## 2.1 Numerical statement hierarchy

A numerical value may be presented as a **current project-grade design criterion** only when supported by the appropriate current authoritative source and/or validated Suite owner.

Otherwise use one of these forms:

- “The study reported…”
- “The manufacturer recommends for this product…”
- “This historical manual used…”
- “The operator-training example assumes…”
- “In this pilot…”
- “One possible starting range is shown here; verify with current design authority.”

## 2.2 Never use “rule of thumb” to hide missing engineering

The phrase “rule of thumb” should not be used as a substitute for:

- media-fluidization calculations;
- bed-expansion curves;
- current vendor data;
- pilot testing;
- source-water characterization;
- membrane projection;
- scaling/speciation calculation;
- jar testing;
- regulatory criteria;
- hydraulic design;
- validated Suite calculations.

## 2.3 Facts still require context

Even a real physical fact may have conditions.

Example:

**Simplified statement:** At 50% RO recovery the concentrate is twice the feed concentration.

**Correct teaching:** For a non-permeating solute in an idealized mass balance with negligible losses and essentially complete rejection, a 50% water recovery gives an approximate concentration factor of 2. Real RO systems require component mass balance and membrane transport.

This teaches both the useful concept and the assumption.

---

# 3. Supplied source register and allowed use

## 3.1 Bolto & Gregory (2007) — Organic polyelectrolytes in water treatment

**Source type:** peer-reviewed review, *Water Research*.

**Academy strength:** HIGH for coagulation/flocculation and polymer fundamentals.

Use strongly for:

- cationic, anionic and nominally non-ionic polymers;
- molecular weight and charge density;
- polymer conformation;
- ionic-strength effects on polyelectrolyte coils;
- adsorption to particle surfaces;
- trains, loops and tails concept;
- polymer bridging;
- charge neutralization / electrostatic patch concepts;
- kinetic aspects of adsorption and flocculation;
- interaction with dissolved organic matter;
- polymer shear degradation;
- dose sensitivity;
- residual polymer;
- polymer toxicity/environmental fate;
- filter backwash-water/sludge implications;
- monitoring/streaming-current concepts.

### Core engineering lesson

> **Polymer selection is not “cationic is good” or “higher molecular weight is better.” Performance depends on charge, molecular architecture, water chemistry, particles, NOM, mixing and dose.**

### Common Mistake

**Mistake:** “If some polymer improves flocculation, more polymer will improve it further.”

**Why it fails:** Under- and overdosing can both degrade performance; excess polymer can re-stabilize particles, carry into filters, increase head loss and affect residuals.

### Academy exercise — Polymer mechanism detective

Students receive:

- particle charge;
- pH;
- ionic strength;
- polymer molecular weight;
- charge density;
- dose trend;
- zeta/streaming-current trend;
- observed floc structure.

They determine whether bridging, charge neutralization or another mechanism is most consistent with the evidence.

---

# 4. Granular-media filtration — principles versus product sheets

Supplied sources include:

- an operator-training Filtration chapter;
- Clack Anthracite data;
- Clack Garnet data;
- International Garnet technical material;
- Puretec Multi-Media Filtration material.

These should be used together deliberately.

## 4.1 Strong general principles

Teach:

- deep-bed filtration is more than geometric straining;
- attachment/adsorption and prior coagulation strongly influence capture;
- coarse-to-fine grading in the direction of flow can increase solids storage compared with a bed that captures most solids at the surface;
- multi-media designs use differences in **particle size and media density** so the bed can re-stratify after backwash;
- anthracite is relatively low density and can be used as an upper/coarser layer;
- garnet is high density and can be used as a lower/finer layer;
- head loss and effluent quality evolve during a filter run;
- poor coagulation can create poor filtration even if the filter vessel itself is mechanically sound;
- backwash performance is part of filter design, not an O&M afterthought;
- underdrain distribution, wash-water trough geometry, air scour/surface wash and freeboard affect cleanability;
- abrupt flow changes can disturb a loaded bed and increase particle breakthrough;
- filter-to-waste after backwash can be necessary until stable effluent quality is restored;
- ineffective backwash can produce mudballs, compaction, cracking, channeling and media loss.

## 4.2 Important correction — filtration is not simply a sieve

The operator-training source explicitly emphasizes that many particles are smaller than media-grain voids and that attachment/adsorption mechanisms are critical.

Academy should visually contrast:

**screening/straining** versus **deep-bed attachment**.

### Interactive — Follow the Particle

The student follows four particles through a bed:

1. large particle removed near bed entrance;
2. smaller destabilized floc attached deeper in the bed;
3. stable colloid that passes because coagulation was poor;
4. retained particle released after a sudden hydraulic surge.

---

# 5. Media properties — teach the physics, not one recipe

## 5.1 Effective size and uniformity coefficient

Teach the meaning of:

- effective size;
- grain-size distribution;
- uniformity coefficient;
- bulk density;
- specific gravity;
- hardness/attrition;
- shape/angularity;
- acid solubility where relevant.

Use the named anthracite/garnet product sheets as **datasheet-reading examples**.

## 5.2 Density and re-stratification

Students should understand why lower-density coarse media can remain above higher-density fine media after an appropriately designed backwash.

Do not teach a fixed anthracite:sand:garnet depth fraction as universal.

### Common Mistake

**Mistake:** “A multi-media filter is always 55% anthracite, 30% sand and 15% garnet.”

**Correction:** That is a source/manufacturer recommendation found in some literature, not a universal law. Actual media grading is selected from required filtration behavior, media properties, underdrain limits, backwash hydraulics, water temperature, available backwash flow and source-water characteristics.

### Interactive — Design the bed from properties

Instead of selecting a canned bed recipe, students receive candidate media with:

- effective size;
- specific gravity;
- UC;
- bed depth;
- expansion curves;
- source-water particle distribution.

They choose and justify the layering.

---

# 6. Backwash — replace fixed flow rules with fluidization reasoning

Several supplied manufacturer/training documents provide fixed backwash flow ranges.

Academy should use these only as examples.

The general lesson is:

> **Required backwash rate depends on the media, grain size/density, desired bed expansion, water temperature/viscosity, bed configuration, air-scour strategy and underdrain limits.**

Teach students to read a manufacturer bed-expansion curve and interpolate at the actual water temperature.

### Common Mistake

**Mistake:** “Backwash every filter at 15 gpm/ft².”

**Why it fails:** The same flow can under-expand one bed and eject media from another.

### Interactive — Cold Morning Backwash

Give the student the same filter in warm and cold water.

Ask:

- what changes physically;
- how viscosity affects expansion;
- whether the same pump setpoint produces the same expansion;
- what should be observed or measured before changing the operating setpoint.

---

# 7. Filter run termination — multi-signal engineering

The operator-training material provides a useful non-numerical principle:

> **Do not decide to backwash from only one signal.**

Academy should teach a multi-signal decision using, as applicable:

- terminal head loss;
- effluent turbidity/particle breakthrough;
- filter run time;
- upstream water-quality change;
- downstream process sensitivity;
- available wash-water inventory;
- plant flow distribution;
- media condition.

Any exact headloss, turbidity or run-time threshold in the supplied training/vendor material remains historical/site-specific.

### Interactive — Backwash Now?

Present four filters:

- high head loss / good effluent;
- low head loss / rising turbidity;
- moderate head loss / sudden raw-water spike;
- long run / stable performance.

Require the student to explain which information is missing before acting.

---

# 8. Cartridge/depth filtration

The GE technical bulletin is useful for terminology and process reasoning.

## 8.1 Nominal versus absolute rating

Teach that “5 micron” is incomplete without understanding the rating method and retention efficiency.

- A **nominal rating** is manufacturer/test dependent and represents a stated retention performance under a defined challenge.
- An **absolute rating** should be tied to a stated efficiency and test condition.

Do not teach nominal and absolute cartridges as directly interchangeable.

## 8.2 Smaller is not automatically better

A tighter cartridge can:

- capture smaller particles;
- increase pressure drop;
- reduce dirt-holding life;
- require larger area or more frequent replacement;
- shift OPEX and waste generation.

Staged coarse-to-fine filtration is one possible strategy.

### Important safeguard

A cartridge micron rating by itself must **not** be presented as a validated microbial barrier or pathogen log-removal credit.

The claim that a particular cartridge “removes most bacteria” cannot be generalized without defined absolute efficiency, integrity and relevant validation.

### Interactive — Nominal 5 µm vs Absolute 5 µm

Students compare two datasheets and discover that the same headline micron number does not establish equivalent retention.

---

# 9. Catalytic oxidation media — GreensandPlus as a product case

The supplied GreensandPlus document is a manufacturer technical data sheet.

Use it to teach:

- catalytic oxidation media concept;
- manganese-dioxide-coated media;
- oxidation of soluble Fe/Mn before/at the media surface;
- coupling of oxidation chemistry and filtration;
- oxidant demand;
- media regeneration/conditioning concepts;
- breakthrough and run-length reasoning;
- importance of pH and source-water chemistry;
- backwash/bed-expansion design;
- arsenic/radium removal through association with precipitated Fe/Mn as a **product/application case**.

Do not convert its stated:

- service-flow range;
- pH range;
- chlorine contact time;
- oxidant-demand formula;
- loading capacity;
- bed depth;
- backwash rate;

into generic manganese-media design values.

### Interactive — What is the media actually doing?

Student identifies whether the dominant function is:

- adsorption;
- catalytic oxidation;
- precipitation;
- filtration of precipitate;
- or a combination.

---

# 10. Natural coagulant research — Opuntia spp.

Miller et al. (2008), *Environmental Science & Technology*, is a useful peer-reviewed **research/innovation case**.

Strong teaching value:

- natural coagulants;
- zeta potential;
- adsorption/bridging;
- dose dependence;
- pH effects;
- distinction between mechanism hypothesis and demonstrated performance;
- comparison of floc morphology;
- technology readiness and scale-up.

The study supports the interpretation that Opuntia coagulation in its tested synthetic waters was more consistent with adsorption/bridging than simple charge neutralization.

Do NOT teach:

- the study's optimum dose as a field design dose;
- its synthetic-water removal as guaranteed natural-water performance;
- Opuntia as an approved drinking-water coagulant;
- safety merely because the cactus is edible.

The paper itself identifies the need to confirm residual-health questions and evaluate natural waters/NOM.

### Interactive — Research to Plant Gate Review

Student receives the paper result and must list what would still be required before full-scale adoption:

- actual source-water tests;
- NOM effects;
- active-agent consistency;
- microbiological consequences of added organics;
- product preparation/stability;
- residuals;
- toxicity;
- regulatory acceptance;
- dose control;
- sludge characteristics;
- economic/logistics assessment.

---

# 11. Cryptosporidium — barrier thinking, not “disinfect harder”

The CRC for Water Quality and Treatment Research Report 3 (2000) is useful agency/research material.

Teach strongly:

- Cryptosporidium oocysts are resistant to conventional chlorine/chloramine disinfection;
- successful control depends on physical removal and an integrated treatment-barrier strategy;
- coagulation influences downstream flocculation, sedimentation and filtration;
- pathogen-removal performance depends on water quality and process optimization;
- pH, NOM, turbidity, coagulant chemistry and dose can affect floc formation/removal.

Do not use its historical jar-test doses as modern design criteria or regulatory log-removal credits.

### Common Mistake

**Mistake:** “If chlorine residual is high enough, coagulation quality is less important.”

**Correction:** Different pathogens have very different disinfectant susceptibility. Barrier design must account for the organism and the demonstrated removal/inactivation mechanism.

### Interactive — Build the Barriers

Students receive a raw-water pathogen risk and must distinguish:

- removal barriers;
- inactivation barriers;
- monitoring surrogates;
- regulatory validation requirements.

---

# 12. Chlorine, NOM, humics and bromide — authoritative chemistry layer

The supplied WHO Environmental Health Criteria material is used as a chemistry reference, while recognizing that much of its context is drinking-water disinfection rather than SWRO pretreatment.

## 12.1 Strong chemical principles

Teach:

- chlorine demand can be consumed by reducing species and organic matter;
- Cl2 hydrolyzes in water to HOCl;
- HOCl ⇌ H+ + OCl-;
- the HOCl/OCl- distribution is pH and temperature dependent;
- HOCl is generally the more potent disinfecting species;
- NOM provides organic precursor material for chlorination DBPs;
- bromide can be oxidized by chlorine to reactive bromine species;
- brominated and chlorinated DBP speciation depends on source-water chemistry and operating conditions;
- DBP formation depends on multiple variables, including organic precursor concentration/character, bromide, dose, pH, temperature and contact time;
- precursor removal before chlorination can reduce DBP formation.

## 12.2 Complement to Khan et al. chlorination school-of-thought note

This chemistry source should prevent the Academy from reducing the chlorination debate to “chlorine works” versus “chlorine does not work.”

Students should analyze simultaneously:

- disinfection objective;
- oxidant demand;
- contact time;
- residual;
- hydraulic accessibility;
- membrane compatibility;
- NOM/AOM/TEP;
- bromide;
- DBPs;
- dechlorination;
- downstream biological regrowth;
- discharge/environmental impacts.

### Common Mistake

**Mistake:** “A chlorine dose of 1 mg/L means the process received 1 mg/L of disinfecting chlorine.”

**Correction:** Dose, demand, residual, speciation and contact time are different concepts.

## 12.3 Alternative oxidants are tradeoffs too

The source can be used to teach that chlorine dioxide, chloramine and ozone each have different benefits and by-products.

Do not present any alternative oxidant as a consequence-free replacement.

---

# 13. Historical FilmTec scale-control manual — what to use and what not to use

The two supplied `0901b80380033f98...` files are duplicate/near-duplicate excerpts from a historical FilmTec scale-control technical manual (published 2000).

Treat them as one source.

## 13.1 Useful enduring concepts

Use for:

- concentration and scaling risk;
- sparingly soluble salts;
- carbonate equilibrium and acid addition;
- the tradeoff of sulfuric acid adding sulfate;
- scale inhibitors and threshold inhibition;
- SHMP hydrolysis risk;
- antiscalant/coagulant compatibility concerns;
- ion exchange / lime softening as alternative scale-control approaches;
- reducing recovery as a last-resort operational lever;
- case-by-case cleaning philosophy.

## 13.2 Historical/vendor values — DO NOT promote

Do not silently use as current defaults:

- stated LSI/S&DSI limits with inhibitor;
- stated SHMP concentrate/feed dosage;
- stated SWRO recovery range as a universal current limit;
- recommendation to use inhibitor above a particular recovery;
- historical ion-exchange capacity/application cutoffs;
- specific pH guidance tied to historical membrane products;
- specific cleaning intervals.

Where useful, present them as:

> “Historical FilmTec guidance (2000) stated… Current design must use current membrane/antiscalant guidance and validated TWDS chemistry.”

### Common Mistake

**Mistake:** “It is in a membrane manufacturer manual, therefore it is a timeless membrane limit.”

**Correction:** Vendor manuals are authoritative for the products and era they cover, but membrane formulations, antiscalants, projection methods and supplier limits evolve.

---

# 14. Antiscalant mechanism — induction time and crystal growth

The supplied Amjad & Hooley (1994) paper, *Effect of Antiscalants on the Precipitation of Calcium Carbonate in Aqueous Solutions*, is useful mechanistic laboratory evidence.

Use to teach:

- induction/lag time before precipitation;
- nucleation and crystal growth as kinetic phenomena;
- sub-stoichiometric inhibitor action;
- effect of antiscalant concentration;
- influence of polymer molecular weight;
- functional-group effects;
- temperature dependence;
- why two polymers at the same ppm may not have the same inhibition performance.

The laboratory ranking of the tested products/chemistries must **not** become a universal antiscalant ranking.

The ppm values used in the controlled experiment must **not** become RO feed-dose guidance.

### Cross-link to crystal-science thread

This paper is an excellent bridge:

**Level 2:** induction time / nucleation / precipitation kinetics

→

**Level 4:** RO antiscalant and membrane scaling

→

**Level 8:** deliberate supersaturation and crystallization.

### Interactive — Delay is not equilibrium

Students see the same supersaturation with different induction times and learn:

> A solution can be thermodynamically supersaturated while precipitation is kinetically delayed.

That distinction is central to both antiscalant use and crystallizer design.

---

# 15. Bureau of Reclamation high-recovery study — evidence beats marketing

The 2003 Bureau of Reclamation study evaluated magnetic and high-voltage capacitance devices against chemical scale control in a specific high-recovery RO pilot configuration.

## 15.1 What Academy may say strongly

In the tested Yuma/MODE system:

- the tested magnetic device did not prevent observed CaSO4 scaling at the high-recovery condition;
- the tested high-voltage capacitance device also did not prevent observed CaSO4 scaling;
- the study's SHMP condition avoided scaling at a somewhat higher recovery during that test program;
- tail-end element performance provided an early/sensitive scaling signal.

## 15.2 What Academy must NOT say

Do not turn this into:

- “all magnetic treatment is impossible”;
- “all electrostatic/capacitance treatment is fraudulent”;
- “2 mg/L SHMP always permits 93% recovery”;
- “93% recovery is safe with SHMP”;
- “SHMP is always the best antiscalant.”

Those conclusions exceed the experiment.

## 15.3 High-value engineering lesson

> **A mechanism claim or vendor testimonial does not replace controlled testing on the actual scaling system.**

### Interactive — Would You Buy the Device?

Give students:

- vendor claim;
- proposed mechanism;
- control test;
- device test;
- normalized tail-element WTC/STC/ΔP;
- autopsy result.

Ask them to decide what the data support and what they do not support.

This becomes part of Academy's broader **engineering evidence literacy**.

---

# 16. Tail-element monitoring and spatial diagnostics

A particularly useful insight from the Bureau of Reclamation work is the value of spatially resolved membrane monitoring.

Academy should connect this to existing Total RO Design tail-element education.

Teach that:

- lead elements can see the highest feed foulant loading and may be vulnerable to particulate/organic/biological fouling;
- tail elements see the most concentrated feed and can be vulnerable to scaling;
- train-average normalized data can hide a local problem;
- element-level sampling/profiling can detect mechanisms earlier.

Do not claim every system requires identical instrumentation; teach the diagnostic principle and cost/complexity tradeoff.

---

# 17. Evidence literacy as an Academy competency

This source pack should create a new cross-course competency:

## `ENG-EVIDENCE-01 — Distinguish evidence strength and applicability`

The learner can distinguish:

- physical principle;
- current standard/design authority;
- peer-reviewed result;
- government pilot result;
- historical practice;
- manufacturer recommendation;
- product specification;
- hypothesis;
- advertising claim.

## `ENG-EVIDENCE-02 — Avoid unsupported extrapolation`

The learner can explain why:

- a jar-test dose is not a plant dose;
- a product sheet flow range is not a universal filter rate;
- one water's antiscalant dose is not another water's dose;
- an absolute/nominal cartridge rating needs test context;
- a successful pilot outside the design season may not cover the design event;
- a manufacturer statement from 2000 may not represent current 2026 limits;
- statistical correlation is not automatically mechanism;
- mechanistic plausibility is not proof of full-scale efficacy.

## `ENG-EVIDENCE-03 — State assumptions`

The learner explicitly identifies assumptions behind simplified calculations.

---

# 18. Academy placement

This pack strengthens existing hours; it does not add hours to the 360-hour curriculum.

## Level 1

- source-water particles, NOM and pathogens;
- why clear water can still be difficult water;
- treatment barriers.

## Level 2

- colloid stability;
- adsorption;
- zeta potential;
- polymer conformation;
- bridging / charge neutralization / sweep floc;
- deep-bed filtration mechanisms;
- induction time / nucleation kinetics;
- chlorine speciation and reaction fundamentals.

## Level 3

- coagulation/flocculation;
- polymer selection and monitoring;
- conventional/direct filtration;
- multi-media filtration;
- anthracite/sand/garnet selection principles;
- filter hydraulics and backwashing;
- cartridge/depth filtration;
- GreensandPlus as a catalytic-media case;
- Opuntia as a research/innovation case;
- Cryptosporidium barrier case.

## Level 4

- RO scaling;
- antiscalant kinetics;
- historical versus current membrane guidance;
- tail-element diagnostics;
- cartridge-filter protection;
- antiscalant/coagulant compatibility.

## Level 7

- streaming-current / charge-monitoring concepts;
- headloss/turbidity/run-time filter-control logic;
- backwash permissives;
- tail-element alarm/trend interpretation;
- evidence-driven operator response.

## Level 8

- polymer/sludge residuals;
- backwash recycle/waste;
- DBP/environmental chemistry;
- precipitation kinetics link to crystallization.

## Level 9

- technology selection under uncertainty;
- pilot-test planning;
- vendor technical evaluation;
- performance guarantees and evidence requirements.

## Level 10

Require the student to identify the **basis of design** for each important numerical criterion in the capstone.

The design defense should be able to answer:

> “Where did this number come from, and why is it applicable here?”

---

# 19. High-value interactive exercises

1. **Fact, Study Result or Vendor Recommendation?**
2. **Design the Multi-Media Bed from Properties**
3. **Cold Morning Backwash**
4. **Backwash Now? Multi-Signal Decision**
5. **Nominal vs Absolute Cartridge Detective**
6. **Polymer Mechanism Detective**
7. **Polymer Overdose Incident**
8. **Streaming-Current Control Lab**
9. **Cryptosporidium Barrier Builder**
10. **Natural Coagulant Technology-Readiness Review**
11. **Chlorine Demand / DBP Precursor Map**
12. **Historical Manual or Current Limit?**
13. **Delay Is Not Equilibrium — Antiscalant Induction Lab**
14. **Would You Buy the Scale-Control Device?**
15. **Lead vs Tail Element Diagnostic Mission**
16. **Capstone Basis-of-Design Defense**

---

# 20. Reusable misconception library

## Filtration

**“A filter works because particles are bigger than the pore spaces.”**

Correction: deep-bed filtration includes attachment/adsorption and is strongly affected by coagulation and surface interactions.

**“Smaller filter media always means better filtration.”**

Correction: retention, headloss, solids storage, cleanability and backwash requirements trade off.

**“A fixed backwash flow works for every filter.”**

Correction: media properties and temperature determine fluidization/expansion behavior.

**“Backwash when ΔP reaches one universal number.”**

Correction: termination should consider multiple signals and site design limits.

## Coagulation

**“More coagulant/polymer is always safer.”**

Correction: overdosing can reduce performance, increase residuals and create downstream filtration problems.

**“Zero zeta potential is always the objective.”**

Correction: the optimal mechanism depends on coagulant and separation process; bridging can occur without charge neutralization.

## Cartridge filtration

**“5 µm is 5 µm regardless of cartridge.”**

Correction: nominal/absolute rating and efficiency/test method matter.

**“A 1-µm cartridge is automatically a pathogen barrier.”**

Correction: pathogen credit requires validated removal performance and integrity, not headline micron rating alone.

## Chlorination

**“Dose = residual = effective CT.”**

Correction: demand, speciation, residual, hydraulics and contact time differ.

**“Alternative disinfectants have no by-products.”**

Correction: each oxidant/disinfectant has distinct chemistry and potential by-products.

## Scaling

**“Supersaturation means precipitation happens immediately.”**

Correction: precipitation has kinetics and an induction time.

**“Antiscalant makes a supersaturated solution unsaturated.”**

Correction: many antiscalants act kinetically; thermodynamic supersaturation may remain.

**“A successful antiscalant dose from one pilot is a universal dose.”**

Correction: dose depends on water chemistry, recovery, temperature, membrane system, formulation and operating conditions.

**“A plausible non-chemical scale-control mechanism proves the device works.”**

Correction: engineering claims require controlled evidence at relevant conditions.

---

# 21. Current-design boundary

This source pack changes **Academy pedagogy and technical depth only**.

It does not authorize Academy to set production design criteria for:

- coagulation dose;
- polymer dose;
- multimedia filter loading;
- media depths;
- backwash rate;
- bed expansion;
- cartridge rating;
- catalytic-media sizing;
- disinfection dose/CT;
- RO recovery;
- antiscalant dose;
- scaling limit;
- membrane cleaning frequency.

Production values remain with current authoritative references, current supplier guidance where appropriate, pilot testing and validated TWDS owners including:

- `app/total-pretreatment-design`;
- `app/total-ro-design`;
- `engine/shared-water-chemistry`;
- other assigned specialist owners.

---

# 22. Provenance and copyright

Where any of these supplied sources materially informs a learner-facing lesson, Academy should identify it in **Research Basis / Sources & Further Reading**.

Do not reproduce copyrighted:

- manual pages;
- manufacturer brochure layouts;
- figures;
- photographs;
- charts;
- tables;
- paper figures;
- long passages.

Build original TWDA diagrams, animations and exercises.

Product names may be used when discussing the specific product/source, but Academy should prefer generic engineering terminology for general lessons.

---

# 23. Source-age safeguard

The supplied documents span roughly 1994–2013/2014 and include older product manuals and training material.

Do not label this pack as the complete **2026 state of the art**.

For future finished lesson authoring:

- retain these sources for mechanisms, historical context and case studies;
- supplement key numerical/current-practice claims with newer authoritative sources;
- use current manufacturer documentation when teaching a current product;
- use current regulations when discussing compliance;
- use validated TWDS calculations for project-grade engineering.

---

# 24. Completion standard for future lesson authoring

A finished lesson derived from this pack should be considered complete only when it:

1. states the engineering principle;
2. identifies important assumptions;
3. identifies the evidence class of numerical claims;
4. labels historical/vendor/case-study values appropriately;
5. includes at least one misconception/counterexample;
6. uses original Academy visuals;
7. cites materially used sources;
8. hands project calculations to the correct Suite owner;
9. avoids unsupported universal rules;
10. asks the learner to defend *why* a chosen criterion applies to the actual design.

This document is **content/source architecture**, not proof that every learner-facing screen has already been authored.