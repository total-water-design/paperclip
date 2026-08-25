# Total Water Academy — Algal Blooms & SWRO Resilience Source Map v1.0

Owner: `app/total-water-academy`

Status: educational/source architecture

Companion source maps:

- `TOTAL_WATER_ACADEMY_SWRO_PRETREATMENT_ALGAL_BLOOMS_SOURCE_MAP_v1.0.md`
- `TOTAL_WATER_ACADEMY_SWRO_INTAKES_OUTFALLS_MARINE_INFRASTRUCTURE_SOURCE_MAP_v1.0.md`

## Purpose

This source map adds a dedicated **algal-bloom science and SWRO resilience** layer to Total Water Academy.

It is intentionally broader than the existing pretreatment source map. The learner should not merely know that DAF, GMF or UF may be used during a bloom. The learner should understand the complete causal chain:

**coastal environment + species + bloom phase**
→ **cell concentration / cell morphology**
→ **EOM + IOM + AOM production**
→ **biopolymer / TEP generation and transformation**
→ **intake and pretreatment loading**
→ **UF fouling / capillary plugging / loss of backwashability**
→ **RO organic conditioning layer / spacer deposition**
→ **biofilm acceleration when nutrients are available**
→ **post-bloom recovery and delayed biofouling risk**.

The Academy should teach students to recognize that an algal bloom is a **time-varying biological, chemical, colloidal and hydraulic event**, not a single water-quality number.

## Primary supplied reference

Loreen Ople Villacorte, **Algal Blooms and Membrane Based Desalination Technology**, doctoral dissertation, Delft University of Technology / UNESCO-IHE Institute for Water Education, 2014; CRC Press/Balkema.

This source is particularly valuable because it integrates:

- bloom ecology and species differences;
- harmful versus non-harmful blooms;
- bloom life-cycle behavior;
- algal organic matter (AOM);
- extracellular organic matter (EOM);
- intracellular organic matter (IOM);
- transparent exopolymer particles (TEP);
- membrane-fouling mechanisms;
- TEP measurement and monitoring;
- MFI-UF;
- UF capillary plugging;
- solution-chemistry effects on algal biopolymer fouling;
- organic-fouling versus biofouling transitions;
- pretreatment-response strategies;
- integrated plant monitoring and resilience.

## Supporting supplied reference

T. M. Missimer et al., **Subsurface intakes for seawater reverse osmosis facilities: Capacity limitation, water quality improvement, and economics**, *Desalination* 322 (2013) 37–51.

This supporting source is used only where the Academy connects algal-bloom resilience to subsurface intake selection and source-water quality improvement. The detailed intake technology curriculum remains in the dedicated intake/outfall source map.

---

# 1. Historical / current-practice safeguard

The Villacorte dissertation is a high-quality 2014 research source. It is authoritative for the experimental observations and mechanistic interpretations it reports, but historical numerical values in the dissertation must not be silently promoted to universal 2026 design criteria.

Examples that must remain **source-labelled study results or historical examples** include:

- reported cell-count thresholds;
- membrane fluxes;
- GMF filtration rates;
- coagulant doses;
- DAF loading rates;
- UF pore size / MWCO values;
- TEP removal percentages;
- MFI-UF values;
- cleaning frequencies;
- specific bloom case-study data;
- specific historic plant behavior;
- specific historical supplier limits.

Current project-grade decisions require, as applicable:

1. current site-specific source-water characterization;
2. seasonal and event monitoring;
3. current pilot testing;
4. current Total Pretreatment Design and Total RO Design logic;
5. current membrane/pretreatment supplier limits;
6. current owner criteria and regulatory requirements;
7. current peer-reviewed literature.

Academy should preserve the distinction between:

**mechanism** — often transferable;

and

**numerical design criterion** — often site-, membrane-, configuration- and era-specific.

---

# 2. Central Academy teaching principle

> **A bloom is not just “too many algae.” The most damaging membrane-fouling load may be the organic material produced by the algae rather than the cells themselves.**

The Villacorte work provides a strong basis for teaching that cell count alone can be a poor predictor of membrane fouling. Different species produce different quantities and types of AOM/TEP, and the release of organic material changes over the bloom life cycle.

The student should eventually be able to answer:

- What is blooming?
- What phase of the bloom are we in?
- Are cells or AOM/TEP driving the risk?
- Is the risk primarily hydraulic, organic, biological, toxicological, or several at once?
- Which measurements actually reveal that risk?
- What should the plant change now?
- What risk may remain after the visible bloom has declined?

---

# 3. Learning progression across the Academy

## Level 1 — Water Treatment Foundations & Water Quality

### 3.1 What is an algal bloom?

Teach a bloom as rapid proliferation of naturally occurring microscopic photosynthetic organisms under favorable environmental conditions.

Important drivers include:

- light;
- water temperature;
- nutrient availability;
- salinity;
- stratification and mixing;
- currents;
- upwelling;
- river inflows;
- storm-driven nutrient transport;
- species-specific life-cycle behavior;
- anthropogenic nutrient loading where relevant.

### 3.2 Natural versus anthropogenic drivers

Students should not learn the simplistic statement that pollution “causes” all blooms.

Teach:

- natural nutrient transport can generate major blooms;
- anthropogenic nutrient loads can increase frequency/severity in some locations;
- the relative importance is site-specific;
- monitoring and coastal context matter.

### 3.3 Harmful algal bloom (HAB) versus red tide

Teach explicitly:

- **not every red tide is harmful**;
- **not every harmful bloom is red**;
- **not every harmful bloom is toxic**;
- high biomass alone can be harmful through oxygen depletion, mucilage, clogging or ecological effects;
- a non-toxic bloom can still be a major desalination reliability event.

### Common Mistake

**Mistake:** “If the bloom is non-toxic, it is not a serious SWRO problem.”

**Why it is tempting:** HAB discussions often focus on toxins and public health.

**Why it fails:** High biomass and AOM can overwhelm pretreatment, create organic fouling, promote biofouling and force production reductions even when toxins are absent.

**How to catch it:** Compare cell/AOM/TEP/fouling indicators with toxin data rather than using toxin presence as the only alarm criterion.

### 3.4 Major bloom-forming groups

At beginner level, introduce the engineering-relevant differences among:

- diatoms;
- dinoflagellates;
- haptophytes;
- raphidophytes;
- cyanobacteria where brackish/saline or freshwater interfaces are relevant;
- other local bloom-forming organisms.

Do not require taxonomy memorization. Teach why the type matters:

- cell size;
- shape;
- chain/colony formation;
- motility;
- density/buoyancy;
- silica/frustule characteristics;
- toxin potential;
- AOM/TEP production;
- bloom duration;
- tendency to generate mucilage or foam.

### Interactive exercise — `Meet the Bloom`

Give four simplified organism profiles and ask students to identify which variables would matter to:

- screening;
- DAF;
- GMF;
- UF;
- RO biofouling risk;
- operator monitoring.

The correct answer must be a **risk profile**, not simply a species name.

---

# 4. Bloom life cycle as an engineering variable

The Academy should teach the bloom as a time series rather than a static sample.

## 4.1 Suggested teaching stages

Use a simplified educational sequence:

**background**
→ **initiation / growth**
→ **rapid growth**
→ **peak biomass**
→ **stationary / nutrient stress**
→ **senescence / decay**
→ **post-bloom recovery**.

This is an educational framework; real blooms may be spatially heterogeneous, multi-species and non-monotonic.

## 4.2 Why phase matters

The student should see that:

- cell count may rise before maximum organic-fouling risk;
- extracellular products can increase under growth and stress;
- damaged or dying cells can release intracellular material;
- AOM composition changes over time;
- TEP and mucilage behavior can change as the bloom develops;
- bacterial activity may increase during decay;
- biofouling risk can continue after visible cell concentrations decline.

### Common Mistake

**Mistake:** “The bloom is over when chlorophyll-a or cell count starts falling.”

**Why it fails:** Senescence and cell lysis can release IOM/AOM and nutrients while existing TEP/AOM deposits remain on pretreatment and RO surfaces.

**How to catch it:** Continue monitoring organic/fouling indicators and normalized membrane performance through the recovery period.

### Interactive exercise — `The Bloom Is Over... Or Is It?`

Show a 30-day time series with:

- chlorophyll-a;
- cell count;
- TEP;
- biopolymer concentration;
- MFI-UF;
- UF permeability;
- RO feed-channel pressure drop.

Make the cell count peak first, TEP/MFI-UF peak later, and RO pressure-drop deterioration continue into recovery.

Ask the learner to identify:

1. bloom initiation;
2. peak biomass;
3. highest pretreatment risk;
4. highest delayed RO biofouling risk;
5. appropriate time to exit bloom-response mode.

---

# 5. Algal organic matter (AOM)

## 5.1 AOM is not one compound

Teach AOM as a heterogeneous mixture including:

- polysaccharides;
- proteins;
- high-molecular-weight biopolymers;
- humic-like/refractory fractions;
- lower-molecular-weight biogenic compounds;
- TEP and TEP precursors;
- cell-associated and dissolved material.

## 5.2 EOM versus IOM

Teach the distinction:

### Extracellular organic matter (EOM)

Material actively exuded/released by living or stressed algal cells.

Engineering significance:

- can be highly polymeric;
- can be sticky;
- can form/precursor TEP;
- can alter particle aggregation;
- can contribute to membrane fouling before obvious cell decay.

### Intracellular organic matter (IOM)

Material released from compromised, lysed, dying or decaying cells.

Engineering significance:

- becomes increasingly important during senescence/death;
- can increase dissolved organic load;
- may include low-molecular-weight compounds;
- may include taste/odor or toxin-related compounds for some species;
- can change biological growth potential downstream.

### Common Mistake

**Mistake:** “Removing intact algal cells removes the bloom problem.”

**Why it fails:** Dissolved and colloidal AOM can pass cell-removal barriers and continue to foul UF/RO or support downstream biofilm growth.

---

# 6. Transparent exopolymer particles (TEP)

## 6.1 What TEP are

Teach TEP as highly hydrated, gel-like, sticky exopolymeric material associated with algal/bacterial organic matter.

The learner should understand that TEP:

- are not ordinary rigid suspended solids;
- can exist over a wide size spectrum;
- can form from smaller colloidal/polymeric precursors;
- can retain large quantities of water;
- can deform and fill voids in deposited cakes;
- can attach to membranes and spacers;
- can aggregate particles and cells;
- can become colonization/conditioning sites for bacteria;
- may themselves be biodegradable or concentrate nutrients.

## 6.2 Why visual intuition fails

A feed can look visually acceptable while carrying a major TEP/biopolymer burden.

### Common Mistake

**Mistake:** “TEP is just another suspended-solid concentration.”

**Why it fails:** Gel structure, hydration, deformability, stickiness, size distribution and biological interactions matter as much as dry mass.

## 6.3 TEP as the bridge between organic and biological fouling

Teach a conceptual sequence:

**AOM/TEP deposition**
→ **conditioning layer**
→ **enhanced bacterial attachment**
→ **nutrient concentration / use**
→ **biofilm development**
→ **feed-channel pressure-drop increase / flux or NDP penalties**.

This should become one of the Academy’s central SWRO biofouling diagrams.

### Original Academy visualization — `From Invisible Gel to Biofilm`

Animate:

1. clean spacer/membrane;
2. colloidal biopolymer/TEP arrival;
3. sticky gel deposition;
4. bacterial attachment;
5. EPS/TEP growth;
6. streamer formation around spacer intersections;
7. increased hydraulic resistance.

Do not reproduce the dissertation figures. Build an original TWDA visual from the governing concepts.

---

# 7. Cell concentration is not fouling potential

The source provides unusually strong pedagogy for this distinction.

Students should learn that:

- cell count is useful for bloom magnitude;
- chlorophyll-a is useful for biomass indication;
- neither alone fully predicts membrane-fouling potential;
- species differ in AOM/TEP production;
- bloom phase matters;
- TEP and MFI-UF can correlate more strongly with UF fouling than cell count in the cited research.

### Common Mistake

**Mistake:** “The highest cell count is the worst membrane-fouling day.”

**Why it fails:** A lower-cell-count period can have higher TEP/AOM and therefore higher non-backwashable fouling potential.

### Interactive exercise — `Cell Count vs Fouling Detective`

Provide three samples:

| Sample | Cells | Chlorophyll-a | TEP | MFI-UF | Biopolymers |
|---|---:|---:|---:|---:|---:|
| A | high | high | moderate | moderate | moderate |
| B | moderate | moderate | very high | very high | high |
| C | low | low | low | low | low |

Ask:

- Which is the most severe bloom by biomass?
- Which is the most severe UF fouling risk?
- Which would trigger the strongest pretreatment response?
- What additional data are needed?

---

# 8. Solution chemistry and AOM fouling

This material provides a valuable link to Level 2 solution chemistry and Level 4 membrane science.

Students should understand that algal biopolymer fouling can be influenced by:

- pH;
- ionic strength;
- cation composition;
- divalent ions such as Ca2+;
- polymer charge / functional groups;
- membrane surface chemistry;
- existing foulant layer.

The Academy should explain **cation bridging** conceptually as a possible mechanism by which divalent ions can alter interactions among negatively charged organic polymers/surfaces.

### Common Mistake

**Mistake:** “Organic fouling is independent of seawater chemistry because the foulant is organic.”

**Why it fails:** Electrostatic interactions, ion bridging, polymer conformation and membrane/foulant interactions all depend on solution chemistry.

### Research-method lesson — `Alginate Is Not Algae`

The dissertation found that model polysaccharides such as sodium alginate and xanthan gum did not reliably reproduce the fouling behavior of real algal biopolymers under the studied seawater conditions.

Teach students:

- why model foulants are useful;
- what simplifications they introduce;
- why validation with real source-water/AOM is important;
- why pilot studies must disclose what surrogate was used.

Never teach the dissertation result as “alginate is useless.” Teach it as **model fidelity matters**.

---

# 9. UF particulate fouling versus capillary plugging

Students should distinguish two different failure modes.

## 9.1 Surface/cake fouling

Mechanism:

- cells, detritus and AOM deposit on membrane surface;
- TEP/biopolymers fill cake voids;
- resistance rises;
- cake can become compressible;
- backwash recovery deteriorates.

## 9.2 Axial/capillary plugging

Mechanism:

- larger cells/debris are transported along the inside-out capillary;
- deposition at a dead-end or constricted portion reduces active flow area;
- local flux increases through the remaining active area under constant production;
- TMP/cake resistance can accelerate;
- backwash may not reach or remove the plug effectively.

### Operator levers to teach

- shorten filtration-cycle duration;
- lower flux;
- use forward flush where appropriate;
- use a small cross-flow/bleed where the module design supports it;
- improve upstream cell removal;
- adjust bloom-response mode.

Historical source values associated with these levers remain examples, not universal settings.

### Interactive exercise — `Where Did My UF Area Go?`

Show a 100-capillary educational module.

Let students progressively plug 0%, 5%, 10%, 20% of capillaries while holding total permeate production constant.

Visualize:

- remaining active area;
- local flux;
- TMP tendency;
- fouling acceleration;
- effect of derating total plant production.

The goal is to teach **why capacity derating can protect reliability**.

---

# 10. Pretreatment technology response during blooms

This source complements, but does not replace, the detailed pretreatment map.

## 10.1 Granular media filtration (GMF/DMF)

Teach:

- GMF normally relies on depth filtration;
- high bloom solids/coagulated-floc load can drive rapid headloss;
- excessive surface accumulation can shift behavior toward surface/cake blocking;
- shorter runs increase backwash demand and reduce available capacity;
- increasing coagulant simply to improve effluent quality can worsen filter loading;
- capacity and water-quality objectives must be balanced.

### Common Mistake

**Mistake:** “If SDI is getting worse, add more coagulant.”

**Why it fails:** More coagulated solids may improve capture but can accelerate media-filter clogging and reduce plant capacity.

## 10.2 Dissolved air flotation (DAF)

Teach DAF as particularly suited to removal of low-density algal/floc particles because microbubbles attach to flocs and drive them upward rather than relying solely on gravity settling.

Students should evaluate:

- coagulation effectiveness;
- floc characteristics;
- bubble/floc interaction;
- hydraulic loading;
- recycle/saturation system;
- sludge removal;
- downstream GMF/UF protection;
- chemical/sludge burden.

Do not teach a single removal percentage or loading rate as universally valid.

## 10.3 Ultrafiltration (UF)

Teach both strengths and vulnerabilities:

### Strengths

- robust particulate barrier;
- generally stable permeate quality for particulate indicators;
- smaller footprint than many conventional trains;
- frequent automatic backwashing;
- ability to operate with inline coagulation;
- strong role as SWRO pretreatment.

### Vulnerabilities

- AOM/TEP can cause strong, non-backwashable fouling;
- capillaries can plug under severe cell/debris loading;
- flux selection affects robustness;
- coagulation may still be needed during challenging blooms;
- CEB/CIP burden can become unacceptable if the source changes beyond design expectations.

### Common Mistake

**Mistake:** “UF eliminates algal-bloom risk.”

**Correction:** UF changes where and how the risk appears. It can protect RO very effectively while becoming the primary hydraulic/fouling bottleneck itself.

---

# 11. Inline coagulation during a bloom

Cross-link to the Tabatabai source map for detailed coagulation pedagogy.

For the algae-bloom lesson, emphasize the operating question:

> **What are we trying to change about the foulant/cake so the UF can keep operating?**

The student should evaluate:

- coagulation dose;
- pH;
- mixing;
- metal speciation/residual risk;
- effect on cake permeability;
- effect on AOM/biopolymer removal;
- effect on backwashability;
- CEB frequency;
- sludge/backwash residuals.

Avoid the conventional-treatment assumption that the objective is always to create the largest possible settleable floc.

---

# 12. Organic fouling versus biofouling

## 12.1 Organic fouling

AOM/TEP can directly deposit on UF and RO surfaces/spacers.

Consequences can include:

- permeability reduction;
- increased hydraulic resistance;
- increased pressure drop;
- non-backwashable UF fouling;
- enhanced particulate deposition;
- creation of a sticky conditioning layer.

## 12.2 Biofouling

Teach biofouling as a biological growth process requiring viable organisms and suitable nutrients/environment, not merely the presence of organic material.

AOM/TEP can:

- improve bacterial attachment;
- provide or concentrate biodegradable substrate/nutrients;
- create surface conditions favorable for biofilm development.

The cited dissertation experiments showed that AOM pre-fouling can accelerate subsequent biofilm development under nutrient-available conditions.

### Common Mistake

**Mistake:** “Organic fouling and biofouling are the same thing.”

**Correction:** Organic deposition can occur without biological growth, but the deposited layer can strongly influence subsequent biological colonization.

---

# 13. Delayed post-bloom biofouling

This should be a signature advanced Academy lesson.

Teach the temporal sequence:

1. bloom cell concentration rises;
2. AOM/TEP production/deposition increases;
3. pretreatment/UF experiences hydraulic stress;
4. cells decline;
5. senescence/lysis changes dissolved organic and nutrient composition;
6. retained AOM/TEP remains on surfaces;
7. bacterial growth can accelerate if nutrients become available;
8. RO feed-channel DP may deteriorate after the visible bloom appears to be ending.

### Common Mistake

**Mistake:** “Once the water clears, the plant can immediately return to normal operating mode.”

**Why it fails:** Organic conditioning layers and post-bloom nutrients may create a delayed biological response.

### Interactive mission — `The 10-Day Surprise`

Student sees:

- declining chlorophyll-a;
- normal-looking turbidity;
- acceptable SDI;
- elevated TEP/biopolymers;
- slowly increasing RO feed-channel DP.

They must decide whether to:

- exit bloom mode;
- maintain enhanced monitoring;
- inspect pretreatment residuals;
- normalize RO performance;
- investigate biological growth potential;
- schedule cleaning prematurely.

The correct outcome should emphasize **evidence-based diagnosis**, not automatic CIP.

---

# 14. Monitoring architecture

The Academy should explicitly teach that no single parameter describes bloom risk.

## 14.1 Tier 1 — environmental / bloom presence

Potential indicators include:

- cell count;
- chlorophyll-a;
- microscopy/species identification where available;
- remote/satellite or external HAB advisories where locally available;
- temperature;
- salinity;
- turbidity;
- dissolved oxygen;
- nutrient trends.

## 14.2 Tier 2 — organic / fouling potential

Teach the roles and limitations of:

- TEP;
- biopolymer concentration / LC-OCD;
- TOC/DOC;
- MFI / MFI-UF;
- SDI;
- UV/fluorescence or other organic proxies where appropriate;
- source-specific surrogate relationships.

## 14.3 Tier 3 — biological growth potential

Introduce advanced indicators such as:

- ATP;
- AOC;
- BDOC;
- bacterial count/activity;
- membrane fouling simulator / biofilm monitoring concepts;
- nutrient availability.

The course must teach that historical research uses different methods and that no globally universal alarm threshold should be inferred from the dissertation.

## 14.4 Tier 4 — plant response indicators

Monitor actual unit behavior:

### DAF / clarification

- float/sludge loading;
- effluent turbidity;
- chemical dose;
- recycle/saturation performance;
- downstream load.

### GMF

- headloss;
- filter run time;
- backwash frequency;
- effluent turbidity;
- SDI/MFI where measured.

### UF

- normalized permeability;
- TMP;
- filtration-cycle duration;
- backwash recovery;
- CEB frequency;
- integrity;
- feed/permeate organic indicators.

### RO

- normalized permeate flow;
- normalized salt passage;
- normalized feed pressure / NDP;
- feed-channel pressure drop;
- stage behavior;
- cleaning frequency;
- differential trends rather than only instantaneous values.

---

# 15. Bloom Early-Warning Dashboard

Create an original interactive dashboard with five panels:

## Panel A — Source condition

- chlorophyll-a;
- algae cell count;
- species / bloom group;
- water temperature;
- turbidity;
- external HAB alert.

## Panel B — Organic-fouling risk

- TEP;
- biopolymers;
- MFI-UF;
- TOC/DOC;
- trend arrows.

## Panel C — Pretreatment performance

- DAF/clarifier removal;
- GMF run length/headloss;
- UF TMP/permeability;
- backwash/CEB frequency.

## Panel D — RO protection

- RO feed SDI/MFI;
- normalized RO pressure drop;
- normalized permeate performance;
- biofouling warning trend.

## Panel E — Operating state

- NORMAL;
- WATCH;
- BLOOM RESPONSE;
- SEVERE BLOOM;
- RECOVERY;
- POST-BLOOM SURVEILLANCE.

Students must learn that changing operating state requires **multiple lines of evidence**, not one sensor.

---

# 16. Bloom Response State Machine

The existing pretreatment map uses a simplified bloom state machine. This dedicated source map expands it.

## NORMAL

Objectives:

- establish seasonal baseline;
- maintain normal pretreatment setpoints;
- confirm monitoring instruments are healthy;
- preserve spare capacity.

## WATCH

Possible triggers:

- external HAB notification;
- rising chlorophyll-a/cell count;
- rising TEP/MFI-UF;
- seasonal precursor trend;
- intake water visual change;
- declining UF permeability.

Actions to teach:

- increase sampling frequency;
- confirm species/organic indicators;
- verify chemical systems and spares;
- prepare derating/alternate treatment modes;
- verify sludge/backwash capacity.

## BLOOM RESPONSE

Potential actions, subject to validated process limits:

- activate DAF or enhanced primary treatment where available;
- optimize coagulation;
- reduce GMF loading;
- reduce UF flux;
- shorten UF filtration cycle;
- adjust forward flush/backwash/CEB strategy;
- tighten RO feed monitoring;
- preserve spare treatment capacity.

## SEVERE BLOOM

Teach decision-making around:

- deliberate plant derating;
- use of standby pretreatment capacity;
- controlled train shutdown;
- avoiding irreversible RO exposure;
- residuals/sludge capacity;
- water-supply obligation versus equipment protection.

## RECOVERY

Do not return to normal solely because algae counts fall.

Check:

- TEP/biopolymer decline;
- MFI-UF trend;
- UF permeability recovery;
- backwash/CEB requirements;
- RO normalized DP;
- biological growth indicators where available.

## POST-BLOOM SURVEILLANCE

Maintain enhanced observation for delayed organic/biological impacts.

### Advanced exercise — `When Can We Return to Normal?`

Students defend an operating-state transition using trend evidence.

---

# 17. Subsurface intake as bloom-resilience strategy

Cross-reference the Missimer intake work and the Academy marine-intake source map.

Teach that a suitable subsurface intake can act as part of pretreatment through natural filtration/biological processes and may strongly reduce:

- algae;
- suspended matter;
- bacteria;
- biopolymers/polysaccharides;
- organic-fouling potential.

But do not teach subsurface intake as universally feasible.

Feasibility depends on:

- geology/hydrogeology;
- aquifer productivity;
- beach/seabed conditions;
- capacity;
- water quality / redox chemistry;
- construction access;
- maintenance;
- environmental constraints;
- lifecycle economics.

### Common Mistake

**Mistake:** “A bloom-prone coast should always use beach wells.”

**Correction:** Subsurface intake may be an excellent resilience strategy where feasible, but feasibility and capacity are site-specific and require early hydrogeologic investigation.

### Integrated design exercise — `Avoid the Bloom or Treat the Bloom?`

Compare two conceptual sites:

**Site A** — favorable permeable coastal geology, high seasonal bloom risk.

**Site B** — low-permeability rocky coast, lower bloom frequency but extreme episodic events.

Ask students to compare:

- intake strategy;
- pretreatment complexity;
- OPEX;
- operational resilience;
- residuals;
- project-development risk.

---

# 18. Toxins: distinguish public-health removal from operational fouling

Academy should introduce toxin risk but avoid turning this module into a toxicology course.

Teach:

- some HAB species produce toxins;
- not every bloom produces toxins;
- toxin concentration and cell count are not equivalent to fouling potential;
- NF/RO rejection of a toxin does not eliminate the need for robust pretreatment;
- pretreatment protects plant operability while membrane barriers protect product water according to validated treatment performance;
- damaged cells may release intracellular material, so pre-oxidation/cell-lysis decisions require careful source-specific engineering.

### Common Mistake

**Mistake:** “RO rejects the toxin, so the bloom does not matter.”

**Why it fails:** The plant still has to remain hydraulically operable and protect membranes/spacers from cells, detritus, AOM and biofouling.

---

# 19. Chemical pretreatment and cell integrity

At advanced level, discuss qualitatively that chemical actions capable of damaging cells can change the balance between:

- intact-cell removal;
- EOM/IOM release;
- dissolved/colloidal organic burden;
- downstream treatment requirements.

Do not create a universal pre-oxidation rule from this source.

Any lesson on oxidants must defer to:

- current membrane compatibility;
- current DBP/toxin guidance;
- source-specific testing;
- validated specialist-application logic.

---

# 20. Residuals and environmental burden during bloom response

Bloom resilience affects the whole plant.

Teach that intensified pretreatment may increase:

- DAF float sludge;
- coagulant-rich solids;
- GMF backwash volume;
- UF backwash volume;
- CEB waste;
- CIP waste;
- chemical storage/consumption;
- sludge thickening/dewatering load;
- disposal/discharge burden;
- auxiliary energy.

### Common Mistake

**Mistake:** “A robust bloom design is just adding an extra barrier.”

**Correction:** Every additional barrier has hydraulic, chemical, residuals, control, footprint, redundancy and lifecycle-cost consequences.

---

# 21. Electrical, controls and automation link

Level 7 should use algal-bloom response as a realistic controls case.

## 21.1 Instruments / signals

Possible educational signals:

- intake turbidity;
- chlorophyll-a;
- differential pressure across screens;
- DAF recycle/pressure;
- GMF headloss;
- UF TMP;
- UF permeability;
- backwash status;
- chemical tank levels;
- RO feed SDI/MFI laboratory results;
- RO feed-channel DP;
- flow and production rate.

## 21.2 PLC / HMI teaching

Have the learner design:

- bloom-watch permissive;
- low-chemical inventory alarm;
- UF high-TMP alarm;
- escalating backwash/CEB logic;
- maximum safe flux override;
- operator-confirmed derating;
- severe-bloom train shutdown permissive/interlock;
- recovery-state timer/criteria;
- event historian tags.

### Guided Engineering Solution Mode example

**Scenario:** Chlorophyll rises sharply, UF TMP trend accelerates, but RO feed SDI remains acceptable.

Step-by-step prompts:

1. What process is currently protecting RO?
2. Does acceptable SDI prove the organic risk is low?
3. What additional indicators do you request?
4. Which UF operating variables can be adjusted?
5. What residual/chemical consequences follow?
6. What condition would justify deliberate plant derating?

---

# 22. Reliability and design philosophy

A bloom-resistant plant should be designed around **variability**, not only average seawater.

Students should evaluate:

- normal versus bloom design basis;
- seasonal envelope;
- worst credible episodic event;
- online versus laboratory monitoring;
- pretreatment redundancy;
- hydraulic turndown;
- ability to derate safely;
- chemical-system capacity;
- backwash/CEB/CIP capacity;
- sludge handling capacity;
- spare parts / membrane modules;
- operator staffing during bloom events;
- alternate intake/pretreatment modes;
- emergency water-supply obligations.

### Common Mistake

**Mistake:** “Design for the average annual water quality and add a safety factor.”

**Why it fails:** Rare episodic events can determine pretreatment reliability and plant availability even if their contribution to annual averages is small.

---

# 23. Pilot-testing philosophy for bloom-prone SWRO

Academy should teach students to ask whether the pilot program actually reproduced the risk that matters.

A useful pilot program should consider:

- seasonal coverage;
- bloom-season operation if possible;
- actual local species/AOM;
- source-water chemistry;
- intake configuration;
- pretreatment train variants;
- normal and bloom flux;
- coagulation range;
- backwash/CEB recovery;
- TEP/biopolymer/MFI-UF trends;
- residuals production;
- RO downstream performance where appropriate.

### Common Mistake

**Mistake:** “The pilot ran for three months without trouble, so the design is validated.”

**Correction:** Three non-bloom months may not challenge the process against the design event.

---

# 24. Misconception library

The following cards should be reusable throughout the Academy.

1. **Red tide = harmful algal bloom.**
   - Wrong because color and harm are different concepts.

2. **Non-toxic bloom = no desalination risk.**
   - Wrong because biomass/AOM can cause severe operational fouling.

3. **Cell count = membrane fouling potential.**
   - Wrong because AOM/TEP and species/lifecycle can dominate.

4. **If cells are removed, RO is safe.**
   - Wrong because colloidal/dissolved AOM can pass cell-removal barriers.

5. **Low SDI = low biofouling risk.**
   - Wrong because SDI does not directly measure all organic/biological drivers.

6. **UF eliminates bloom risk.**
   - Wrong because UF itself can become the fouling/plugging bottleneck.

7. **More ferric = more protection.**
   - Wrong because filter loading, residual metals, membrane fouling and sludge also rise/change.

8. **The tightest membrane is always best.**
   - Wrong because permeability, surface porosity, backwashability and energy/area tradeoffs matter.

9. **Alginate is a complete surrogate for AOM.**
   - Wrong because model-polymer behavior may differ significantly from real algal biopolymers.

10. **The bloom ends when cells fall.**
    - Wrong because AOM/IOM/nutrients and surface conditioning can persist.

11. **Organic fouling = biofouling.**
    - Wrong because biological growth is a separate process, though organic deposits can accelerate it.

12. **RO toxin rejection makes pretreatment irrelevant.**
    - Wrong because plant operability and membrane protection remain critical.

13. **A subsurface intake is always the best bloom solution.**
    - Wrong because hydrogeologic and capacity feasibility is site-specific.

14. **A bloom response should maximize plant production.**
    - Wrong because deliberate derating may preserve long-term availability and prevent irreversible damage.

---

# 25. Interactive exercise library

## 25.1 `Bloom Lifecycle Simulator`

Change:

- temperature;
- light;
- nutrient availability;
- growth phase;
- species profile.

Observe simplified trends in:

- cell concentration;
- EOM;
- IOM;
- TEP;
- membrane-fouling risk.

The simulator is conceptual unless backed by a validated ecological model. It must not claim to predict real bloom growth.

## 25.2 `Species Is Not Just a Name`

Learner compares cell size, morphology, toxin potential, AOM/TEP behavior and treatment implications.

## 25.3 `Cell Count vs Fouling Detective`

Learner chooses the most useful fouling indicators among cell count, chlorophyll, TEP, biopolymer concentration and MFI-UF.

## 25.4 `EOM or IOM?`

Classify organic-release scenarios during growth, stress and cell lysis.

## 25.5 `TEP Hydrogel Explorer`

Visualize hydrated gel occupying pore/cake void space and forming a sticky conditioning layer.

## 25.6 `Calcium Bridge`

Conceptual visualization of how divalent cations can alter interactions of negatively charged algal polymers.

## 25.7 `Alginate Is Not Algae`

Compare model foulant versus real AOM experimental reasoning and ask what can/cannot be generalized.

## 25.8 `Where Did My UF Area Go?`

Capillary plugging reduces effective membrane area; learner chooses derating, cycle time and flushing responses.

## 25.9 `GMF Depth or Surface Blocking?`

Learner recognizes the transition from normal depth filtration to surface/cake loading during high algae/coagulant conditions.

## 25.10 `DAF Protects the Downstream Train`

Balance algae removal, coagulant dose, sludge, footprint and downstream GMF/UF loading.

## 25.11 `UF Is the Shield — Until It Isn't`

Track UF permeability, TMP, backwash recovery and CEB frequency during a simulated bloom.

## 25.12 `Bloom Early-Warning Dashboard`

Learner interprets multiple source and plant-response indicators.

## 25.13 `Build the Bloom PLC State Machine`

Design NORMAL/WATCH/BLOOM/SEVERE/RECOVERY/POST-BLOOM transitions.

## 25.14 `The 10-Day Surprise`

Diagnose delayed RO biofouling after visible bloom decline.

## 25.15 `Avoid the Bloom or Treat the Bloom?`

Compare open-intake robust pretreatment versus feasible subsurface intake.

## 25.16 `Residuals During the Worst Week`

Calculate/compare conceptual backwash, sludge and chemical burden during normal and bloom modes.

## 25.17 `Pilot Test the Right Season`

Choose a pilot schedule and monitoring plan that actually challenges the proposed design.

## 25.18 `Full SWRO Bloom Resilience Defense`

Student presents a complete design and operating philosophy for a bloom-prone SWRO site.

---

# 26. Guided Engineering Solution Mode — full example

## Scenario

An SWRO facility with open-ocean intake normally operates with coagulation + DAF + UF + cartridge filters + RO.

During a seasonal event:

- chlorophyll-a rises rapidly;
- cell count increases;
- DAF float loading increases;
- UF TMP rises faster than normal;
- backwash recovery deteriorates;
- RO feed SDI remains below the normal contractual limit;
- TEP/MFI-UF increase;
- RO feed-channel DP is currently stable.

## Step 1 — Define the actual problem

The problem is not “SDI is okay.”

The engineering question is:

> Can the pretreatment maintain sufficient hydraulic capacity and protect the RO from particulate, organic and biological fouling throughout the event and recovery period?

### Common Mistake

Using a single RO-feed SDI value as proof of complete protection.

## Step 2 — Identify the likely bottleneck

UF is currently absorbing much of the event load, as indicated by accelerating TMP and deteriorating recovery.

## Step 3 — Separate cell and AOM risk

Request/trend:

- cell count/chlorophyll;
- TEP;
- MFI-UF;
- biopolymer/organic indicators where available.

## Step 4 — Check pretreatment loading

Review:

- DAF removal;
- coagulant performance;
- float/sludge capacity;
- UF feed load;
- UF flux/cycle time;
- CEB frequency.

## Step 5 — Use operating levers

Within validated process limits, consider:

- coagulation optimization;
- increased DAF protection;
- lower UF flux;
- shorter filtration cycle;
- forward flush / bleed where equipment permits;
- planned plant derating.

## Step 6 — Protect downstream RO

Trend normalized:

- feed pressure/NDP;
- feed-channel DP;
- permeate flow;
- salt passage.

Do not wait for severe RO performance deterioration before acting if upstream evidence shows increasing risk.

## Step 7 — Plan recovery

Do not exit bloom mode based only on lower cell count.

Confirm recovery of:

- TEP/MFI-UF;
- UF permeability/backwashability;
- residuals load;
- RO normalized DP;
- biological indicators where available.

## Step 8 — Learn from the event

Update:

- seasonal design basis;
- bloom-response triggers;
- chemical inventory;
- redundancy philosophy;
- pilot/test assumptions;
- capital improvement priorities.

---

# 27. Level mapping summary

## Level 1

- what blooms are;
- HAB versus red tide;
- major algae groups;
- cells versus organic products;
- why desalination plants care.

## Level 2

- colloids/hydrogels;
- cake/gel resistance;
- compressibility;
- shear and particle transport;
- pH/ionic-strength/cation effects;
- cation bridging;
- model-foulant limitations.

## Level 3

- DAF/GMF/UF response;
- cell removal versus AOM removal;
- coagulation;
- filtration-cycle strategy;
- UF plugging/backwashability;
- bloom-resilient pretreatment train selection.

## Level 4

- RO spacer/organic fouling;
- TEP conditioning layer;
- organic versus biological fouling;
- delayed biofouling;
- normalized RO performance diagnosis.

## Level 6

- headloss and hydraulic capacity during bloom;
- pump/flow derating consequences;
- backwash and auxiliary hydraulic loads.

## Level 7

- online monitoring;
- alarm philosophy;
- bloom state machine;
- PLC/HMI response;
- operator decision support;
- historian/event analysis.

## Level 8

- sludge/backwash/CEB/CIP residuals;
- disposal consequences;
- chemical and water-recovery tradeoffs.

## Level 9

- reliability and availability;
- lifecycle cost;
- intake strategy;
- pilot testing;
- redundancy;
- project risk and owner criteria.

## Level 10

- full intake + pretreatment + RO + residuals + controls bloom-resilience defense.

---

# 28. Level 10 capstone requirement — Bloom Resilience Annex

For a coastal SWRO capstone in a bloom-prone location, require a short **Bloom Resilience Annex** containing:

1. bloom/source-water risk statement;
2. relevant species/groups and seasonality;
3. normal and severe-event water-quality envelope;
4. AOM/TEP risk statement;
5. intake strategy;
6. pretreatment train and why each barrier is present;
7. normal/bloom operating flux philosophy;
8. coagulation philosophy;
9. DAF/GMF/UF loading strategy;
10. monitoring plan;
11. alarm/state-transition philosophy;
12. intentional derating philosophy;
13. residuals/sludge capacity check;
14. RO protection/normalized-performance plan;
15. post-bloom surveillance strategy;
16. pilot-testing/data gaps;
17. reliability/availability implications;
18. key assumptions and limitations.

The student must defend the strategy verbally or in a written design review.

---

# 29. Engineering ownership boundary

Academy owns:

- explanation;
- pedagogy;
- original educational visualizations;
- diagnostic cases;
- bloom-response scenarios;
- learner exercises;
- misconception callouts;
- progress/competency assessment.

Academy does **not** own project-grade engineering models for:

- pretreatment sizing;
- RO membrane projection;
- chemistry/speciation;
- hydraulic design;
- ecological bloom prediction;
- HAB forecasting;
- toxin fate/compliance;
- coastal/intake environmental impact.

Where validated owner adapters exist, Academy should call them.

Relevant owners include:

- `app/total-pretreatment-design`;
- `app/total-ro-design`;
- `engine/shared-water-chemistry`;
- `app/total-water-balance`;
- future validated marine/intake/environmental owners where created.

The Academy must not create an independent production **HAB prediction engine** or an independent SWRO pretreatment solver simply to support teaching.

---

# 30. Source provenance and learner citations

Whenever a learner-facing lesson materially uses concepts or experimental findings from the Villacorte dissertation, include it in:

**Research Basis / Sources & Further Reading**

Suggested reference:

> Villacorte, L. O. (2014). *Algal Blooms and Membrane Based Desalination Technology*. Delft University of Technology / UNESCO-IHE Institute for Water Education; CRC Press/Balkema.

Where a specific statement relies on another paper cited inside the dissertation, Academy authors should prefer the primary paper when practical, especially for advanced lessons.

Do not label this single 2014 dissertation as the complete “2026 state of the art.”

For current-state lessons, supplement it with newer peer-reviewed literature and current practice.

---

# 31. Copyright and visual-content rule

The supplied dissertation is copyrighted.

Academy must not reproduce:

- publisher pages;
- figures;
- microscopy panels;
- tables;
- long passages;
- diagrams;
- page layouts.

Instead, build original TWDA graphics that teach the same engineering concepts.

Examples:

- original bloom lifecycle plot;
- original TEP hydrogel animation;
- original UF capillary-plugging diagram;
- original organic-to-biofilm pathway animation;
- original monitoring dashboard;
- original DAF/GMF/UF decision flow;
- original bloom-response state machine.

Source attribution must remain attached to the underlying lesson.

---

# 32. Relationship to existing Academy sources

## Villacorte 2014 — primary role

**Why the bloom behaves the way it does** and how AOM/TEP connects ecology to membrane fouling and biofouling.

## Tabatabai 2014 — companion role

**How coagulation and UF pretreatment behave** hydraulically and chemically under challenging AOM/bloom conditions.

## Missimer et al. 2013 — companion role

**How source/intake selection can avoid or reduce the bloom load** before it reaches in-plant pretreatment.

## Total RO / Pretreatment validated owners

**How real project calculations are performed.**

This separation prevents duplicated content while giving students a coherent chain:

**marine event → intake → pretreatment → membrane fouling → operation → recovery → lifecycle reliability**.

---

# 33. Completion criteria for future lesson authoring

This source is considered fully converted into learner-facing Academy content only when the authored modules include, at minimum:

- beginner bloom/HAB concepts;
- bloom lifecycle and EOM/IOM;
- AOM/TEP mechanism;
- species-versus-risk reasoning;
- TEP versus cell-count misconception;
- UF fouling and capillary plugging;
- solution-chemistry effect on AOM;
- organic-to-biofouling transition;
- post-bloom delayed risk;
- multi-indicator monitoring;
- bloom-response state machine;
- DAF/GMF/UF response tradeoffs;
- subsurface-intake cross-link;
- controls/PLC exercise;
- residuals consequence;
- full capstone resilience defense;
- source citations;
- historical-value caveats;
- original graphics.

Until those learner-facing modules are authored, this document is the authoritative Academy **content/source architecture**, not proof that every lesson screen is already implemented.
