# Total Water Academy — Practical RO Engineering Source Map v1.0

**Owner:** `app/total-water-academy`  
**Primary source integrated:** Jane Kucera, *Reverse Osmosis: Industrial Processes and Applications*, 2nd ed. (2015)  
**Purpose:** strengthen Academy teaching, exercises and troubleshooting judgment without making a 2015 textbook an authoritative present-day design standard.

## 1. Why this source is valuable

This source is especially useful for Total Water Academy because it progresses from simple RO fundamentals into practical system design, pretreatment, skid equipment, instrumentation, controls, operations, normalization and troubleshooting. That teaching pattern matches the Academy objective: explain the engineering principle, show how it appears in an actual plant, then let the student make a design or operating decision.

The Academy should preserve this practical style while using original explanations and original graphics. The book is a source of engineering concepts and teaching structure, not course copy.

## 2. Curriculum strengthening map

### Levels 1–2 — practical membrane literacy

Use the source to strengthen beginner explanations of:

- osmosis and reverse osmosis;
- semipermeable membranes;
- dead-end versus cross-flow filtration;
- feed, permeate and concentrate streams;
- recovery and concentration factor;
- rejection versus salt passage;
- membrane flux and net driving pressure;
- osmotic pressure as a resistance to permeation;
- concentration polarization and the membrane-surface boundary layer;
- the meaning of fouling, scaling, SDI, MFI and saturation indexes;
- the solution-diffusion model as the principal conceptual transport model.

The goal is that a beginner can look at an RO process diagram and explain what is physically happening before using Total RO Design.

### Level 3 — pretreatment as protection of the membrane process

Strengthen the Pretreatment level with RO-specific design consequences:

- why feed-water characterization determines pretreatment;
- suspended solids, turbidity and SDI;
- microbial and organic fouling;
- iron, manganese and aluminum risks;
- hydrogen sulfide and oxidation/precipitation consequences;
- silica speciation, amorphous silica and metal-silicate interactions;
- calcium carbonate, sulfate, fluoride and phosphate scaling;
- oxidant compatibility and dechlorination;
- clarifiers, multimedia filtration, high-efficiency filtration, carbon, iron removal, softening, UV and membrane pretreatment;
- sequencing pretreatment technologies instead of selecting equipment independently;
- cartridge filters as final protection rather than a substitute for bulk pretreatment.

Professional design predictions remain owned by `app/total-pretreatment-design`, `engine/shared-water-chemistry` and relevant specialist owners.

### Level 4 — RO design and membrane-system engineering

Use the source heavily in the membrane level for:

- membrane materials and construction;
- membrane modules and spiral-wound anatomy;
- feed spacers, permeate carriers, brine seals, interconnectors and anti-telescoping devices;
- membrane specification-sheet test conditions;
- why rated membrane performance cannot be compared without comparing test conditions;
- arrays and stages;
- tapering vessel count to maintain cross-flow;
- recycle;
- double-pass systems;
- multiple trains and redundancy;
- module-by-module changes in flow, concentration and permeate quality;
- recovery/product-quality tradeoffs;
- local scaling tendency increasing toward the tail of an RO train;
- use and interpretation of RO design/projection software.

Actual membrane projections and performance calculations must come from `app/total-ro-design` and validated Suite adapters.

### Level 6 — pumps, hydraulics and equipment

Strengthen the equipment curriculum with RO-specific examples:

- centrifugal pump selection from flow and pressure duty;
- reading a pump curve;
- pump efficiency and motor efficiency;
- NPSH and cavitation awareness;
- VFD operation as a process-control tool rather than only an electrical concept;
- pressure-vessel purpose and pressure ratings;
- water hammer and controlled pressurization;
- pressure drop, axial loading and membrane telescoping;
- materials-of-construction decisions.

This allows the electrical/mechanical lessons to remain connected to a process the student already understands.

### Level 7 — instrumentation, PLC and controls in a real water process

Use the RO skid as a recurring controls case study:

- feed, interstage, permeate and concentrate pressure measurement;
- flow and conductivity measurement;
- pH, temperature and ORP monitoring;
- low-feed-flow, low-reject-flow and low-suction-pressure protection;
- high-pressure, high-temperature and oxidant protection;
- permeate-quality divert logic;
- PLC, PID, HMI and SCADA concepts;
- automated start-up and flush sequences;
- control of pressure and recovery using valves and VFDs;
- why changing one set point without understanding dependent variables can accelerate fouling or scaling.

The teaching objective is for students to connect a P&ID/control narrative with the physical RO process.

### Level 8 — RO concentrate as the bridge to residuals and ZLD

Use the source to reinforce that RO design creates a concentrated residual stream whose management is part of plant design.

Topics include:

- reject/concentrate disposition options;
- reuse of reject where technically appropriate;
- how higher recovery changes reject volume and concentration;
- why scale-forming constituents become increasingly important in reject management;
- when a downstream MLD/ZLD strategy becomes necessary;
- handoff from Total RO Design to Total ZLD Design.

Detailed ZLD design remains owned by `app/total-zld-design`.

### Levels 9–10 — operations, lifecycle thinking and troubleshooting

The strongest advanced use of this source is to teach students to diagnose an RO as a system rather than treating every performance problem as a membrane problem.

Strengthen the capstone with:

- performance monitoring and data quality;
- normalization of permeate flow and rejection;
- preventive maintenance;
- recognizing loss of normalized flow, loss of rejection and increased pressure drop;
- membrane cleaning and stage-by-stage cleaning logic;
- system flush and lay-up concepts;
- instrumentation calibration and chemical-feed calibration;
- mechanical evaluation before assuming chemistry failure;
- distinguishing acute from chronic performance problems;
- water sampling and membrane integrity testing;
- profiling and probing;
- membrane autopsy as a last-stage investigative tool;
- checking the original design/projection before diagnosing operation;
- tying reliability, cleaning frequency, membrane replacement and redundancy back to lifecycle cost.

## 3. Interactive Academy missions inspired by the source

These should use original Academy graphics and validated TWDS data where numerical calculations are authoritative.

1. **RO stream builder** — identify feed, permeate and concentrate and close a simple water balance.
2. **Recovery slider** — increase recovery and observe concentrate flow, concentration factor and product-quality consequences.
3. **Boundary-layer visual** — compare bulk concentration with membrane-surface concentration and explain concentration polarization.
4. **Array builder** — assemble 2:1 and 4:2:1 arrays and maintain minimum cross-flow constraints using validated RO logic.
5. **Membrane spec-sheet challenge** — compare two membrane ratings and identify why differing test conditions make a direct comparison invalid.
6. **Tail-element risk mission** — follow concentration and scaling tendency from lead to tail elements.
7. **Pretreatment detective** — inspect raw-water constituents and build a defensible pretreatment sequence before RO.
8. **RO skid PFD mission** — place pressure, flow, conductivity, pH, temperature and ORP instruments where they provide diagnostic value.
9. **PLC start-up mission** — arrange permissives, valve positions, pump start, ramping, product divert and flush logic.
10. **VFD control mission** — adjust pressure to maintain production as water temperature or membrane resistance changes without violating hydraulic limits.
11. **Normalization detective** — decide whether an apparent performance change is due to temperature/pressure/concentration or true membrane degradation.
12. **Troubleshooting tree** — diagnose low normalized flow, high pressure drop or high salt passage using mechanical, hydraulic, chemical and membrane evidence.
13. **Profiling/probing mission** — localize first-stage fouling versus tail-stage scaling.
14. **Cleaning decision mission** — determine when cleaning is justified and which stage should be isolated.
15. **RO-to-ZLD handoff** — evaluate how a higher-recovery RO changes the volume and chemistry of the stream entering residuals/ZLD treatment.

## 4. Visual-teaching direction

The book demonstrates that simple engineering diagrams are powerful teaching tools. Academy should create its own interactive equivalents for:

- dead-end versus cross-flow filtration;
- a two-stage RO array;
- module-by-module flow/concentration progression;
- scaling tendency along a train;
- spiral-wound module anatomy;
- pump curves;
- RO skid PFDs;
- instrument-location maps;
- HMI/SCADA process screens;
- troubleshooting decision trees.

Do not copy copyrighted figures or photographs into the product unless separately licensed.

## 5. Date and authority policy

This edition was published in 2015. Therefore:

- conceptual principles may be used when still technically sound;
- manufacturer names, available products and design-software versions are historical context unless independently confirmed;
- membrane limits, recommended fluxes, chlorine exposure limits, silica limits, antiscalant allowances, cleaning thresholds and other numerical guidance must be checked against current manufacturer documentation and/or validated TWDS logic before being presented as current professional guidance;
- historical examples may be retained when clearly labeled as examples rather than current design limits;
- Academy should explicitly teach students to distinguish **a textbook rule of thumb** from **a project-specific validated design calculation**.

## 6. Engineering ownership

Academy owns pedagogy, explanations, exercises and diagnostic scenarios. It does not become the calculation authority.

- water chemistry → `engine/shared-water-chemistry`
- stream and mass balance → `engine/shared-waterstream` / `app/total-water-balance`
- pretreatment → `app/total-pretreatment-design`
- RO/NF design → `app/total-ro-design`
- ZLD → `app/total-zld-design`
- lifecycle economics → `app/total-water-economics`
- authentication, progress, entitlement and shared UI → `platform/suite-core`

## 7. Source/copyright rule

Use the book to identify concepts, sequencing, practical cases and diagnostic reasoning. Academy lessons should paraphrase and synthesize those ideas with current authoritative references and validated Suite behavior. Do not reproduce chapters, tables, photographs or figures from the source as Academy content without permission.
