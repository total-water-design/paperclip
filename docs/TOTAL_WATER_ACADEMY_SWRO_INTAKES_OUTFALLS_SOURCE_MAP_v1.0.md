# Total Water Academy — SWRO Intakes, Outfalls & Marine Infrastructure Source Map v1.0

Owner: `app/total-water-academy`

## Purpose

This source map strengthens the existing Total Water Academy curriculum with the system boundary that is often under-taught in desalination courses: **how seawater reaches the treatment plant and how concentrate safely returns to the receiving environment**.

The primary supplied reference is:

Thomas M. Missimer, Burton Jones and Robert G. Maliva (eds.), **Intakes and Outfalls for Seawater Reverse-Osmosis Desalination Facilities: Innovations and Environmental Impacts**, Springer, 2015. DOI: `10.1007/978-3-319-13203-7`.

The book is valuable because it links intake/outfall design to:

- feed-water quality and pretreatment intensity;
- plant reliability and availability;
- hydraulics, pumping and surge;
- corrosion, biofouling and long-term maintainability;
- impingement and entrainment;
- coastal geology, hydrogeology and bathymetry;
- environmental permitting and monitoring;
- concentrate diffuser design and mixing;
- near-field and far-field coastal modeling;
- intake/outfall recirculation risk;
- capital cost, construction risk and project schedule;
- integrated SWRO plant design.

The source is from 2015. Regulatory thresholds, named equipment, materials guidance, case-study performance, cost shares, design velocities, screen openings and technology maturity statements must therefore be treated as **source-labelled historical/reference values**, not automatic 2026 TWDS design criteria. Current project requirements must be established from current jurisdictional permits/regulations, current owner criteria, current manufacturer data, current environmental studies and validated TWDS engineering owners where available.

## Core teaching principle

> **The intake is the first treatment barrier, and the outfall is the final engineered environmental interface.**

The student must not think of the desalination plant as beginning at the pretreatment skid and ending at the RO concentrate header.

The Academy should teach the coupled system:

`marine source → intake location/type → conveyance/screens/pumps → pretreatment → RO → concentrate conditioning/conveyance → outfall/diffuser → receiving environment → monitoring`.

Design decisions at either boundary can propagate through the entire plant.

---

# 1. Academy placement

## Level 1 — Water Treatment Foundations & Water Quality

Use intake/outfall concepts to expand the beginner's mental model of a treatment train.

Teach:

- a seawater desalination plant has environmental and hydraulic boundaries beyond the process building;
- the feed-water source is dynamic, not a fixed laboratory bottle;
- intake location can change temperature, suspended solids, algae, bacteria, organics and biofouling risk;
- the concentrate stream remains part of the plant design after it leaves the RO system;
- plant reliability depends on source-water access and disposal as well as process equipment.

### Beginner exercise — “Where does the plant really start and end?”

Give a simplified SWRO block flow and ask the student to add:

1. source-water characterization;
2. intake;
3. screening/conveyance;
4. pretreatment;
5. RO;
6. product-water treatment;
7. concentrate conveyance;
8. outfall/diffuser;
9. receiving-environment monitoring.

**Common misconception:** “The desalination plant starts at pretreatment and ends at the RO skid.”

---

## Level 3 — Pretreatment & Solids Separation

This is the main home for **intake-as-pretreatment** reasoning.

Teach the principal intake families at technology-literacy level:

- conventional shoreline/open-ocean intake;
- offshore intake with velocity cap;
- offshore passive/cylindrical wedgewire screens;
- vertical/beach wells;
- slant/angle wells;
- horizontal wells;
- radial collector wells;
- beach infiltration galleries;
- seabed infiltration galleries;
- tunnel conveyance where applicable.

### Selection dimensions

Students should compare alternatives using original Academy decision matrices based on:

- required reliable capacity;
- source-water quality and variability;
- seasonal algae/jellyfish/debris risk;
- geology/hydrogeology;
- bathymetry and coastal morphology;
- waves, currents and sediment transport;
- impingement/entrainment risk;
- constructability;
- maintainability and access;
- corrosion/biofouling exposure;
- redundancy and expansion;
- pretreatment consequences;
- CAPEX/OPEX and project risk.

Do **not** reproduce the book's comparison tables. Recreate the logic in original TWDA visuals and scenarios.

### Intake affects pretreatment

Make explicit that intake design can change what the downstream pretreatment plant receives.

Examples for teaching:

- open intakes can transmit rapid variations in algae, bacteria, organics and suspended solids;
- passive screens can reduce larger debris and marine-life interactions but do not remove dissolved/colloidal organics simply by having a fine slot;
- subsurface intakes may provide natural filtration and more stable feed quality where geology/hydrogeology permit;
- a better intake does **not automatically eliminate** the need for validated pretreatment design.

### Interactive mission — “Choose the intake before the pretreatment”

Give three sites:

1. high-energy sandy coastline with frequent algae events;
2. rocky coast with deep water and hostile waves;
3. permeable coastal aquifer with suitable hydrogeology.

The student first screens intake families, then sees how the selected intake changes the starting assumptions for Total Pretreatment Design.

### Common Mistake cards

- **“An intake is just a pipe to the sea.”**
- **“Smaller screen slots are always better.”**
- **“Low approach velocity alone guarantees zero entrainment.”**
- **“Passive screens remove the dissolved/colloidal foulants that control RO biofouling.”**
- **“Subsurface intakes are always better.”**
- **“A published intake-selection table is globally transferable without site investigation.”**

---

## Level 4 — Membrane Systems — MF, UF, NF & RO

Use the source to link marine source selection directly to membrane performance.

Teach:

- feed variability and pretreatment stability affect membrane fouling risk;
- algae, bacteria, TOC/NOM, biopolymers and TEP are relevant to biofouling discussions;
- intake depth and location may change water quality, but the effect can be non-monotonic and site-specific;
- lower biological loading at depth does not guarantee a simpler pretreatment train;
- source-water temperature and salinity shifts influence RO hydraulics/osmotic pressure and energy;
- intake reliability affects RO availability even if the membrane design itself is excellent.

### Advanced misconception mission — “Deeper is always cleaner”

Use the Red Sea deep-intake case as a source-labelled case study.

Students predict that deeper water should automatically mean:

- fewer algae;
- fewer organics;
- less pretreatment;
- better RO operation.

Then they examine the actual engineering complications:

- bathymetry and seismic/structural risk;
- temperature/salinity changes;
- irregular TEP/TOC/algae profiles;
- possible biological productivity layers at intermediate depths;
- maintenance/access constraints;
- the finding that observed quality improvements in that case were insufficient to justify a different general pretreatment train.

**Transfer lesson:** never optimize one water-quality variable without checking constructability, maintenance, hydraulics, chemistry and total lifecycle risk.

---

## Level 6 — Pumps, Energy & Electrical Systems

Use seawater intake/outfall infrastructure as a realistic hydraulics and machinery case.

Teach:

- intake pump station duty;
- static head versus friction head;
- screen/conveyance headloss;
- increasing headloss as screens foul;
- long-term roughness and marine growth;
- tunnel/pipeline diameter tradeoffs;
- pumping-energy consequences of intake/outfall siting;
- surge/water-hammer concepts during pump trips;
- wet-well/suction design literacy;
- duty/standby philosophy and maintainability;
- materials/corrosion implications for seawater pumps and fittings;
- cleaning/pigging access as a design input, not an afterthought.

### Interactive mission — “Design for the dirty year, not the clean day”

Students compare the pump head calculated with:

- clean screens and clean conveyance;
- fouled screens;
- conservative long-term roughness;
- seasonal water-level variation.

The goal is not to create a marine hydraulic production solver inside Academy; it is to teach why a pump selected only at clean commissioning conditions may not satisfy lifecycle duty.

### Surge exercise

Use a simplified control-volume/water-hammer teaching problem to show why rapid intake-pump shutdown can create transient water-level/surge problems. Any project-grade transient calculation must come from an approved hydraulic/transient owner or specialist model, not Academy.

---

## Level 8 — Residuals, Brine Management & ZLD

Add a **marine concentrate discharge** branch before students assume every residual stream must go to ZLD.

Teach the principal marine-outfall concepts:

- concentrate density and negative buoyancy;
- outfall siting;
- single-port versus multiport diffuser literacy;
- inclined dense jets;
- diffuser port number/spacing/orientation;
- initial dilution;
- near-field mixing;
- interaction/merging of adjacent jets;
- bottom interaction and re-entrainment;
- density currents;
- far-field transport;
- ambient currents, stratification, bathymetry, waves and wind;
- intake/outfall recirculation risk;
- environmental mixing zones and compliance concepts;
- monitoring and model validation.

### Modeling literacy

Teach **why model selection matters** rather than teaching students to press a button in a coastal model.

Progression:

1. conceptual screening / dimensional reasoning;
2. near-field integral modeling literacy;
3. CFD awareness for complex near-field behavior outside simple-model assumptions;
4. far-field hydrodynamic/water-quality modeling;
5. coupled near-/far-field assessment for complex environments and recirculation;
6. field monitoring to validate assumptions and predictions.

Academy must explain that a near-field dilution result does not by itself prove acceptable far-field environmental performance.

### Interactive mission — “Where did the brine go?”

Students are given:

- concentrate flow and salinity;
- water depth;
- a proposed diffuser;
- two ambient-current cases;
- an intake located downcoast.

They first predict the dense-plume behavior qualitatively. Then they decide which modeling tier is justified and what site data are missing.

Do not generate regulatory-compliance predictions from Academy-owned equations.

### Common Mistake cards

- **“An outfall is just a pipe diameter calculation.”**
- **“High exit velocity automatically guarantees acceptable dilution.”**
- **“More ports always means more dilution.”**
- **“If near-field dilution passes, the environmental assessment is finished.”**
- **“The intake and outfall can be designed independently.”**
- **“A steady uniform current is adequate for every coastal site.”**
- **“ZLD is automatically environmentally preferable to a well-designed marine discharge.”**

The last statement must be handled as a lifecycle/environmental tradeoff, not a universal rule.

---

## Level 9 — Integrated Design, Project Development, Risk & Economics

Use marine works to connect the technical plant with the project-development/commercial track.

Teach that intake/outfall decisions can affect:

- site feasibility;
- permitting schedule;
- environmental baseline-study duration;
- geotechnical/oceanographic investigation scope;
- CAPEX and contingency;
- construction methodology;
- critical path and long-lead marine equipment;
- construction weather windows;
- availability guarantees;
- lifecycle maintenance access;
- redundancy;
- insurance and project risk;
- lender/owner confidence in reliability;
- expansion strategy.

The book includes historical Australian case examples delivered under fast-track design-build/DBOM arrangements. Use them as project-history examples only; do not present them as a universal execution model recommendation.

### Project-development exercise — “The cheapest intake is not the cheapest project”

Compare two options:

- lower first-cost intake with greater algae/debris exposure, maintenance uncertainty and environmental/permitting risk;
- higher-CAPEX intake/tunnel/gallery option with different lifecycle and reliability characteristics.

Students must make a recommendation based on:

`CAPEX + OPEX + availability + schedule + constructability + permitting + environmental risk + maintenance + expansion`.

### Reliability and finance connection

Teach the principle that an unreliable raw-water supply can undermine the feasibility/bankability of an otherwise technically sound desalination plant.

Do not teach historical cost percentages as current estimating factors. They are context for understanding that marine works may be material to total project cost and risk.

---

## Level 10 — Integrated SWRO Capstone

A seawater-desalination capstone should no longer begin at the pretreatment inlet flange.

The student must provide a defensible concept for:

1. source-water characterization and variability;
2. intake technology and siting basis;
3. marine/environmental constraints;
4. screening and raw-water conveyance;
5. intake hydraulics/pumping philosophy;
6. pretreatment basis;
7. RO design using validated Total RO Design;
8. product-water treatment;
9. concentrate characterization;
10. outfall/disposal strategy;
11. diffuser/modeling strategy where marine discharge is selected;
12. intake/outfall recirculation check strategy;
13. monitoring plan;
14. reliability/redundancy/O&M philosophy;
15. project-development, risk and economics implications.

### Capstone defense questions

The student should be able to answer:

- Why is this intake type appropriate for this coastline and plant capacity?
- How does the intake change pretreatment risk?
- What seasonal/extreme events control the design basis?
- How will the intake be cleaned, inspected and maintained?
- What happens if one intake train/screen/pump is unavailable?
- How does long-term fouling/roughness affect hydraulics?
- Why is the proposed outfall concept appropriate for a dense concentrate?
- What near-field and far-field analyses are required?
- Could the discharge recirculate to the intake?
- What environmental baseline and post-commissioning monitoring are required?
- Which assumptions are source-labelled historical examples versus current project requirements?

---

# 2. Intake selection teaching framework

Academy should use an original multicriteria decision tool with dimensions such as:

| Decision dimension | Questions for the learner |
| --- | --- |
| Capacity | Can the intake reliably supply design, peak and future flow? |
| Feed quality | How variable are solids, algae, bacteria, NOM/TEP, temperature and salinity? |
| Geology/hydrogeology | Can wells/galleries produce required flow without adverse groundwater impacts? |
| Bathymetry | What depth/distance is constructible and maintainable? |
| Waves/currents | What loads, sediment transport and cleaning benefits/risks occur? |
| Marine ecology | What are impingement/entrainment and habitat concerns? |
| Pretreatment | Does the intake reduce or increase downstream treatment burden? |
| Hydraulics | What are clean/fouled/lifecycle headloss and surge implications? |
| O&M | Can screens, pipes, tunnels and wells be inspected, cleaned and rehabilitated? |
| Materials | What corrosion/biofouling environment exists? |
| Construction | Trench, seabed pipe, HDD, microtunnel, TBM, wells or gallery? |
| Project risk | Weather window, geotechnical uncertainty, long-lead equipment, permitting? |
| Economics | CAPEX, OPEX, lifecycle maintenance and availability consequences? |

This matrix teaches engineering judgment; it is not a deterministic universal intake-selection algorithm.

---

# 3. Passive-screen teaching framework

Teach the coupled variables rather than a single published velocity number:

- total design flow;
- effective open screen area;
- approach velocity;
- through-slot velocity;
- slot width;
- flow uniformity;
- ambient cross-current;
- debris/biological loading;
- screen fouling allowance;
- headloss;
- material/corrosion/biofouling;
- air-burst or mechanical cleaning;
- distance/depth and maintenance access;
- redundancy during cleaning;
- conveyance and pump interface.

### Critical terminology lesson

**Approach velocity and through-screen/through-slot velocity are not interchangeable.**

Historical regulatory/design values in the supplied book illustrate the terms but must not become current TWDS universal limits.

### Simple educational relationship

For concept teaching only, students may use:

`effective screen area = design flow / selected allowable approach velocity`

provided the lesson immediately explains that real design also requires:

- open-area correction;
- fouling/blockage allowance;
- nonuniform flow distribution;
- slot velocity;
- environmental criteria;
- structural design;
- clean/dirty headloss;
- selected screen technology/manufacturer;
- current site-specific permitting requirements.

This is a Unit Operations teaching relationship, not a complete passive-screen design engine.

---

# 4. Environmental engineering thread

## Impingement versus entrainment

Teach the distinction clearly:

- **impingement** — organisms retained/pinned against a screen by intake flow;
- **entrainment** — smaller organisms pass through the screen and enter the intake/process system.

Students should learn that mitigation depends on more than one variable:

- intake location;
- withdrawal flow;
- screen/slot size;
- approach/through-screen velocity;
- ambient currents;
- species/life stage/morphology;
- behavioral avoidance;
- collection/return system where applicable.

Do not convert U.S. 2014-era regulatory thresholds from the book into globally current rules.

## Environmental baseline and monitoring

Academy should teach a monitoring-plan mindset:

### Before design / baseline

- water quality;
- bathymetry;
- waves/currents/tides;
- sediment transport;
- habitats;
- species/life stages;
- seasonal/diel variability;
- existing discharges and pollution sources.

### Construction

- turbidity/sediment disturbance;
- habitat disturbance;
- marine-construction windows;
- protected species observations;
- permit conditions.

### Operation

- intake impingement/entrainment where required;
- water quality;
- tunnel/pipeline/screen condition;
- biofouling;
- outfall plume/salinity where required;
- benthic/ecological response;
- model validation and adaptive operating measures.

---

# 5. Tunnel and marine-works engineering literacy

Academy should teach why marine civil works often sit on the project's critical path.

Topics:

- bathymetry and seabed geomorphology;
- geotechnical investigation;
- wave climate and extreme conditions;
- currents and construction loads;
- TBM/jack-up/ROV/diver access awareness;
- tunnel profile and diameter;
- pipe/tunnel roughness evolution;
- marine growth;
- cleaning/pigging limitations;
- pumping station integration;
- surge;
- corrosion/material durability;
- design life;
- future expansion;
- redundancy;
- construction sequence and weather windows.

### Common Mistake cards

- **“Use the clean-pipe friction factor for the entire project life.”**
- **“If the tunnel is inaccessible, maintenance can be solved later.”**
- **“The intake pump station can be designed independently of tunnel/screen hydraulics.”**
- **“A larger tunnel only changes CAPEX.”**
- **“Marine construction risk belongs only to the civil contractor, not the process design basis.”**

---

# 6. Outfall modeling literacy framework

## Near field

Students should understand:

- jet momentum and buoyancy;
- dense-jet trajectory;
- entrainment and initial dilution;
- port geometry/orientation;
- water depth;
- bottom/free-surface interaction;
- multiple-jet interaction;
- ambient current.

## Far field

Students should understand why broader circulation matters:

- currents and tides;
- wind;
- bathymetry;
- stratification;
- density currents;
- temporal variability;
- shoreline/coastal geometry;
- recirculation to the intake;
- sensitive habitats.

## Modeling hierarchy

The Academy should ask the student to decide whether the problem needs:

- screening calculations;
- an integral near-field model;
- CFD;
- a hydrodynamic far-field model;
- coupled near-/far-field modeling;
- physical modeling;
- field monitoring/calibration.

Do not teach CORMIX, CFD, Delft3D or another named model as if the software name itself guarantees a correct answer. Teach **model assumptions, applicability, calibration and validation**.

---

# 7. Original interactive exercises

1. **Intake Family Selector** — compare open ocean, passive screen and subsurface options.
2. **The Intake Is Pretreatment** — see how intake quality changes pretreatment design assumptions.
3. **Algal Bloom Day** — determine which intake/pretreatment risks become controlling.
4. **Deeper Is Always Better?** — challenge the misconception using the Red Sea case.
5. **Passive Screen Tradeoff** — flow, effective area, velocity, slot, current, fouling and cleaning.
6. **Approach vs Through-Slot Velocity** — terminology and hydraulic consequences.
7. **Marine Biofouling Lifecycle** — clean versus fouled screen/tunnel hydraulics.
8. **Tunnel Critical Path** — connect marine construction method to schedule/risk.
9. **Pump Trip / Surge Awareness** — qualitative transient consequences and mitigation thinking.
10. **Intake Environmental Review** — impingement/entrainment and baseline-study design.
11. **Build the Concentrate Outfall** — select single/multiport concept and identify required data.
12. **Near Field or Far Field?** — choose appropriate modeling tier.
13. **Diffuser Interaction Detective** — identify when adjacent jets/bed interaction may impair dilution.
14. **Will the Brine Return?** — intake/outfall recirculation reasoning.
15. **Marine Monitoring Plan** — baseline, construction and operating monitoring.
16. **The Cheapest Intake Is Not the Cheapest Project** — lifecycle/project-risk decision.
17. **Sydney / Gold Coast Case Review** — original Academy reconstruction of the design logic, not copied figures.
18. **Capstone Marine Boundary Defense** — student defends intake and outfall as part of complete plant design.

---

# 8. Misconception library

Academy should explicitly call out:

- “The intake is just civil infrastructure.”
- “The outfall is just the last pipe.”
- “Deeper seawater is always better feed water.”
- “A passive screen eliminates pretreatment.”
- “A subsurface intake is feasible wherever there is a sandy beach.”
- “Smaller screen slots are always environmentally and hydraulically better.”
- “Approach velocity and through-slot velocity are the same.”
- “A clean-screen headloss is the lifecycle design headloss.”
- “If impingement is low, entrainment must also be low.”
- “A velocity cap eliminates entrainment.”
- “More diffuser ports always improve dilution.”
- “Near-field dilution proves far-field compliance.”
- “A model result is valid outside the model's assumptions.”
- “Intake and outfall locations can be selected independently.”
- “Historical regulatory values are current global design criteria.”
- “The lowest-CAPEX marine option is the lowest-cost project.”

---

# 9. Engineering authority boundary

At the time of this source-map creation, repository search did not identify a dedicated validated TWDS marine-intake/outfall/coastal-dispersion project-design engine.

Therefore:

## Academy may own

- conceptual intake/outfall selection exercises;
- original diagrams and interactive teaching visuals;
- simplified mass/hydraulic reasoning where clearly labelled educational;
- environmental mechanism explanations;
- model-selection literacy;
- case-study interpretation;
- common-mistake coaching;
- design-basis/checklist exercises.

## Academy must not claim authority for

- project-grade marine intake structural design;
- coastal geotechnical/hydrogeological design;
- final passive-screen sizing or regulatory compliance;
- project-grade tunnel transient analysis;
- marine ecological impact prediction;
- project diffuser sizing/compliance guarantees;
- near-/far-field salinity plume prediction;
- regulatory mixing-zone determination;
- environmental permit compliance.

Where applicable, Academy should use validated TWDS owners for the portions they already own:

- `app/total-pretreatment-design` — downstream pretreatment;
- `app/total-ro-design` — SWRO membrane/hydraulic/energy performance;
- `engine/shared-water-chemistry` — authoritative water chemistry;
- `app/total-water-balance` — plant-wide flow/recycle/reject balances;
- `app/total-zld-design` — alternative brine concentration/ZLD pathways;
- `app/total-water-economics` — project/lifecycle economic comparisons.

A future dedicated marine hydraulics/intake/outfall owner may replace Academy screening approximations with validated adapters.

---

# 10. Source quality and copyright policy

This Springer book is copyright protected.

Academy must:

- cite the book and relevant chapter/authors when concepts materially derive from it;
- paraphrase rather than copy substantial text;
- create original Academy diagrams rather than reproduce publisher figures;
- create original comparison matrices rather than reproduce tables;
- label case-study and historical numerical values with source/year/context;
- revalidate regulatory and project-design limits against current authoritative sources before learner-facing use as current criteria;
- distinguish general engineering principles from site-specific conclusions.

Particular care is required for figures showing:

- intake arrangements;
- velocity caps;
- passive screens;
- tunnel systems;
- coastal maps;
- environmental sampling;
- diffuser/plume modeling.

These should inspire original interactive visuals but must not be copied into TWDA.

---

# 11. Success criterion

A student completing the SWRO marine-infrastructure thread should be able to explain:

1. why intake selection is part of process design;
2. how intake location/type changes pretreatment and RO risk;
3. why geology, oceanography, biology and maintainability affect intake feasibility;
4. the difference between impingement and entrainment;
5. why screen velocity, slot size and ambient current must be considered together;
6. why lifecycle fouling and surge matter to intake hydraulics;
7. how dense concentrate behaves differently from a neutrally buoyant discharge;
8. why diffuser geometry and ambient conditions control initial dilution;
9. when near-field analysis is insufficient and far-field/coupled modeling is needed;
10. why intake/outfall recirculation must be checked;
11. why marine works may control project schedule, CAPEX, risk and financing confidence;
12. which results belong to validated engineering owners rather than Academy.

The desired outcome is that a TWDA graduate sees seawater desalination as a **complete coastal water system**, not only an RO process skid.