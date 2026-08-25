# Total Water Academy — SWRO Pretreatment, Algal Blooms & Fouling-Control Source Map v1.0

Owner: `app/total-water-academy`

## Purpose

This source map strengthens the Total Water Academy seawater reverse-osmosis learning path with a rigorous treatment of **pretreatment reliability, algal-bloom response, coagulation, dissolved-air flotation, granular-media filtration, micro-/ultrafiltration, organic/biological fouling risk, fouling indicators and pretreatment operating strategy**.

Primary supplied reference:

S. Assiyeh Alizadeh Tabatabai, **Coagulation and Ultrafiltration in Seawater Reverse Osmosis Pretreatment**, doctoral dissertation, Delft University of Technology / UNESCO-IHE Institute for Water Education, 2014; CRC Press/Balkema.

The source is especially valuable because it connects classic unit-operations theory with real SWRO pretreatment behavior:

- coagulation chemistry and pH;
- G, Gt and mixing intensity;
- particle aggregation and floc structure;
- Darcy flow and resistance-in-series;
- cake/gel formation and compression;
- Carman-Kozeny reasoning;
- membrane flux and TMP development;
- backwashable, non-backwashable and irreversible fouling;
- algal cells versus algal organic matter (AOM);
- transparent exopolymer particles (TEP);
- biopolymers and LC-OCD interpretation;
- SDI limitations and MFI/MFI-UF;
- DAF, GMF and UF process selection;
- inline coagulation versus conventional coagulation/flocculation;
- CEB/CIP and membrane recoverability;
- low-MWCO UF and surface-porosity tradeoffs;
- experimental ferric-hydroxide membrane pre-coating;
- chemical consumption, sludge and marine-discharge consequences;
- robustness during harmful algal blooms (HABs).

## Historical/reference safeguard

This dissertation was published in 2014. Its experimental doses, fluxes, pore sizes/MWCOs, membrane products, cleaning intervals, treatment performance, historical plant experience and stated industry practices must be presented as **source-labelled study results or historical examples**, not automatic 2026 TWDS design criteria.

Current project design values must come from:

1. current source-water characterization and pilot data;
2. current owner requirements and jurisdictional permits;
3. current membrane and pretreatment supplier guidance;
4. validated Total Pretreatment Design / Total RO Design logic where available;
5. current authoritative references and peer-reviewed evidence.

Academy may teach the governing physics and engineering reasoning from this source but must never silently convert a single study result into a universal design rule.

---

# 1. Core teaching principle

> **SWRO pretreatment is a reliability system, not merely a turbidity-reduction step.**

The learner should understand that the pretreatment train must simultaneously:

- maintain hydraulic capacity;
- control particulate/colloidal loading;
- limit organic fouling potential;
- limit biological fouling potential;
- protect RO feed channels/spacers;
- produce stable water quality through source variability;
- recover effectively by backwash/CEB/CIP;
- minimize chemical, energy and waste burden;
- preserve contracted plant availability.

A low turbidity or low SDI result by itself does not prove that all these objectives have been met.

---

# 2. Academy placement

## Level 1 — Water Treatment Foundations & Water Quality

Introduce seawater as a **dynamic biological and colloidal source**, not only a saline ionic solution.

Teach beginners that raw seawater may contain:

- suspended mineral particles;
- colloids;
- algae and algal debris;
- bacteria;
- natural organic matter;
- algal organic matter (AOM);
- high-molecular-weight biopolymers;
- transparent exopolymer particles (TEP);
- nutrients capable of supporting downstream biofilm growth;
- oil/grease and episodic contamination where applicable.

### Beginner concept — “Clear water is not necessarily easy water”

A source may have modest turbidity yet still create severe membrane problems if it contains sticky or compressible organic foulants.

### Common Mistake

**Mistake:** “If the seawater looks clear, pretreatment should be easy.”

**Why it fails:** Many important foulants are microscopic, colloidal or dissolved/high-molecular-weight organics that are not obvious visually.

---

# 3. Level 2 — Unit Operations, Balances & Transport Fundamentals

This source should become an applied bridge between unit-operations theory and later SWRO pretreatment.

## 3.1 Darcy flow and resistance-in-series

Teach the membrane-flux relationship conceptually:

`flux ∝ driving pressure / (viscosity × total resistance)`

and decompose resistance into:

- clean membrane resistance;
- pore-blocking resistance;
- cake/gel-layer resistance.

Students should understand that constant-flux operation requires rising TMP as fouling resistance increases.

## 3.2 Cake/gel filtration

Teach that deposited foulants do not behave like a generic solid blanket.

Cake/gel resistance depends on:

- particle/aggregate size;
- particle density;
- particle shape/sphericity;
- cake porosity;
- cake compressibility;
- concentration of deposited material;
- filtration flux/pressure history.

## 3.3 Carman-Kozeny reasoning

Use the relationship only as a **conceptual/educational model** to show why cake resistance can change strongly with particle size and porosity.

Students should learn:

- larger, more open aggregates may form more permeable cakes;
- low-density/fluffy aggregates can filter differently from dense primary particles;
- fractal aggregate structure makes real behavior more complicated than ideal packed spheres;
- model assumptions matter.

## 3.4 Compressible cakes

AOM is particularly useful for teaching compressible cake/gel behavior.

The student should see that:

- increasing flux can compact deformable AOM deposits;
- a compressed layer has higher resistance;
- local flux can rise when part of the active area becomes blocked;
- this can accelerate pressure development nonlinearly.

### Interactive exercise — “Why did TMP curve upward?”

Show two constant-flux filtration traces:

1. approximately linear TMP rise;
2. strongly curved/accelerating TMP rise.

Ask the student to diagnose:

- simple cake filtration;
- cake compression;
- loss of active area/pore blocking;
- combined effects.

## 3.5 Mixing, G and Gt

Reinforce the meaning of:

- velocity gradient `G`;
- exposure `Gt`;
- power input;
- residence time;
- aggregation versus breakup.

Students should learn that mixing conditions appropriate for a sedimentation flocculator are not automatically appropriate for inline coagulation ahead of UF.

## 3.6 Perikinetic and orthokinetic aggregation

Connect:

- Brownian-motion-driven collisions for small particles;
- shear/velocity-gradient-driven collisions for larger aggregates;
- collision efficiency;
- hydrodynamic breakup.

### Common Mistake

**Mistake:** “More Gt always produces a better floc.”

**Correction:** Higher exposure can promote growth under some conditions but excessive shear can break aggregates; the desired aggregate depends on the downstream separation process.

---

# 4. Level 3 — Pretreatment & Solids Separation

This is the main home for the source.

## 4.1 Pretreatment objectives

Teach that SWRO pretreatment is selected from combinations of:

- intake/source control;
- screens/microstrainers;
- coagulation;
- flocculation;
- sedimentation;
- dissolved air flotation (DAF);
- granular media filtration (GMF/DMF);
- microfiltration (MF);
- ultrafiltration (UF);
- cartridge filtration;
- associated backwash/sludge handling.

The train must be matched to source-water risk rather than selected by habit.

## 4.2 Conventional versus membrane pretreatment

Teach the functional difference:

### Conventional route

`coagulation → flocculation → clarification (when required) → media filtration → cartridge → RO`

### Membrane route

Possible simplified configurations include:

`screen → UF → cartridge → RO`

or

`screen → inline coagulation → UF → cartridge → RO`

or for more challenging water:

`screen → coagulation/flocculation → DAF → UF → cartridge → RO`

The student must learn why no single train is universally optimal.

## 4.3 GMF / DMF

Teach granular-media filtration as depth filtration.

Important design/operational concepts:

- media size and layering;
- filtration rate;
- bed depth;
- headloss development;
- backwash;
- ripening;
- coagulation assistance;
- depth filtration versus surface blocking;
- vulnerability to excessive floc load and algae.

### Failure mechanism

During severe blooms or high coagulated-solids loading, the filter can transition from desired depth filtration toward surface/cake blocking, causing rapid headloss and short runs.

### Common Mistake

**Mistake:** “If SDI is high, just increase coagulant dose ahead of the media filters.”

**Why it fails:** More coagulant may increase floc loading and accelerate surface clogging; clarification or a different train may be required.

## 4.4 DAF

Teach DAF as a low-density-solids clarification process particularly relevant to algae.

Concepts:

- coagulation/floc formation;
- recycle saturation;
- depressurization and microbubble generation;
- bubble-floc attachment;
- rise velocity / flotation;
- skimming/sludge removal;
- hydraulic loading;
- downstream filter protection.

### Why DAF can help during blooms

Algal cells and low-density biological solids may separate poorly by sedimentation but can be amenable to flotation.

### Common Mistake

**Mistake:** “DAF solves the whole algal-bloom problem.”

**Correction:** DAF can remove cells/flocs and reduce downstream solids loading, but AOM/TEP/biopolymers and dissolved nutrients may still pass depending on coagulation and downstream processes.

## 4.5 UF / MF pretreatment

Teach:

- inside-out versus outside-in;
- pressurized versus submerged concepts;
- dead-end filtration;
- filtration flux;
- TMP/permeability;
- backwash;
- air scour where applicable;
- CEB;
- CIP;
- membrane integrity;
- pore size/MWCO;
- surface porosity;
- module hydraulic limitations.

### Why UF can be robust

UF provides a physical barrier with more stable turbidity/SDI performance than media filtration under many variable conditions.

### But UF still fouls

UF is not immune to:

- AOM/TEP;
- pore blocking;
- compressible cake/gel layers;
- non-backwashable fouling;
- irreversible fouling;
- capillary plugging;
- high cleaning frequency.

## 4.6 Algal cells versus AOM

A major lesson from this source is that **algal cells are not necessarily the only or even the dominant membrane-fouling concern**.

Teach the distinction:

- algal cells;
- intracellular organic matter (IOM);
- extracellular organic matter (EOM);
- AOM;
- biopolymers;
- TEP;
- proteins/polysaccharides;
- nutrients released during bloom decay.

### Common Mistake

**Mistake:** “If UF removes the algal cells, the RO is safe.”

**Why it fails:** Sticky high-molecular-weight organics and nutrients can persist and affect UF hydraulics, RO organic fouling and biofilm development.

## 4.7 TEP

Teach TEP as highly hydrated, sticky gel-like material that can:

- accumulate on UF and RO surfaces/spacers;
- fill voids within deposited cakes;
- increase non-backwashable fouling;
- act as a conditioning layer for bacterial attachment;
- contribute to biofilm initiation.

The lesson must distinguish TEP from conventional mineral particulate matter.

## 4.8 Inline coagulation before UF

Teach the key conceptual difference from conventional coagulation:

### Conventional coagulation goal

Create flocs suitable for a subsequent clarification/filter process.

### Inline coagulation/UF goal

Modify foulant properties so the UF system has:

- lower pore blocking;
- more permeable cake/gel structure;
- better backwashability;
- lower non-backwashable fouling;
- acceptable permeate quality.

Large settleable flocs are not necessarily required.

### Variables

Students should reason about:

- coagulant type;
- dose;
- pH;
- rapid-mix G;
- contact time;
- downstream pipe/pump shear;
- UF flux;
- foulant type/concentration.

## 4.9 Ferric versus aluminium awareness

Teach why residual aluminium can be problematic upstream of NF/RO through potential precipitation/scaling interactions.

Do not hard-code a universal ban or universal coagulant rule; current product chemistry, source conditions, residual targets and specialist-owner guidance govern project design.

## 4.10 Coagulant dose is not monotonic “more is better”

Students should learn that coagulant dose can affect:

- destabilization/complexation;
- sweep-floc formation;
- aggregate concentration;
- cake resistance;
- residual metal;
- filter loading;
- sludge production;
- backwash-water treatment burden;
- downstream fouling risk.

### Guided exercise — “Find the useful dose window”

The student changes dose and pH and must identify why the optimum for hydraulic stability may not equal the optimum for organic removal or sludge minimization.

## 4.11 pH matters

Teach pH effects on:

- metal hydrolysis/speciation;
- precipitation;
- complexation with organic matter;
- aggregate formation kinetics;
- residual dissolved metal;
- cake properties;
- downstream scaling/corrosion considerations.

Avoid turning the dissertation's experimental pH results into universal seawater coagulation setpoints.

## 4.12 Flocculation may be unnecessary or harmful before UF

Teach that extended conventional flocculation is not automatically required ahead of UF.

Reasons:

- UF does not need settleable millimeter-size floc;
- significant G/Gt is already experienced in mixers, pumps, pipes and modules;
- excessive aggregation is not necessarily beneficial;
- excessive shear can also grind/break aggregates.

### Common Mistake

**Mistake:** “A good coagulation system must always include a large flocculation basin.”

**Correction:** The downstream separator determines the desired particle condition.

---

# 5. Level 4 — MF/UF/NF/RO Membrane Systems

## 5.1 Pretreatment and RO spacer protection

Teach that spiral-wound RO is particularly vulnerable to feed-channel/spacer accumulation of particulate, organic and biological material.

The consequence can include:

- normalized permeate-flow decline;
- increasing feed-channel pressure drop;
- higher required NDP/feed pressure;
- more frequent CIP;
- increased downtime;
- reduced membrane life;
- loss of water production.

## 5.2 Fouling categories

Explicitly distinguish:

- particulate fouling;
- colloidal fouling;
- organic fouling;
- biological fouling;
- scaling;
- metal/precipitate fouling;
- mixed fouling.

Real plants frequently experience combinations.

## 5.3 Conditioning layer concept

Teach how sticky AOM/TEP can create a surface that promotes bacterial attachment and later biofilm growth.

A biofouling problem can therefore begin upstream with an organic-fouling/conditioning event.

## 5.4 Bloom lifecycle

Teach that the risk does not necessarily end when cell count falls.

During bloom decline/death:

- intracellular material may be released;
- biodegradable organics/nutrients may increase;
- biofouling risk may persist or shift in time.

### Common Mistake

**Mistake:** “The bloom is over because chlorophyll-a dropped, so pretreatment can immediately return to normal.”

**Correction:** The organic/nutrient aftermath may remain important.

---

# 6. Fouling indicators — cross-level diagnostic thread

This source is valuable because it challenges overreliance on a single indicator.

## 6.1 SDI

Teach:

- what SDI measures operationally;
- why it became widely used;
- why it remains useful as an industry screening/acceptance parameter;
- why it is not a mechanistic universal predictor of all particulate/colloidal/organic/biofouling.

### Common Mistake

**Mistake:** “SDI < 3 means the RO cannot foul.”

**Correction:** SDI does not fully represent organic, biological, nutrient, TEP or all submicron colloidal risks.

## 6.2 MFI / MFI-UF

Teach MFI conceptually as a fouling indicator based on cake filtration rather than a purely empirical plugging time.

Students should understand why MFI-UF was developed to capture smaller foulants and constant-flux behavior more relevant to modern membrane filtration.

Do not teach one MFI threshold as globally valid without current validated engineering support.

## 6.3 Complementary indicators

Teach the purpose and limitations of:

- turbidity;
- SDI;
- MFI/MFI-UF;
- algae cell count;
- chlorophyll-a;
- TEP;
- LC-OCD biopolymers;
- DOC/TOC;
- UV254/SUVA where meaningful;
- ATP;
- AOC;
- BDOC;
- bacterial counts/activity;
- nutrient concentrations;
- membrane fouling simulator / biofilm monitoring concepts.

### Interactive exercise — “The SDI says good; the RO says bad”

Give a case with:

- low SDI;
- low turbidity;
- elevated TEP/biopolymers;
- rising RO differential pressure.

Ask the student to identify why the monitoring program is incomplete.

---

# 7. Level 6 — Pumps, Hydraulics & Energy

Use inline coagulation/UF to connect process hydraulics with water chemistry.

Teach that after coagulant dosing, aggregates experience hydraulic history through:

- static mixers;
- feed pumps;
- pipe networks;
- valves;
- headers;
- hollow-fibre lumens.

Those zones contribute:

- G;
- Gt;
- residence time;
- collision opportunity;
- potential aggregate breakup.

### Interactive mission — “The pipe is part of the flocculator”

Students calculate simplified headloss, residence time and qualitative G/Gt trends through a dosing/mixer/pump/UF train.

The goal is to recognize that hydraulic layout can affect coagulation performance even when there is no formal flocculation basin.

---

# 8. Level 7 — Instrumentation, Process Control & PLC

Use SWRO pretreatment as an applied control problem.

## 8.1 Monitoring architecture

Possible teaching signals:

- intake turbidity;
- chlorophyll-a / algae warning;
- temperature;
- conductivity/salinity;
- UF feed pressure;
- UF TMP;
- permeability;
- filtrate turbidity;
- SDI;
- MFI/MFI-UF where available;
- differential pressure;
- backwash frequency;
- CEB frequency;
- chemical dose;
- residual iron where appropriate;
- RO feed DP;
- normalized RO flow/rejection;
- cleaning triggers.

## 8.2 Bloom-response control narrative

Teach students to build an operational state machine such as:

`NORMAL → BLOOM WATCH → BLOOM RESPONSE → RECOVERY → NORMAL`

Possible actions may include:

- increased monitoring frequency;
- pretreatment mode change;
- coagulant enable/adjustment;
- DAF enable/optimization;
- reduced UF flux;
- shorter filtration cycles;
- modified backwash/CEB strategy;
- plant derating if necessary;
- RO protection/shutdown criteria.

The exact logic must be project-specific and validated.

### Common Mistake

**Mistake:** “A PLC can optimize coagulation using one turbidity signal.”

**Correction:** Algal/AOM events may not track turbidity alone; multiple indicators and operator judgement can be required.

---

# 9. Cleaning hierarchy

Teach the difference between:

## Hydraulic backwash

Removes reversible/backwashable deposits.

## Chemically enhanced backwash (CEB)

Used more frequently than full CIP to recover performance from deposits not removed hydraulically.

## Cleaning in place (CIP)

A more intensive restoration event with greater downtime, chemical handling and membrane-life implications.

Students should track:

- TMP recovery after BW;
- permeability recovery after BW;
- residual loss after CEB;
- residual loss after CIP;
- trend in cleaning interval.

### Fouling taxonomy for trend analysis

Teach:

- backwashable fouling;
- non-backwashable fouling;
- CEB-recoverable fouling;
- CIP-recoverable fouling;
- irreversible residual loss.

---

# 10. Flux as a design and operating lever

The source provides strong evidence for teaching that flux is not merely a capacity number.

Higher UF flux can:

- increase local foulant loading rate;
- accelerate TMP development;
- compress AOM cake/gel layers;
- shorten run length;
- increase backwash/CEB frequency;
- reduce availability.

Lower flux can:

- reduce fouling severity;
- improve run stability;
- require more membrane area;
- increase CAPEX/footprint;
- reduce instantaneous production when derating an existing plant.

### Interactive mission — “Flux versus robustness”

Students compare two designs:

- high-design-flux / smaller UF area;
- lower-design-flux / larger UF area.

Then introduce an algal-bloom season and compare:

- TMP;
- cleaning frequency;
- production derating;
- lifecycle cost/availability.

---

# 11. Low-MWCO UF — advanced technology lesson

The dissertation's comparison of 10 kDa and 150 kDa UF is valuable as a **technology tradeoff case study**.

Teach the concept:

- tighter membrane → better retention of high-molecular-weight AOM/biopolymers;
- but tighter membrane/material structure may have lower surface porosity and poorer hydraulic recovery;
- better water quality does not automatically mean better lifecycle process performance.

### Critical lesson

The 10 kDa membrane in the study removed AOM biopolymers very effectively, but hydraulic/backwash performance was inferior to the 150 kDa membrane because of material/surface-porosity differences.

### Common Mistake

**Mistake:** “Choose the tightest UF membrane available.”

**Correction:** Selection must balance retention, permeability, surface porosity, fouling, backwashability, chemical demand, energy, recovery, lifecycle cost and downstream RO benefit.

### Research interpretation safeguard

Do not present 10 kDa as a universal commercial SWRO pretreatment recommendation. Teach it as a research-backed example of the separation-versus-hydraulics tradeoff.

---

# 12. Ferric-hydroxide pre-coating — advanced research/innovation lesson

The dissertation investigated applying a removable ferric-hydroxide particle layer at the start of each UF cycle to reduce non-backwashable AOM fouling.

This is useful in Academy as a **research-method and innovation case**, not as a standard TWDS process recommendation.

Teach:

- hypothesis: protect/modify the membrane-foulant interface;
- particle-size effect;
- equivalent chemical dose;
- backwashability;
- physical shielding versus chemical interaction;
- distinction between hydraulic stability and permeate-quality improvement;
- how an experimental idea progresses toward or fails to progress toward commercial practice.

### Common Mistake

**Mistake:** “A promising dissertation result is ready to become a plant design standard.”

**Correction:** Technology readiness, scale-up, manufacturability, long-term operation, regulatory impact and current evidence must be checked.

---

# 13. Level 8 — Residuals / Brine / Environmental Interface

Pretreatment chemicals create residual streams that must be part of plant design.

Teach:

- spent UF backwash;
- CEB waste;
- CIP waste;
- coagulant-rich sludge;
- DAF float sludge;
- GMF backwash water;
- sedimentation sludge;
- residual iron/aluminium concerns;
- sludge thickening/dewatering;
- supernatant recycle versus discharge;
- interaction with RO concentrate discharge;
- environmental permitting.

### Core principle

> **The cheapest pretreatment chemical dose at the membrane skid may not be the cheapest plant-wide solution once sludge and disposal are included.**

### Common Mistake

**Mistake:** “Chemical cost is only the cost of FeCl3 per tonne.”

**Correction:** Add storage/dosing, controls, corrosion, backwash, sludge treatment, dewatering, transport/disposal and environmental constraints.

---

# 14. Level 9 — Reliability, Economics & Project Risk

Use severe bloom events to teach why pretreatment reliability can dominate project economics.

Students should connect:

- pretreatment CAPEX;
- membrane area;
- DAF/clarification redundancy;
- chemical inventory;
- sludge handling;
- cleaning chemicals;
- availability;
- production penalties;
- membrane replacement;
- operator workload;
- source-water seasonality;
- contractual water-supply obligations.

### Case exercise — “Cheap pretreatment, expensive outage”

Compare two concepts:

A. lower initial CAPEX but poor bloom resilience;
B. higher pretreatment CAPEX with DAF/UF robustness.

Introduce a bloom and calculate conceptual consequences for:

- production loss;
- chemical cost;
- CIP frequency;
- membrane life;
- contracted water shortfall.

No historical cost from the dissertation should be used as a 2026 cost default.

---

# 15. Level 10 — Integrated SWRO Capstone

The final SWRO capstone should require a **Pretreatment Design Basis & Operating Philosophy**.

The student must defend:

1. source-water risks;
2. intake implications;
3. selected primary pretreatment;
4. selected secondary pretreatment;
5. coagulation philosophy;
6. DAF/clarification rationale if included;
7. UF/GMF choice;
8. normal and bloom operating flux;
9. backwash/CEB/CIP philosophy;
10. monitoring and alarm strategy;
11. RO feed-water acceptance criteria;
12. residuals/sludge strategy;
13. source variability and derating plan;
14. redundancy/availability;
15. pilot-testing plan and unresolved risks.

### Capstone challenge

Give the student a site with:

- open-ocean intake;
- seasonal diatom bloom;
- occasional red tide;
- variable TEP/biopolymers;
- high required plant availability;
- constrained sludge disposal.

Require comparison of at least three trains, such as:

- coagulation + DAF + DMF + cartridge + RO;
- coagulation + DAF + UF + cartridge + RO;
- inline coagulation + UF + cartridge + RO.

The student must explain the tradeoff, not merely select the “best” train.

---

# 16. Guided Engineering Solution Mode — SWRO pretreatment examples

Hard exercises should use the Academy guided workflow.

## Example A — “Why is the UF failing during spring?”

### Step 1 — Define symptom

- rising TMP;
- shorter cycles;
- poor BW recovery;
- frequent CEB.

### Step 2 — Check source change

- algae;
- chlorophyll-a;
- TEP;
- biopolymers;
- turbidity;
- temperature.

### Step 3 — Classify fouling

Ask whether the problem is:

- particulate loading;
- compressible AOM gel;
- pore blocking;
- chemical precipitate;
- mixed fouling.

### Step 4 — Check flux

Determine whether the membrane is being pushed at the same flux despite a radically different source-water foulant load.

### Step 5 — Check pretreatment/coagulation mode

Evaluate whether inline coagulation or DAF mode should change.

### Step 6 — Evaluate cleaning recovery

Distinguish BW, CEB and CIP recoverability.

### Step 7 — Protect RO

Determine whether RO feed should be derated or isolated.

### Step 8 — Review residues

Assess increased chemical/sludge/backwash burden.

### Common mistakes called out aloud

- “SDI is low, so the RO is safe.”
- “The algae are removed, so AOM is gone.”
- “Increase coagulant until the SDI improves.”
- “Lowering UF flux has no economic cost.”
- “DAF and UF are substitutes in every case.”
- “CEB and CIP are the same thing.”

---

# 17. Interactive Academy exercises to author

1. **Bloom Early-Warning Dashboard** — interpret chlorophyll-a, TEP, turbidity, SDI/MFI and TMP trends.
2. **GMF Surface-Blocking Mission** — increase floc load and watch run length/headloss collapse.
3. **DAF Bubble-Floc Challenge** — compare low-density algal flocs versus dense mineral solids.
4. **UF Flux vs TMP Lab** — increase flux and observe accelerated fouling/compressibility.
5. **AOM Compression Lab** — compare incompressible mineral cake with deformable AOM cake.
6. **SDI vs MFI Detective** — identify why two waters with similar SDI can behave differently.
7. **TEP Conditioning-Layer Animation** — follow gel deposition → bacterial attachment → biofilm.
8. **Inline Coagulation Mixer** — adjust dose, pH, G and residence time.
9. **Flocculation: Needed or Not?** — choose conventional flocculation for sedimentation versus UF.
10. **Backwashability Ladder** — classify BW, CEB, CIP and irreversible loss.
11. **Bloom Response State Machine** — create PLC mode logic for escalating source-water risk.
12. **10 kDa vs 150 kDa Research Case** — compare retention and hydraulic recovery.
13. **Pre-Coating Research Challenge** — evaluate a promising laboratory innovation without overselling readiness.
14. **Residuals Ledger** — calculate conceptual chemical-to-sludge consequences.
15. **Pretreatment CAPEX vs Availability** — compare cheap train versus resilient train.
16. **Full SWRO Pretreatment Defense** — capstone selection and operating philosophy.

---

# 18. Misconception library

Academy should explicitly call out these recurring errors:

1. `Low turbidity = low fouling risk.`
2. `SDI alone predicts all RO fouling.`
3. `Algal cells are the only bloom foulant.`
4. `Removing cells removes AOM/TEP.`
5. `A bloom ends when chlorophyll falls.`
6. `More coagulant is always better.`
7. `A sedimentation floc is also the ideal UF floc.`
8. `Extended flocculation is mandatory before UF.`
9. `DAF makes UF unnecessary.`
10. `UF cannot foul because its product SDI is low.`
11. `Tighter UF is always better.`
12. `Higher UF flux only reduces CAPEX.`
13. `Backwash, CEB and CIP are interchangeable.`
14. `Chemical cost does not include sludge/disposal.`
15. `A laboratory pre-coating result is production-ready.`
16. `A single historical flux/dose threshold is globally valid.`
17. `RO fouling begins at the RO membrane.`

---

# 19. Student competency outcomes

After completing the SWRO pretreatment thread, an advanced student should be able to:

- explain why algal blooms affect pretreatment and RO in several distinct ways;
- differentiate cells, AOM, TEP, biopolymers and nutrient-driven biofouling risk;
- compare GMF, DAF and UF on a process-mechanism basis;
- explain why coagulation requirements differ ahead of sedimentation and UF;
- explain G/Gt and the role of hydraulic history in inline coagulation;
- interpret TMP/permeability trends and distinguish reversible/non-backwashable fouling;
- explain why flux influences fouling severity;
- explain the limitations of SDI and the purpose of MFI-UF;
- select additional monitoring when SDI is insufficient;
- discuss the water-quality versus hydraulic tradeoff of tighter UF;
- incorporate chemical/sludge handling into pretreatment selection;
- develop a bloom-response operating philosophy;
- define what must be pilot-tested before final SWRO pretreatment selection;
- defend pretreatment as a lifecycle reliability decision rather than a single equipment choice.

---

# 20. Engineering ownership and calculation boundaries

## Academy owns

- explanations;
- source-grounded examples;
- original diagrams/animations;
- quizzes;
- diagnostic exercises;
- guided problem-solving;
- original simplified teaching simulations;
- technology-literacy comparisons.

## Academy does not own

Project-grade SWRO pretreatment sizing, including final:

- DAF sizing;
- media-filter sizing;
- UF module count/flux operating envelope;
- coagulant dose;
- cleaning chemistry;
- sludge-system sizing;
- membrane acceptance limits;
- RO cleaning-frequency prediction.

These must come from validated Suite owners and/or current vendor/pilot/project engineering.

Relevant owners include:

- `app/total-pretreatment-design` for pretreatment process design;
- `app/total-ro-design` for RO design/operating consequences;
- shared chemistry owners where chemical-equilibrium calculations are required;
- future validated biological/fouling-monitoring owners if created.

The dissertation's equations may be used to teach mechanisms and assumptions, but Academy must not fork them into an independent production pretreatment engine.

---

# 21. Source provenance and copyright

The supplied dissertation is copyrighted. Academy must not reproduce its figures, tables, diagrams, long passages or publisher layout.

Use it to create:

- original TWDA diagrams;
- original trend plots using synthetic teaching data;
- original decision matrices;
- original scenarios;
- original process flows;
- original misconception cards.

When a lesson materially uses scientific conclusions or specific study findings from this source, include it in the learner-facing **Research Basis / Sources & Further Reading** section.

Recommended source entry:

> Tabatabai, S.A.A. (2014). *Coagulation and Ultrafiltration in Seawater Reverse Osmosis Pretreatment*. Doctoral dissertation, Delft University of Technology / UNESCO-IHE Institute for Water Education. CRC Press/Balkema.

For current-state-of-the-art statements, supplement this 2014 source with newer peer-reviewed and current manufacturer/industry references.

---

# 22. Content-authoring priority

Recommended authoring sequence:

### Priority 1

- algal blooms, AOM and TEP;
- GMF/DAF/UF decision logic;
- SDI versus MFI-UF;
- UF fouling / TMP / backwashability;
- inline coagulation concept.

### Priority 2

- flux/compressibility;
- G/Gt and pipe/pump hydraulic history;
- CEB/CIP hierarchy;
- bloom-response controls;
- chemical/sludge balance.

### Priority 3 — advanced/research

- low-MWCO UF;
- membrane surface porosity;
- ferric-hydroxide pre-coating;
- mechanistic cleaning-frequency prediction;
- research uncertainty and technology-readiness evaluation.

This ordering keeps the Academy practical for beginners while retaining substantial depth for advanced learners.
