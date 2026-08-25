# Total Water Academy — UF/MF Membrane Water Treatment Source Map v1.0

## Source

Graeme K. Pearce, *UF/MF Membrane Water Treatment: Principles and Design*, Water Treatment Academy / TechnoBiz, Bangkok, 2011, ISBN 978-616-90836-3-4.

User-supplied photographs reviewed for this source map cover approximately pages 21–93, spanning late Chapter 1 and most of Chapter 2.

## Evidence classification

Treat this book as a **HIGH_QUALITY_EXPERT_PRACTITIONER_REFERENCE** for UF/MF fundamentals, terminology, process architecture, fouling/cleaning concepts, operating philosophy and historical industry practice.

It is not a substitute for:

- current manufacturer design manuals;
- current membrane integrity requirements;
- current drinking-water/reuse regulation;
- current chemical-compatibility limits;
- current product-specific TMP/flux/backwash/CEB/CIP operating envelopes;
- validated Total Pretreatment Design calculations.

Because the source was published in 2011, numerical operating ranges, product comparisons, market shares, regulatory references and chemical-cleaning examples must be presented as **source-specific/historical examples** unless independently verified against current authoritative information.

The Academy must not silently convert any example number into a 2026 design rule.

---

# 1. Curriculum role

Use this source as a major backbone for UF/MF education across existing Academy levels without increasing the 360-hour curriculum.

## Level 1 — Water-treatment foundations

Teach:

- where UF/MF sits in the filtration spectrum;
- what a porous membrane physically does;
- why UF/MF is different from NF/RO;
- why particle/pathogen barriers and dissolved-salt barriers are different engineering functions;
- the idea that membrane naming alone does not fully describe performance.

## Level 2 — Unit operations / transport

Teach:

- pressure-driven porous-membrane flow;
- transmembrane pressure (TMP);
- flux and permeability;
- viscosity and temperature effects;
- hydraulic resistance;
- pore transport concepts;
- dead-end/direct filtration versus crossflow;
- surface charge and interfacial effects;
- particle deposition, cake formation and pore blocking.

Connect these lessons to general transport phenomena rather than presenting them as isolated membrane formulas.

## Level 3 — Pretreatment

Strengthen L03-M04 MF/UF Pretreatment and Fouling Risk with:

- UF versus MF terminology and ratings;
- MWCO versus pore-size language;
- hollow-fibre configurations;
- inside-out versus outside-in implications;
- polymeric versus ceramic membrane characteristics;
- membrane material selection;
- membrane hydrophilicity/hydrophobicity;
- zeta potential / surface charge;
- pore-size distribution;
- fibre diameter and mechanical strength;
- allowable pressure concepts;
- dead-end/direct filtration;
- crossflow;
- backwash;
- air flush;
- air scour;
- CEB;
- CIP;
- coagulant interaction with UF/MF;
- filtrate monitoring and operational diagnosis.

## Level 4 — Membrane systems

Use Pearce to reinforce:

- membrane transport terminology;
- flux/permeability distinctions;
- membrane structure-performance tradeoffs;
- critical flux;
- sustainable flux;
- threshold flux;
- temperature-normalized performance;
- fouling-versus-cleaning tradeoffs;
- how local pore/fibre properties affect whole-system behavior.

Do not let Academy replace Total RO Design or Total Pretreatment Design with its own project-grade membrane design engine.

## Level 6 — Pumps / energy

Use crossflow versus dead-end/direct filtration to teach why hydraulic configuration changes energy demand.

Teach that more crossflow can reduce deposition but carries pumping-energy consequences; the optimum is application-specific.

## Level 7 — Controls

Use UF/MF as a concrete PLC/control application:

- filtration state;
- backwash sequence;
- air scour sequence;
- CEB sequence;
- CIP permissives;
- filtrate-to-waste logic;
- TMP alarms;
- permeability trend alarms;
- integrity/quality alarm response;
- recovery and cycle timing.

## Level 8 — Residuals

Connect:

- backwash waste;
- CEB/CIP waste;
- chemical residuals;
- coagulant residuals;
- solids loading;
- recovery impact.

## Level 9 — economics / project decisions

Teach the lifecycle tradeoff among:

- membrane area;
- design flux;
- cleaning frequency;
- chemical consumption;
- energy;
- replacement interval;
- redundancy;
- filtrate-quality risk;
- operating labor;
- pretreatment intensity.

## Level 10 — capstone

Require the student to defend a UF/MF design philosophy, not merely select a membrane brand.

---

# 2. Core science and engineering concepts to teach

## 2.1 UF/MF ratings and terminology

Teach clearly:

- UF has historically been described using MWCO as well as nominal pore-size concepts;
- MF is generally described by pore size;
- MWCO is not a perfect physical pore-size measurement;
- nominal rating, absolute rating and actual removal performance are not interchangeable concepts;
- pore-size distribution matters;
- biological/particle rejection must be demonstrated using the applicable integrity/performance framework rather than inferred solely from a nominal label.

### Common mistake

**“A 0.04 µm membrane removes every particle larger than 0.04 µm and passes everything smaller.”**

Why it fails:

Real membranes have pore distributions, tortuous structures, surface interactions and system-level integrity considerations. Removal performance cannot be inferred from one nominal number alone.

---

## 2.2 UF versus MF

Teach the overlap between modern UF and MF rather than presenting an artificial hard boundary.

The learner should understand:

- the historical distinction;
- why water-treatment UF and MF product ranges can overlap;
- why actual rejection and integrity performance matter more than the marketing label;
- why some applications call similar technology UF/MF or MF/UF.

Do not create a universal single-pore-size cutoff that claims to define all UF versus MF products.

---

## 2.3 Flow configuration

Teach two major concepts:

### Crossflow

Feed moves tangentially along the membrane surface, which can reduce excessive solids accumulation but increases recirculation/pumping energy.

### Dead-end / direct-flow filtration

Most feed passes through the membrane while rejected material accumulates until a cleaning/backwash step removes it.

Students must understand that the hydraulic choice affects:

- energy;
- solids accumulation;
- cleaning frequency;
- recovery;
- module configuration;
- process control.

### Interactive exercise — Crossflow or Dead-End?

Give the learner three waters with different suspended-solids loading and ask them to choose a hydraulic strategy and defend the energy/fouling tradeoff.

---

# 3. Membrane material science

## 3.1 Polymeric membranes

Teach common membrane-selection properties:

- permeability;
- pore-size distribution;
- surface hydrophilicity/hydrophobicity;
- contact angle as a surface-wetting indicator;
- zeta potential/surface charge;
- mechanical strength;
- chemical resistance;
- oxidant resistance;
- temperature tolerance;
- fibre strength;
- ageing and cleaning compatibility.

The book discusses common historical polymer families including materials such as PES/PS, PVDF, PAN and cellulose-based options.

Do not rank polymers universally from the 2011 book. Product formulations and surface modifications evolve.

### Interactive exercise — Choose the Membrane Material

Students receive:

- feed pH;
- oxidant exposure;
- expected organics;
- cleaning chemicals;
- operating temperature;
- mechanical duty;
- required permeability.

They must identify the material properties that matter before consulting current product data.

---

## 3.2 Hydrophobicity and contact angle

Teach:

- why wetting behavior matters;
- why hydrophobic surfaces can be more susceptible to certain organic interactions;
- why membrane manufacturers modify surfaces;
- why hydrophilicity alone does not determine fouling performance.

### Common mistake

**“The most hydrophilic membrane is always the least-fouling membrane.”**

Correction:

Fouling depends on feed composition, membrane chemistry, surface charge, roughness, pore structure, hydrodynamics and cleaning strategy as well as hydrophilicity.

---

## 3.3 Zeta potential / surface charge

Teach:

- membrane surfaces can carry pH-dependent charge;
- feed-water ionic strength and chemistry influence electrostatic interactions;
- membrane charge can affect particle/organic interaction;
- zeta potential is an explanatory/diagnostic property, not a complete fouling predictor.

Connect to Level 2 colloid/coagulation lessons.

---

## 3.4 Hollow-fibre structure and mechanical strength

Teach:

- asymmetric porous wall structure;
- active/separation layer versus support structure;
- fibre inside/outside diameters;
- how diameter/wall geometry affects strength and packing;
- burst pressure versus collapse pressure;
- why inside-out and outside-in designs impose different mechanical/hydraulic constraints.

Do not publish historical burst/collapse pressure values as current product limits.

---

## 3.5 Ceramic membranes

Teach ceramic membranes as a separate material family with potential advantages such as:

- chemical durability;
- thermal durability;
- mechanical robustness;
- long service-life potential;
- aggressive-cleaning capability in suitable applications.

Also teach tradeoffs:

- capital cost;
- module design;
- surface chemistry;
- application-specific economics.

Use current specialist/vendor information for actual material/product selection.

---

# 4. Transport model, TMP, flux and permeability

## 4.1 TMP

Teach TMP as the effective hydraulic driving pressure across the membrane.

Students must understand that TMP is derived from feed/concentrate/permeate pressure conditions according to system configuration.

Do not teach one TMP equation without identifying the hydraulic configuration and pressure measurement locations.

## 4.2 Flux

Flux is membrane throughput normalized by membrane area.

Teach units and conversion carefully.

## 4.3 Permeability

Permeability relates flux to driving pressure and is useful for comparing membrane condition after controlling for temperature and relevant operating conditions.

### Common mistake

**“Flux decreased, therefore the membrane fouled.”**

Why it fails:

Flux can change because of TMP, viscosity/temperature, control philosophy, recovery, feed characteristics or fouling.

Students must normalize and interpret trends.

---

# 5. Fouling mechanisms

Use the book to teach distinct mechanisms rather than one generic word “fouling.”

## 5.1 Particle fouling / pore-blocking models

Teach conceptual forms:

- complete blocking;
- standard blocking;
- intermediate blocking;
- cake filtration.

The purpose is not for Academy to force every real plant into one ideal model. The models teach how different deposition patterns affect flux/TMP behavior.

### Interactive exercise — Blocking Law Detective

Give four stylized permeability/TMP trends and ask the student which mechanism is most plausible and what additional evidence they would request.

---

## 5.2 Gel/organic fouling

Teach how dissolved/colloidal organics can form highly resistant surface layers and how water chemistry, concentration, surface properties and hydrodynamics influence behavior.

Connect to existing Academy AOM/TEP and algal-bloom material.

---

## 5.3 Oil fouling

Introduce oil/emulsion fouling as a distinct application-specific challenge.

Teach:

- hydrophobic interactions;
- droplet deformation/coalescence;
- pore/surface deposition;
- cleaning implications.

Do not make broad design recommendations without application-specific testing.

---

# 6. Fouling-control hierarchy

Academy should teach fouling control as a hierarchy of escalating intervention.

## 6.1 Prevention / operating design

- appropriate pretreatment;
- appropriate flux;
- hydraulic configuration;
- coagulant strategy when justified;
- solids loading control;
- temperature awareness;
- feed-quality monitoring.

## 6.2 Routine physical cleaning

- backwash;
- air flush;
- air scour;
- hydraulic relaxation where relevant;
- crossflow where relevant.

## 6.3 Maintenance chemical cleaning / CEB

Teach CEB as an intermediate restoration tool between routine physical cleaning and full CIP.

## 6.4 CIP

Teach CIP as a deeper restoration process whose chemistry must match:

- foulant type;
- membrane material;
- temperature limits;
- concentration limits;
- contact time;
- sequence/rinsing requirements;
- environmental and waste-disposal constraints.

Do not copy 2011 chemical concentrations or soak durations as 2026 defaults.

### Interactive exercise — Cleaning Ladder

Students must decide whether a deteriorating UF train needs:

1. operating adjustment;
2. backwash;
3. air scour;
4. CEB;
5. CIP;
6. inspection/integrity investigation.

The exercise penalizes jumping directly to aggressive chemical cleaning without diagnosis.

---

# 7. Backwash, air scour and hydraulic cleaning

Teach the mechanism of each step.

## Backwash

Reverse permeate/filtrate flow can dislodge deposited solids.

## Air flush / air scour

Air changes hydrodynamics and shear around fibres and can improve foulant removal.

Teach inside-out versus outside-in differences and why air strategy depends on module architecture.

## Crossflow

Can reduce accumulation but increases pumping energy and may not be economical for low-solids drinking-water applications.

### Common mistake

**“More air or more backwash always cleans better.”**

Correction:

Excess intensity can waste energy/water, damage fibres, cause excessive stress, create carryover issues or provide little incremental benefit. Current manufacturer limits and validated design logic govern.

---

# 8. Coagulation upstream of UF/MF

Integrate Pearce with Bolto & Gregory, Tabatabai and the existing Academy SWRO pretreatment source maps.

Teach two possible objectives:

- removal of particles/NOM before membrane filtration;
- modification of cake/floc properties to improve membrane performance and reversibility.

Teach risks:

- underdose;
- overdose;
- poor mixing;
- residual metal/polymer;
- irreversible fouling;
- incompatibility between coagulant/polymer and membrane/antiscalant systems.

No universal coagulant dose is authorized.

---

# 9. Critical, sustainable and threshold flux

This is one of the most valuable advanced teaching areas in the uploaded pages.

## Critical flux

Introduce as the conceptual flux below which a particular fouling signature may be very low or absent under defined conditions.

## Sustainable flux

Teach as an operating/economic concept balancing fouling rate, cleaning, recovery, reliability and lifecycle cost.

## Threshold flux

Teach the transition between lower and more rapidly increasing fouling regimes where applicable.

### Critical safeguard

Do not present critical, sustainable or threshold flux as intrinsic universal constants for a membrane product.

They depend on:

- source water;
- pretreatment;
- membrane condition;
- temperature;
- solids/organic loading;
- module hydrodynamics;
- cycle design;
- cleaning strategy.

### Interactive exercise — The Highest Flux Is Not the Best Flux

Students compare three operating points with different membrane area, TMP rise, cleaning frequency, energy and replacement cost and select the lifecycle-optimal operating philosophy.

---

# 10. Temperature correction

Teach why colder water has higher viscosity and often lower membrane permeability/flux under otherwise similar conditions.

Students should learn to normalize performance to a reference temperature before diagnosing fouling.

The book discusses temperature correction factors and alternative correction approaches.

Do not hard-code its coefficients as the universal current TWDS model until validated against the intended membrane family and current design authority.

### Interactive exercise — Cold Morning, Same Membrane

Plant permeability falls after seawater temperature decreases.

Student must distinguish temperature effect from genuine fouling before triggering a chemical clean.

---

# 11. Filtrate quality and monitoring

Teach a multi-signal approach.

Possible learner-facing indicators include:

- turbidity;
- particle counting;
- total suspended solids where applicable;
- pressure/TMP;
- normalized permeability;
- cycle length;
- filtrate quality trend;
- membrane integrity test results where applicable;
- downstream SDI/MFI or other application-specific metrics.

### Common mistake

**“Low turbidity proves the membrane is intact.”**

Correction:

Turbidity is a useful indirect quality signal but does not replace required direct/indirect integrity monitoring or applicable regulatory validation.

---

# 12. SWRO pretreatment integration

The Chapter 1 SWRO discussion should strengthen existing seawater Academy material.

Teach why UF/MF may be selected before SWRO to provide a more consistent particulate/microbial barrier and potentially reduce downstream feed variability.

But students must still evaluate:

- algae/AOM/TEP;
- coagulant strategy;
- membrane fouling;
- feed temperature;
- source-water seasonal variability;
- energy;
- chemical cleaning;
- backwash waste;
- membrane replacement;
- cartridge-filter interface;
- RO feed-quality targets;
- plant availability and redundancy.

UF/MF is not automatically superior to conventional pretreatment for every SWRO site.

### Interactive exercise — Conventional or UF?

Students receive two seawater sites:

A. stable low-turbidity offshore source;
B. algae-prone variable coastal intake.

They compare conventional pretreatment and membrane pretreatment using reliability, fouling risk, waste, footprint, chemicals, energy and lifecycle economics.

---

# 13. Regulatory material

The 2011 book includes historical drinking-water and reuse regulatory/approval discussion.

Use it to teach:

- why membrane integrity and certification exist;
- difference between regulatory approval and technical capability;
- why jurisdiction matters;
- why membrane systems require validated performance evidence.

Do not present historical regulatory lists/standards as current requirements.

Any learner-facing current regulation claim must be verified against current jurisdictional sources.

---

# 14. Evidence-literacy lesson

Pearce is an excellent example for the Academy's ENG-EVIDENCE competency.

Students should be told:

> The physics may remain highly valuable even when the product market, regulations and typical operating practices have evolved.

### Exercise — What Aged and What Did Not?

Students classify statements from the source as:

- fundamental physics;
- durable engineering principle;
- historical market observation;
- historical regulation;
- product-specific property;
- operating example requiring current verification.

---

# 15. Proposed interactive UF/MF missions

1. **UF or MF?** — interpret MWCO, pore size and actual removal evidence.
2. **Crossflow or Dead-End?** — choose hydraulic configuration.
3. **Choose the Membrane Material** — surface/chemical/mechanical tradeoff.
4. **Contact Angle Is Not the Whole Story** — hydrophilicity misconception.
5. **Zeta Potential Explorer** — pH/ionic-strength interaction.
6. **Inside-Out vs Outside-In** — hydraulic/mechanical module reasoning.
7. **Burst or Collapse?** — fibre pressure-direction challenge.
8. **Blocking Law Detective** — pore blocking/cake interpretation.
9. **Fouling Fingerprint** — particle vs organic vs oil/gel scenarios.
10. **Cleaning Ladder** — backwash → air scour → CEB → CIP.
11. **Coagulant Before UF?** — benefit-versus-residual-fouling tradeoff.
12. **The Highest Flux Is Not the Best Flux** — sustainable-flux economics.
13. **Critical / Sustainable / Threshold Flux** — distinguish the concepts.
14. **Cold Morning, Same Membrane** — temperature correction.
15. **Filtrate Quality Dashboard** — multi-signal monitoring.
16. **Integrity or Fouling?** — diagnose sudden filtrate-quality change.
17. **SWRO Pretreatment Defense** — conventional vs UF/MF.
18. **What Aged and What Did Not?** — engineering evidence literacy.

---

# 16. Guided Engineering Solution Mode examples

For difficult UF problems use:

**Design basis → source-water risk → membrane/material constraint → hydraulic mode → flux/TMP expectation → fouling mechanism → physical cleaning → chemical cleaning → monitoring → lifecycle consequence.**

Each advanced exercise should contain **Common Mistake / Why It Fails / How to Detect It / Correct Engineering Approach** callouts.

Examples:

- assuming MWCO equals absolute pore diameter;
- treating UF and MF labels as universal performance categories;
- diagnosing every permeability decline as fouling;
- increasing flux without examining cleaning frequency/lifecycle cost;
- choosing CEB chemistry without identifying foulant type;
- ignoring water temperature when trending permeability;
- using turbidity as the only membrane-integrity indicator;
- assuming membrane pretreatment automatically eliminates SWRO biofouling.

---

# 17. Engineering ownership

Academy owns:

- pedagogy;
- source interpretation;
- conceptual calculations;
- original visuals;
- quizzes;
- exercises;
- troubleshooting scenarios.

Project-grade UF/MF selection, sizing, hydraulic design and operating envelopes remain with:

- `app/total-pretreatment-design`;
- applicable validated shared engines;
- current validated vendor/product data.

Academy must not fork a competing professional UF/MF engine.

---

# 18. Copyright / provenance

Do not reproduce photographed book pages, tables, figures or long passages in learner-facing content.

Create original Academy diagrams for:

- filtration spectrum;
- crossflow/dead-end;
- hollow-fibre structure;
- pore-size distribution;
- blocking mechanisms;
- fouling-control ladder;
- flux/TMP/permeability trends;
- critical/sustainable/threshold flux;
- temperature normalization;
- filtration-state PLC sequence.

Whenever Pearce materially informs a lesson, list it under **Research Basis / Sources & Further Reading**.

---

# 19. Status

This source map is **content/source architecture**. It does not claim that all UF/MF learner-facing lessons have already been authored.

Future pages from the same book should extend this map rather than create duplicate source documents, unless they introduce a materially separate topic such as module sizing, system design, integrity testing, case studies or lifecycle costing that merits its own specialized source note.
