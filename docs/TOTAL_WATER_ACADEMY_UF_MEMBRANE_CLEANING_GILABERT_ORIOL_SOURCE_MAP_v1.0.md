# Total Water Academy — UF Membrane Cleaning & Cleaning Optimization — Gilabert-Oriol Source Map v1.0

## Purpose

This source map adds a dedicated **UF membrane cleaning and cleaning-optimization teaching block** to Total Water Academy.

It is based primarily on the user-supplied photographed pages from:

**Guillem Gilabert-Oriol, _Ultrafiltration Membrane Cleaning Processes: Optimization in Seawater Desalination Plants_, De Gruyter, 2021. DOI: 10.1515/9783110715149.**

The uploaded source pack contains 105 photographed pages spanning the book's cleaning research, modeling, seawater validation, RO-brine backwash work, integrated conclusions and operating/control implications.

The book consolidates work originally developed through Gilabert-Oriol's doctoral and industrial research on pressurized UF as pretreatment to seawater reverse osmosis. The Academy should treat it as an unusually valuable **expert/practitioner + research-grounded specialist source** because the author connects experimental work, plant operating data, statistical optimization, membrane cleaning, process efficiency, downstream RO protection and operating economics.

A useful current corroborating source is:

- Morten Lykkegaard Christensen and Guillem Gilabert-Oriol, "Microfiltration and ultrafiltration," in _Experimental Methods for Membrane Applications in Desalination and Water Treatment_, IWA Publishing, 2024, DOI chapter 10.2166/9781789062977_0027. The chapter lists Gilabert-Oriol with DuPont Water Solutions, Spain and retains the same core framework of hydraulic cleaning, backwash optimization, CEB and tailored CIP.

This source map does **not** turn any DuPont/Dow operating recipe, Tarragona test condition, historical setpoint, chemical concentration, cycle frequency, product geometry or cost result into a universal Total Water Design Suite design rule.

---

# 1. Evidence classification

## 1.1 What can be taught strongly

The following can be taught as robust engineering concepts when presented with the appropriate system context:

- membrane cleaning is part of process design and production optimization, not merely a maintenance activity;
- fouling reversibility matters when choosing a cleaning mechanism;
- hydraulic cleaning, chemically enhanced backwash and CIP serve different purposes and time scales;
- every cleaning consumes some combination of productive time, water, energy, chemical inventory and membrane life;
- cleaning performance must therefore be judged against **net plant performance**, not simply maximum instantaneous foulant removal;
- a backwash sequence is a collection of unit operations, and each substep should have a defensible physical purpose;
- experimental comparison can determine whether a cleaning substep provides incremental value;
- cleaning frequency has an optimum: too little cleaning can accelerate fouling, while excessive cleaning can waste production time/water/chemicals and impose unnecessary membrane stress;
- TMP and normalized permeability trends provide evidence about filtration/fouling/cleaning behavior when interpreted with temperature, flux, feed quality and hydraulic state;
- empirical cleaning/fouling models are valid only inside the operating envelope for which they were developed and validated;
- an upstream UF cleaning sequence must be designed with its downstream customer in mind, especially a chlorine-sensitive RO membrane process;
- dose at a chemical injection point is not equivalent to residual/exposure everywhere in a train;
- valve sequencing, pump ramps, drain/flush paths, dead volumes and backflow can materially affect the success and safety of a cleaning sequence;
- unconventional cleaning-water sources such as RO brine require chemistry, compatibility and pilot validation before use.

## 1.2 What remains source-specific or historical

Treat all of the following as **case-study evidence, not universal design criteria** unless independently verified against current manufacturer and project authority:

- exact filtration fluxes;
- exact backwash fluxes/flows;
- 20, 30, 60, 80, 90, 120 minute filtration-cycle examples;
- individual backwash-step durations;
- exact air-scour rates;
- exact CEB and CIP concentrations;
- exact NaOCl, NaOH, acid or other cleaning-chemical doses;
- daily, multi-day or other CEB frequencies;
- any maximum TMP/CIP trigger stated in the source;
- the source's SFP module/fiber/product geometry;
- Tarragona Mediterranean seawater properties;
- 2010s Dow/DuPont equipment limitations or operating practices;
- the source-reported process-efficiency improvements;
- cost-of-water savings percentages;
- chemical-consumption reductions;
- specific RO-brine backwash outcomes;
- PVDF-versus-PES performance observations beyond the actual tested products and conditions.

Current manufacturer O&M manuals, membrane chemical-compatibility limits, current regulatory requirements and the authoritative Total Pretreatment Design implementation remain project authority.

---

# 2. Primary curriculum placement

## Level 3 — Pretreatment & Solids Separation

Primary home:

**L03-M04 — MF/UF Pretreatment and Fouling Risk**

Create a substantial authored block tentatively titled:

**UF Membrane Cleaning, Recovery & Cleaning Optimization**

The block should be large enough to function as a chapter/subchapter within the existing module but should not add guided hours to the 360-hour Academy total.

Level 3 should teach the complete operational hierarchy:

**filtration → hydraulic cleaning → CEB → CIP → diagnosis / revalidation**

with emphasis on why, when and how each step is chosen.

## Level 2 — Unit Operations / Transport

Prerequisite concepts:

- TMP;
- flux and permeability;
- resistance buildup;
- concentration/cake layers;
- pore blocking;
- reversible versus persistent resistance;
- pressure-driven transport;
- shear and solids transport;
- chemical concentration versus actual exposure.

## Level 6 — Pumps, Energy & Electrical

Connect cleaning to:

- backwash pump duty;
- instantaneous versus average duty;
- air-scour blower duty;
- ramp times;
- valve transition time;
- hydraulic transients;
- water-hammer risk;
- cleaning-energy accounting;
- pump and valve sequencing constraints.

## Level 7 — Instrumentation, Process Control & PLC

Use UF cleaning as a major controls case:

- filtration state;
- relaxation/drain state where applicable;
- backwash top/bottom states where applicable;
- air-scour state;
- forward-flush state;
- CEB chemical fill/contact/soak/displacement/rinse;
- post-CEB filtrate-to-waste or rinse state;
- CIP isolation/permissives;
- TMP/permeability alarms;
- oxidant monitoring;
- valve proof/open-close permissives;
- pump/blower permissives;
- chemical-tank low-level and dosing interlocks;
- downstream RO protection logic;
- return-to-service criteria.

## Level 9 — Economics / project-development integration

Teach the commercial/lifecycle consequences of cleaning:

- productive availability;
- recovery;
- net production;
- water consumed for cleaning;
- chemical mass per treated volume;
- energy;
- labor;
- CIP frequency;
- membrane replacement risk;
- waste disposal;
- Total Water Cost.

Do not lock this material to the current executable Level 9 module titles until the previously identified Level 9 curriculum reconciliation is complete.

## Level 10 — Capstone

Require a **UF Cleaning Philosophy and Optimization Plan** where UF/MF is used.

The learner should defend:

- foulant risks;
- hydraulic-cleaning philosophy;
- CEB philosophy;
- CIP philosophy;
- monitoring variables;
- cleaning triggers;
- water/chemical balance;
- downstream-process protection;
- residuals handling;
- validation/pilot plan;
- assumptions and current manufacturer limits.

---

# 3. Central teaching principle — cleaning is a production optimization problem

The strongest transferable lesson from Gilabert-Oriol is:

> Do not ask only "How clean can I make the membrane?" Ask "Which cleaning strategy gives the most reliable net production at acceptable membrane condition, water recovery, chemical use, energy, risk and cost?"

Academy should repeatedly distinguish:

- **gross filtration flux** from **net plant production**;
- **instantaneous cleaning effectiveness** from **whole-cycle efficiency**;
- **maximum cleaning intensity** from **minimum sufficient cleaning**;
- **membrane cleanliness** from **plant optimization**.

A cleaning sequence can remove fouling and still be economically poor if it consumes excessive productive time, filtrate, air, chemicals or membrane life.

---

# 4. Cleaning ladder and fouling reversibility

Teach cleaning as an escalation ladder rather than as one recipe.

## 4.1 Hydraulic cleaning

Examples include, depending on membrane/module/vendor design:

- relaxation;
- backflush/backwash;
- forward flush;
- air scour combined with liquid movement;
- drain/displacement steps.

Primary role: remove or redistribute **reversible hydraulic fouling** and restore permeability without chemical exposure.

Do not state that every module supports every hydraulic step.

## 4.2 Chemically enhanced backwash (CEB)

CEB is a more intensive periodic cleaning intervention intended to address fouling that hydraulic cleaning does not adequately control.

Teach:

- chemical identity should respond to foulant mechanism and membrane compatibility;
- concentration at the tank/injection point is not the same as exposure at the membrane surface;
- contact time, mixing/displacement, pH, temperature and oxidant demand can matter;
- rinse/displacement after CEB is a process-design requirement, especially when a sensitive downstream process exists;
- the objective is adequate restoration/control, not "maximum chemical dose";
- repeating a CEB more often than necessary can reduce recovery/availability and increase chemical burden.

## 4.3 CIP

CIP is the higher-intensity restoration step for fouling that cannot be sustainably managed through normal hydraulic cleaning and CEB.

Teach CIP as **foulant-specific and condition-specific**.

The source framework associates, in its context:

- particle/reversible deposits primarily with hydraulic cleaning;
- biological fouling with oxidizing CEB where membrane compatibility permits;
- inorganic deposits with acidic cleaning approaches;
- organic deposits with alkaline/caustic cleaning approaches.

Academy must clearly label this as a useful **source framework**, not a complete universal chemical-selection rule. Real CIP selection requires foulant diagnosis, membrane-material compatibility, current vendor procedure, chemical safety and waste handling.

---

# 5. Backwash anatomy — every step needs a physical job

Gilabert-Oriol's seawater work is especially valuable because it challenges the assumption that a longer sequence with more steps is automatically safer.

The studied sequence included combinations of:

- air scour;
- drain;
- top backwash with/without air scour;
- bottom backwash;
- forward flush.

A factorial Design of Experiments (DoE) and ANOVA approach was used to evaluate which steps materially affected the chosen responses.

In the studied system, the researchers found that a multi-step sequence could be reduced substantially while maintaining cleaning performance. The engineering significance is **not** "use only two steps." It is:

**prove the incremental value of every cleaning substep.**

For each candidate step, Academy should ask:

1. What physical mechanism is this step intended to provide?
2. What measurable response should improve if the mechanism matters?
3. Is another step already providing the same mechanism?
4. Does the step remove foulant, displace dirty water, change shear, release trapped solids, or merely consume time?
5. What is the hydraulic/energy/water cost?
6. What happens if it is removed?
7. Was the altered sequence validated long enough to observe delayed consequences?

---

# 6. Design of Experiments and statistical cleaning optimization

This source should introduce students to **engineering experimentation**, not just membrane operations.

Teach the workflow:

**define factors → define responses → design experiment → control confounders → collect cycle data → analyze main effects/interactions → identify candidate simplification → validate side-by-side → confirm long-term TMP behavior → quantify economic impact.**

Possible factors:

- presence/absence of a BW substep;
- BW duration;
- BW frequency;
- air scour;
- forward flush;
- CEB frequency;
- CEB concentration;
- CEB contact/soak time;
- cleaning-water source.

Possible responses:

- TMP recovery;
- normalized permeability recovery;
- TMP rise during subsequent filtration;
- cycle-to-cycle irreversible TMP change;
- net production;
- recovery;
- availability;
- chemical burden;
- energy;
- water consumed;
- integrity failures;
- downstream oxidant residual.

Teach ANOVA as a way to distinguish an apparent difference from a statistically defensible effect under the experiment—not as proof of universality outside the test envelope.

---

# 7. The TMP sawtooth — convert operating history into a cleaning model

A particularly strong Academy visualization should be an original **TMP sawtooth model**.

For each filtration/cleaning cycle identify:

- TMP at the start of filtration;
- TMP at the end of filtration;
- TMP immediately before hydraulic cleaning;
- TMP after hydraulic cleaning;
- TMP before CEB;
- TMP after CEB.

Conceptually separate three behaviors:

### A. Fouling accumulation during filtration

`ΔTMP_filtration = TMP_end_filtration - TMP_start_filtration`

Interpret with caution because TMP also depends on flux, viscosity/temperature and membrane state.

### B. Hydraulic-cleaning recovery

`ΔTMP_BW = TMP_before_BW - TMP_after_BW`

Use this to reason about reversible foulant removal, while also watching whether the post-BW baseline itself drifts upward over many cycles.

### C. CEB recovery

`ΔTMP_CEB = TMP_before_CEB - TMP_after_CEB`

A larger decrease is not automatically "better" if the system was being over-cleaned or chemical intensity is unnecessary.

The Academy should teach the difference between:

- within-cycle reversible increase;
- post-backwash baseline;
- long-term baseline drift;
- post-CEB reset;
- eventual CIP trigger.

The book's empirical model used these cycle-level relationships to predict TMP evolution and examine cleaning-frequency/cost scenarios.

The teaching value is the modeling method, not copying the coefficients.

---

# 8. Model envelope and extrapolation discipline

This must be a prominent **Common Mistake** lesson.

## Common mistake

"The regression/model predicted this UF well, so I can apply it to another water, flux, membrane or season."

## Why tempting

The fitted equation can have reasonable correlations and appears physically intuitive.

## Why it fails

An empirical model encodes the tested:

- membrane/module;
- water quality;
- temperature;
- flux;
- pretreatment condition;
- cleaning chemicals;
- cycle frequencies;
- fouling regime;
- measurement uncertainty.

Outside that domain, the response surface can change.

## How to catch it

Require an explicit **model applicability envelope** before using any empirical cleaning model.

## How to correct it

Revalidate or refit with representative data from the new operating regime.

---

# 9. Availability, recovery and cleaning-adjusted process efficiency

Use the source's comparative metrics to teach whole-system accounting.

### Productive availability

`Availability = productive filtration time / total elapsed time`

### Water recovery

`Recovery = useful product water / feed water`

The source also uses a comparative process "efficiency" combining availability and recovery.

Academy may teach that source-defined metric as:

`Source cleaning/process efficiency = Availability × Recovery`

but must label it as the **source's process-efficiency definition**, not a universal membrane-industry definition of efficiency.

This distinction is important because "efficiency" can mean energy efficiency, pump efficiency, removal efficiency, process yield or other metrics elsewhere in TWDS.

---

# 10. Continuous Equivalent Chemical concentration / normalized chemical burden

The source uses a normalized chemical-burden concept so cleaning strategies with different concentration, duration and frequency can be compared on a common basis.

Academy should teach the broader concept:

**chemical burden per treated feed/product volume and time basis**

rather than memorizing a single CEC formula without context.

Students should calculate and compare:

- dose concentration;
- chemical solution volume;
- chemical active mass;
- number of events per day/week;
- feed/product volume processed;
- chemical mass per m³;
- residual-neutralization/disposal implications.

Key lesson:

**a high-concentration but rare event can use less or more total chemical than a low-concentration frequent event; concentration alone does not describe chemical burden.**

---

# 11. Frequency optimization — under-cleaning versus over-cleaning

Create a two-sided operating window.

## Under-cleaning can lead to

- rising irreversible TMP;
- declining permeability;
- shortened filtration cycles;
- more frequent CIP;
- localized fouling;
- higher energy/TMP;
- loss of capacity;
- potentially harder-to-remove deposits.

## Over-cleaning can lead to

- lower productive availability;
- lower water recovery;
- more filtrate consumed for BW;
- excessive chemical use;
- more neutralization/waste;
- increased operator/maintenance burden;
- potentially unnecessary membrane chemical exposure;
- pump/blower/valve cycling;
- avoidable lifecycle cost.

This is one of the most important lessons from the source.

Do not make "lower TMP after cleaning" the only optimization objective.

---

# 12. A powerful diagnostic — CEB always returns to the same low TMP

Gilabert-Oriol's analysis found CEB response could show weak dependence on the starting TMP while repeatedly restoring the system to a similar lower state in the studied conditions.

Academy should turn this into a reasoning exercise:

**If CEB repeatedly restores substantially more permeability/TMP than needed, could the CEB be more frequent or more intense than necessary?**

Possible hypotheses to investigate:

- CEB is appropriately preventive and preserving stability;
- CEB frequency could be reduced;
- chemical concentration could be reduced;
- contact time could be reduced;
- some foulant is being removed that is not visible in TMP alone;
- biological risk requires the existing schedule even when TMP appears healthy;
- the apparent full reset may be temperature/flux normalization artifact;
- downstream risk or membrane-life constraints dominate.

The Academy must **not** teach automatic dose reduction from this pattern. It should teach hypothesis formation + controlled validation.

---

# 13. Hidden downtime — valves, pumps and transition states

A cleaning event costs more productive time than the nominal backwash-flow duration.

Include:

- stopping filtration;
- pump deceleration;
- valve closure/opening time;
- drain/fill time;
- blower start/stop;
- backwash-pump ramp;
- chemical displacement;
- rinse;
- repressurization;
- filtrate-to-waste stabilization;
- return to production.

This supports an important controls/economics lesson:

**two cleaning strategies with the same nominal backwash seconds can have different availability because their transition states differ.**

---

# 14. UF → RO interface — cleaning chemistry does not stop at the UF boundary

This is one of the most valuable systems-engineering lessons in the source.

When UF pretreats RO, oxidant or cleaning-chemical carryover can threaten the downstream membrane or interfere with downstream chemistry.

Teach students to map:

**chemical tank → dosing pump → injection point → header → UF module → dead volumes → backwash/flush path → filtrate header → RO feed.**

Potential failure mechanisms discussed by the source include:

- chemical injected too late in a sequence;
- inadequate displacement/rinse;
- diffusion/backflow from chemical-injection piping;
- dead volume retaining chemical;
- incorrect valve sequence;
- insufficient post-CEB flush water/time;
- using an optimized normal backwash sequence for post-chemical removal without proving it provides adequate displacement.

Academy should teach safeguards as design logic, not a copied recipe:

- stop chemical addition early enough to allow displacement;
- prevent unintended backflow/diffusion through injection arrangements;
- define a dedicated post-CEB rinse/flush where required;
- explicitly prove the rinse path reaches all relevant volume;
- use appropriate drains/flushes where needed;
- verify residual before releasing the stream to chlorine-sensitive downstream membranes;
- interlock downstream process availability against cleaning state/residual where justified.

Current RO membrane chlorine tolerance and neutralization requirements remain with current manufacturer and Total RO Design authority.

---

# 15. ORP/redox monitoring — useful signal, not automatically a chlorine analyzer

The source uses redox/ORP behavior as a practical indication of oxidant presence/trend.

Academy should teach:

- ORP responds to the overall oxidation-reduction environment;
- it can be very useful for detecting a change, breakthrough or persistence of oxidizing conditions;
- ORP is **not inherently a quantitative free-chlorine measurement**;
- calibration/correlation can be water-specific;
- pH, temperature and other redox couples can influence the signal.

Therefore:

**ORP trend ≠ exact chlorine concentration.**

If an exact chlorine/residual criterion is required, use an appropriate validated analytical/instrument method.

---

# 16. Advanced research case — backwashing UF with RO brine

The source presents side-by-side work where RO brine was used as the UF backwash fluid in an integrated seawater system and reports comparable cleaning performance without the tested precipitation/integrity problems during that specific validation.

This is an excellent advanced Academy decision case because it challenges the assumption that only permeate can ever be used for BW while also requiring rigorous caution.

Academy must label it:

**RESEARCH / SITE-SPECIFIC VALIDATION CASE — NOT A DEFAULT TWDS RECOMMENDATION.**

Before considering a nonstandard BW water source, require analysis of:

- ionic concentration and saturation state;
- pH;
- temperature;
- antiscalant carryover;
- reducing agent/SMBS carryover;
- oxidant demand;
- suspended/colloidal load;
- compatibility with membrane/module materials;
- cleaning direction and concentration polarization effects;
- precipitation risk during mixing/contact;
- hydraulic pressure/flow requirements;
- impact on integrity testing;
- effect on subsequent filtrate quality;
- waste/recovery implications;
- pilot or side-by-side evidence.

The right Academy question is:

**"What evidence would make brine backwash defensible here?"**

not:

**"What brine concentration is safe?"**

---

# 17. Membrane material observations

The source contains comparative observations involving PVDF and PES-family materials/products.

Teach the general lesson:

- polymer chemistry;
- pore structure;
- mechanical construction;
- hydrophilicity;
- oxidant/chemical tolerance;
- foulant interaction;
- manufacturer surface treatment;
- module design

can change cleaning response.

Do not teach "PVDF is always more cleanable" or any other universal ranking from the tested products.

Product-specific cleaning compatibility remains manufacturer authority.

---

# 18. Lean / waste-elimination lens

The book uses Lean Six Sigma thinking to identify cleaning steps that may not add value.

This can be taught carefully as an engineering-improvement framework:

### Possible cleaning waste

- excess waiting/downtime;
- unnecessary water consumption;
- redundant motion/valve states;
- excessive chemical inventory;
- repeated steps with no measurable incremental restoration;
- overprocessing/over-cleaning;
- unnecessary energy;
- unnecessary maintenance cycles.

The engineering safeguard is that a step is not removed merely because it looks wasteful. It is removed only after the learner defines its intended risk-control function and validates that function is preserved.

---

# 19. Proposed learner exercises

## Exercise 1 — Which Backwash Step Actually Cleans?

Given a five-step BW sequence and cycle data, identify the physical purpose of each step and define the experiment needed to prove incremental value.

## Exercise 2 — Five Steps or Two? DoE Detective

Interpret a simplified factorial experiment. Separate main effect, interaction and noise. Recommend a candidate sequence for validation without claiming universality.

## Exercise 3 — Gross Flux vs Net Flux

Compare two operating strategies: one with higher gross flux but frequent BW and one with lower gross flux but higher productive availability/recovery.

## Exercise 4 — The Cleanest Membrane Is Not the Best Plant

Choose between cleaning strategies using net production, chemical burden, water use, energy and TMP stability.

## Exercise 5 — Build the TMP Sawtooth

Plot repeated filtration/BW/CEB cycles and identify reversible fouling, baseline drift and the effect of CEB.

## Exercise 6 — Over-Cleaning or Under-Cleaning?

Diagnose a plant where CEB always returns TMP to nearly the same low value. Propose hypotheses and a controlled validation plan rather than immediately reducing chemical.

## Exercise 7 — Stay Inside the Model Envelope

Give students a regression developed on one seawater/temperature/flux range and ask whether it may be applied to a new season, membrane or industrial water.

## Exercise 8 — Hidden Downtime

Build a complete cleaning timeline including ramps, valve travel, drains, refill, rinse and stabilization. Calculate productive availability rather than counting only nominal BW seconds.

## Exercise 9 — CEB State Machine

Write the state logic, permissives and interlocks for an oxidizing CEB followed by a protected return to service.

## Exercise 10 — Where Did the Chlorine Go?

Trace oxidant from injection to UF and downstream RO. Identify dead volumes, diffusion/backflow paths and incorrect sequencing that could produce unexpected RO exposure.

## Exercise 11 — ORP Says Something Changed

Interpret ORP trend versus exact chlorine measurement. Decide what additional measurement is needed before declaring the stream safe.

## Exercise 12 — Can We Backwash with RO Brine?

Assess chemistry, scaling, antiscalant/SMBS carryover, membrane compatibility and validation requirements. No universal answer is provided.

## Exercise 13 — Cleaning Cost per m³

Calculate water, chemical, energy, downtime and labor burden for several cleaning strategies.

## Exercise 14 — Side-by-Side Validation

Design an A/B validation with matched feed water and controlled operating conditions. Define success criteria and minimum observation period appropriate to the risk.

## Capstone exercise — Defend the UF Cleaning Philosophy

The learner presents a complete strategy including:

- foulant hypotheses;
- hydraulic cleaning;
- CEB;
- CIP;
- triggers;
- monitoring;
- controls;
- downstream membrane protection;
- residuals;
- lifecycle economics;
- pilot data gaps;
- current vendor constraints.

---

# 20. Common mistakes to teach explicitly

1. **More frequent BW is always better.**
   - False. More cleaning can reduce net availability/recovery and increase lifecycle burden.

2. **More BW steps are always safer.**
   - False. Some steps may duplicate a physical function; prove incremental value.

3. **The highest chemical concentration gives the best CEB/CIP.**
   - False. Cleaning must balance efficacy, membrane compatibility, exposure, waste and cost.

4. **CEB and CIP are interchangeable.**
   - False. They differ in function, intensity, frequency and restoration role.

5. **A low post-clean TMP proves the membrane has no fouling.**
   - False. TMP alone may miss biological/organic/integrity risks and must be normalized/interpreted.

6. **If CEB always resets TMP, the current schedule must be optimal.**
   - False. It may be appropriate or excessive; test the hypothesis.

7. **An empirical TMP model can be extrapolated to any UF.**
   - False. State and respect the validation envelope.

8. **A book's typical BW/CEB/CIP values are current universal limits.**
   - False. Product and project authority are current manufacturer/validated design sources.

9. **RO brine is proven as a generally safe UF BW fluid.**
   - False. The source demonstrates a tested case; chemistry/site validation is required.

10. **ORP equals free chlorine concentration.**
    - False. ORP is a redox signal, not inherently a quantitative chlorine analyzer.

11. **An optimized normal BW is automatically enough for post-CEB rinse.**
    - False. Chemical displacement and downstream protection must be demonstrated independently.

12. **UF cleaning cannot affect downstream RO.**
    - False. Cleaning chemicals can cross the process boundary through hydraulics, sequencing and dead volumes.

13. **Shorter cleaning is automatically better.**
    - False. Reduced downtime only has value if membrane performance, reliability, integrity and downstream protection remain acceptable.

14. **A statistically significant step removal is automatically plant-safe.**
    - False. Statistical evidence must be combined with physical mechanism, long-term validation and risk analysis.

---

# 21. Recommended original Academy graphics

Do not copy publisher figures. Create original TWDA graphics such as:

1. **Cleaning ladder** — Reversible fouling → Hydraulic → CEB → CIP.
2. **TMP sawtooth** — filtration rise / BW reset / long-term baseline / CEB reset / CIP boundary.
3. **Cleaning-value waterfall** — productive time versus transition/cleaning downtime.
4. **DoE response matrix** — candidate BW steps versus TMP/net-production responses.
5. **Over-cleaning window** — under-cleaning risk ↔ sustainable zone ↔ over-cleaning burden.
6. **UF→RO chemical-path map** — CEB injection, dead volume, flush and downstream RO.
7. **Chemical burden dashboard** — concentration × volume × frequency normalized per water produced.
8. **Model applicability envelope** — water quality / temperature / flux / membrane / chemical regime.
9. **Brine-BW decision tree** — chemistry → compatibility → pilot → monitoring → accept/reject.
10. **Cleaning state machine** — filtration / BW / CEB / rinse / waste / return-to-service.

---

# 22. Evidence hierarchy for numerical content

Before putting a number from this book into a learner-facing design input, classify it.

### Class A — physical/mechanistic relationship

May be taught generally if correctly derived and supported.

### Class B — experimental result

Teach as:

> "In Gilabert-Oriol's tested seawater UF system..."

### Class C — product/vendor operating condition

Teach as a data-sheet/O&M interpretation exercise, not a universal value.

### Class D — historical rule/range

Label with year/source and require current verification.

### Class E — current project design criterion

Must come from current authoritative manufacturer/regulatory/validated TWDS owner input, not merely from this source map.

---

# 23. Specific source results that are valuable but must remain contextual

The uploaded book reports, for its tested/modelled systems, substantial gains from:

- removing BW substeps that did not add measurable value;
- extending filtration time/reducing BW frequency;
- reducing cleaning-water consumption;
- adjusting CEB strategy;
- using RO brine as BW water in a validated research configuration;
- empirical TMP-cycle modeling;
- improving overall UF process availability/recovery;
- reducing modeled/observed water-production cost.

Academy may discuss those results as evidence that optimization can matter greatly.

Academy must **not** infer that another UF plant will obtain the same efficiency, recovery or cost savings.

---

# 24. Relationship to existing Pearce UF/MF curriculum

Pearce remains the broader backbone for:

- UF/MF fundamentals;
- membrane/module configurations;
- fouling mechanisms;
- operating philosophy;
- integrity;
- drinking-water/reuse/SWRO applications;
- commissioning and troubleshooting.

Gilabert-Oriol adds a deeper specialist layer for:

- cleaning-sequence optimization;
- experimental design;
- cleaning economics;
- TMP-cycle modeling;
- over-cleaning diagnosis;
- whole-process availability/recovery accounting;
- UF→RO cleaning-chemical interface;
- unconventional BW-water validation.

The two sources complement rather than duplicate one another.

---

# 25. Current 2024 corroboration

The 2024 IWA MF/UF chapter by Christensen and Gilabert-Oriol supports continued teaching of the core framework:

- hydraulic cleaning methods include backwash/backflush/relaxation depending on system;
- cleaning effectiveness should be judged from operating response rather than assumed;
- backwash sequence and frequency can be optimized;
- persistent/biological fouling can require CEB;
- CIP is tailored to fouling type and system requirements;
- cleaning optimization should support sustainable operation and flux rather than maximize one isolated variable.

This newer source helps distinguish the durable methodology from older system-specific numbers in the 2021 book/earlier research.

---

# 26. Authority boundaries

Academy owns:

- explanation;
- visualizations;
- exercises;
- evidence literacy;
- experimental-design training;
- operational reasoning;
- cleaning-strategy comparison;
- diagnostic reasoning;
- controls narratives;
- capstone defense.

Academy does **not** own:

- current UF membrane chemical compatibility;
- allowable NaOCl exposure;
- allowable pH/temperature;
- project backwash flow/pressure;
- CEB/CIP recipe selection;
- project CIP trigger;
- manufacturer warranty limits;
- project RO chlorine tolerance;
- project scaling/precipitation prediction for brine BW;
- current product-specific cleaning sequences.

These remain with current manufacturer data and the validated specialist application/engine owners, particularly Total Pretreatment Design and downstream Total RO Design where applicable.

---

# 27. Implementation status

This document is a **source/curriculum architecture addition only**.

It does not:

- modify Academy runtime routes;
- change the current 360 guided hours;
- change the 50-course catalog;
- alter Academy pricing;
- modify the multilingual runtime;
- add project-grade UF equations;
- change Total Pretreatment Design;
- change Total RO Design;
- change Suite Core;
- change Alpha deployment wiring.

When the L03-M04 learner-facing chapter is authored, all final learner content must also enter the Academy English / `es-419` / Arabic translation workflow under the existing multilingual contract.

---

# 28. Final teaching statement

The Academy should leave the learner with this principle:

**A UF cleaning protocol is not a sacred vendor sequence and it is not a contest to make the membrane as clean as possible. It is an engineered control strategy. Every step must have a mechanism, measurable benefit, acceptable risk and lifecycle justification—and any optimization must be validated inside the actual membrane/water/operating envelope before it becomes a plant standard.**
