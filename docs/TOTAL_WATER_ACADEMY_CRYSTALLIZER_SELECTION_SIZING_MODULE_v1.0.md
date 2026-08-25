# Total Water Academy — Crystallizer Selection & Sizing Module v1.0

Owner: `app/total-water-academy`
Curriculum targets: Level 8 (`L08-M02`, `L08-M03`, `L08-M04`) and Level 10 capstone.

## Purpose

Strengthen the Academy so students learn not only crystallization science, but how engineers translate crystallization thermodynamics and kinetics into an industrial crystallizer design basis.

This module is based on the provided *Handbook of Industrial Crystallization* excerpts, especially:

- D.L. Klug, “The Influence of Impurities and Solvents on Crystallization” (Chapter 3 excerpts provided by the user).
- K.A. Berglund, “Analysis and Measurement of Crystallization Utilizing the Population Balance” (Chapter 4 excerpts provided by the user).

Use these excerpts for concepts and original Academy teaching material. Do not reproduce publisher pages, figures, tables, or prose in the product.

## 1. What the learner must understand before sizing equipment

A crystallizer is not sized from feed flow alone. The design basis must connect:

1. feed and mother-liquor mass balance;
2. equilibrium solubility and the intended supersaturation path;
3. crystal growth and nucleation kinetics;
4. target crystal-size distribution (CSD), crystal habit and product purity;
5. slurry solids loading / suspension density;
6. residence time;
7. heat-removal or evaporation duty, depending on how supersaturation is generated;
8. mixing, circulation and mass-transfer behavior;
9. solids withdrawal, classification, fines handling and downstream dewatering;
10. impurity and solvent effects that can alter kinetics, habit, inclusion formation and purity.

Academy must teach students to define the desired **product crystal** and **process duty** before selecting equipment.

## 2. Population balance as the bridge from kinetics to equipment volume

For an ideal continuous mixed-suspension, mixed-product-removal (MSMPR) crystallizer with size-independent growth and no agglomeration, breakage, classification or seeding complications, the population density has the classical exponential form.

The key engineering relationships to teach conceptually are:

- mean residence time: `tau = V / Q`;
- the semilog population-density slope is controlled by `1/(G tau)`;
- the intercept provides the zero-size population density;
- nucleation and growth are connected through the population balance;
- moments of the population distribution can be used to calculate number, area and mass/suspension density.

The Academy should let students change `G`, `tau`, nucleation behavior and slurry flow and observe how the predicted CSD shifts.

### Existing Suite connection

The current Total ZLD Design workbook forensic inventory shows a simplified forced-circulation-crystallizer CSD screen based on the McCabe Delta-L / ideal MSMPR assumption, including a predominant crystal-size relation of `Lpd = 3 G tau` and the ideal-MSMPR theoretical coefficient of variation. This is useful pedagogically, but it is not a complete industrial crystallizer model.

Academy should explicitly explain the difference between:

- a **screening / idealized sizing relation**; and
- a **validated design calculation using actual kinetics, hydrodynamics, chemistry and equipment-specific behavior**.

## 3. Practical preliminary sizing workflow

Academy should teach the following sequence as a design workflow, not as a universal equipment vendor calculation.

### Step 1 — establish the crystallization duty

From the validated ZLD / chemistry owners determine:

- feed flow and composition;
- expected precipitating solids and precipitation sequence;
- mother-liquor composition;
- water evaporation or cooling duty;
- dry solids production rate;
- purge requirement;
- temperature, pressure and boiling-point-elevation regime where relevant.

### Step 2 — define the desired solid product

Specify learning targets such as:

- desired characteristic crystal size;
- acceptable CSD width;
- product purity;
- acceptable agglomeration;
- crystal habit / morphology important to downstream filtration or centrifugation;
- cake-moisture / dewatering objective;
- acceptable fines fraction.

### Step 3 — establish equilibrium and kinetic information

Use authoritative chemistry and experimental / validated kinetic data to determine:

- solubility as a function of temperature/composition;
- operating supersaturation;
- metastable-zone considerations;
- growth-rate expression;
- nucleation-rate behavior;
- effect of seeding when applicable;
- effect of impurities, solvent/solution composition and additives.

Do not infer a project growth rate from a textbook example.

### Step 4 — estimate residence time from the target CSD

For an introductory MSMPR exercise, learners may use the relationship between growth rate and residence time to estimate the order of magnitude of the residence time needed to obtain a desired crystal size.

Then challenge the assumption:

- Is growth independent of size?
- Is the semilog population plot linear?
- Is there evidence of growth-rate dispersion?
- Is agglomeration present?
- Is breakage/attrition present?
- Is product classification intentional?
- Are fines removed or destroyed?

If these conditions are violated, the simple MSMPR result is no longer sufficient.

### Step 5 — estimate working suspension volume

Once an appropriate residence-time basis is established, the idealized first estimate follows from `V = Q tau` on the correct slurry / suspension basis.

Students must then understand that the resulting vessel working volume is only one part of industrial sizing. A production design also needs vapor disengagement, freeboard, slurry circulation, solids inventory, heat-transfer/circulation equipment, nozzle arrangements, level control, turndown and mechanical margins from the authoritative design owner.

### Step 6 — close the solids inventory / suspension density

Use the population-distribution moments and crystal density / shape factors to relate CSD to suspension density and solids holdup.

The important learning point is that the same solids-production rate can correspond to very different numbers of crystals and different CSDs depending on nucleation and growth behavior.

### Step 7 — verify downstream solids handling

Selection is incomplete until the student checks whether the expected crystal size and habit are compatible with:

- settling/classification;
- centrifugation;
- filtration;
- washing;
- mother-liquor displacement;
- drying or disposal/recovery requirements.

## 4. Choosing crystallizer behavior / design features from CSD objectives

The provided population-balance excerpts directly support teaching how crystallizer design features alter residence-time distributions and therefore the CSD.

### Simple mixed suspension / mixed product removal

Use as the baseline educational model when an approximately exponential CSD and complete mixing assumptions are appropriate for learning.

### Classified product removal

Teach that selective removal of larger product can change the product residence time relative to small crystals and alter the product CSD.

### Fines destruction / fines removal

Teach that preferentially removing or dissolving small crystals can increase average product size, but the source also highlights the trade-off that larger average size may come with a wider distribution.

### Combined fines control + classified product removal

Teach this as an example of deliberately shaping the crystal residence-time distribution instead of accepting the natural MSMPR CSD.

### Agglomeration / breakage-sensitive systems

If CSD data show curvature or local maxima inconsistent with an ideal MSMPR semilog plot, students should investigate agglomeration, breakage, classification or growth-rate effects before forcing a simple model fit.

## 5. Source-supported diagnostic logic

The population-balance chapter provides a valuable diagnostic framework for interpreting semilog population-density plots.

Academy should create an original interactive CSD diagnostic where students identify whether the observed distribution is consistent with:

- ideal MSMPR behavior;
- size-dependent growth;
- growth-rate dispersion;
- agglomeration;
- classification;
- agglomeration plus breakup.

The goal is to teach that **model deviation is process information**, not merely bad data.

## 6. Impurities, mixing and solvent/solution composition as design variables

The Klug chapter is important because it prevents Academy from teaching crystallizer sizing as a purely geometric problem.

The provided excerpts show that impurities and solvent/solution environment can strongly affect:

- nucleation;
- crystal growth rate;
- relative face-growth rates and therefore crystal habit;
- impurity incorporation;
- inclusions;
- product purity;
- interfacial mass transfer.

One provided example shows impurity incorporation changing with crystal growth rate and agitation because boundary-layer transport changes. Another shows the same crystalline material exhibiting very different growth behavior in water versus ethanol. Academy should use original examples to teach the broader principle: kinetics measured in one solution environment cannot automatically be transferred to another.

For ZLD this should be translated from “solvent choice” into the broader and more relevant idea of **mother-liquor composition / ionic environment / impurities**.

## 7. Mixing and circulation lesson

Students should learn the non-trivial role of mixing:

- better mixing can reduce concentration and impurity boundary-layer limitations;
- circulation affects heat and mass transfer;
- excessive mechanical intensity can increase attrition or secondary nucleation in some systems;
- inadequate circulation can allow nonuniform supersaturation, deposition and poor suspension;
- growth and impurity incorporation can therefore depend on hydrodynamics, not only bulk supersaturation.

Do not convert these qualitative principles into arbitrary fixed circulation velocities in Academy. Numerical project limits belong to the validated ZLD / crystallizer design owner.

## 8. Interactive Academy missions

1. **MSMPR sizing lab** — choose target size and growth rate, solve for residence time, then calculate first-pass suspension volume.
2. **CSD slope lab** — infer `G tau` from a semilog population-density plot.
3. **Nucleation/growth lab** — show how changing nucleation while holding solids production constant changes particle count and size distribution.
4. **Model-violation detective** — diagnose curved or multimodal CSD data rather than forcing a straight-line MSMPR fit.
5. **Fines-control mission** — compare baseline MSMPR, fines destruction and classified product removal.
6. **Purity-versus-growth mission** — change growth rate and mixing and reason about impurity incorporation / boundary-layer effects.
7. **Mother-liquor chemistry mission** — show how changed solution chemistry alters the valid kinetic basis and forces the learner to request new data rather than reuse an unrelated growth law.
8. **Dewatering handoff** — select a preferred CSD/habit target based on centrifuge or filtration needs.
9. **ZLD crystallizer design-basis mission** — assemble feed chemistry, solids load, evaporation duty, kinetic basis, residence time, target CSD and solids-handling requirements into a design-basis sheet.
10. **Screening-vs-production-design challenge** — identify which outputs are safe educational estimates and which require the validated Total ZLD Design owner.

## 9. What these excerpts do NOT yet establish

These source excerpts provide strong support for population-balance sizing, CSD control, kinetic interpretation, impurity effects and design-feature reasoning.

They do **not**, by themselves, provide a complete authoritative selection matrix among specific industrial crystallizer equipment families or vendors.

Academy should therefore not yet publish universal rules such as “use crystallizer type X whenever condition Y occurs” unless those rules are supported by a direct authoritative crystallizer-design source and reconciled with Total ZLD Design.

A future equipment-selection source should explicitly support comparison of items such as:

- method of supersaturation generation;
- circulation arrangement;
- heat-transfer arrangement;
- vapor/flash disengagement;
- solids classification;
- fines destruction;
- crystal size target;
- solids concentration;
- fouling/scaling tendency;
- viscosity;
- boiling-point elevation;
- corrosion/materials constraints;
- turndown;
- mechanical reliability and maintainability.

Until then, Academy can teach the **questions an engineer must answer before selecting a crystallizer**, while avoiding unsupported equipment-selection rules.

## 10. Suite integration / authority

Academy owns pedagogy, interactive visualization and the learning sequence.

Authoritative project calculations remain with:

- solution chemistry / phase behavior → `engine/shared-water-chemistry` and approved ZLD thermodynamic owner;
- stream / mass balance → `engine/shared-waterstream` / `app/total-water-balance`;
- ZLD, evaporation and crystallizer project design → `app/total-zld-design`;
- economics → `app/total-water-economics`;
- accounts/progress/access → `platform/suite-core`.

Academy must not silently replace validated ZLD calculations with its own crystallizer equations.

## 11. Confidential-source boundary

Internal customer proposals and proprietary project documents may demonstrate real industrial configurations, but they are not Academy publishing sources. Do not reproduce confidential project flows, capacities, chemistry, equipment details, pricing or customer information in Academy content.

Use publishable references and validated Suite logic for learner-facing material.

## 12. Next source needed

The highest-value next source is a rigorous crystallizer equipment-design chapter or manual that explicitly compares industrial crystallizer families and gives defensible design/selection criteria. That source should allow us to complete the equipment-selection matrix without relying on generic rules of thumb.
