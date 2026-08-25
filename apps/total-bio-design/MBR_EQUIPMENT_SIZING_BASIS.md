# Total Bio Design — MBR Equipment Sizing Basis

## Scope

This layer converts a solved Total Bio Design project into planning duties for membrane trains and selected MBR ancillary equipment. It is deliberately downstream of the validated biological workbook/process-network engine and does not modify the protected biological equations or unit-operation removal models.

## Primary reference

Simon Judd, *The MBR Book: Principles and Applications of Membrane Bioreactors in Water and Wastewater Treatment*, Elsevier, 1st edition, 2006.

Relevant source sections include:

- Sections 2.1.4 and 2.3.7–2.3.9: flux, permeability, aeration, fouling and cleaning;
- Section 2.2.5: oxygen transfer and process-water correction;
- Chapter 3: liquid pumping, membrane maintenance, aeration and design calculation;
- Appendix A: blower power consumption;
- Appendix B: MBR biotreatment parameter ranges;
- Appendix C: hollow-fibre module geometry;
- Appendix D: historical membrane product/module data.

## Source-control rule

The book is a 2006 reference. Numerical membrane-product data, supplier-specific flux, SADm/SADp, chemical compatibility, TMP, cleaning protocols and module geometry are therefore treated as **historical planning/reference information**, not current vendor guarantees. Final design release requires current manufacturer data.

## Implemented sizing relationships

### 1. Gross-to-net membrane flux

Net flux accounts for productive filtration time, relaxation, backwash permeate consumption and chemical-cleaning downtime. This follows the Chapter 3 design framework in which physical-cleaning interval/duration, chemical-cleaning interval/duration and backwash flux are explicit design parameters and net flux is the appropriate plant-capacity basis.

Historical planning defaults are intentionally editable:

- gross flux: 25 LMH;
- filtration: 10 min;
- relaxation: 1 min;
- HF backwash: 0.5 min at 2 × operating flux;
- maintenance clean: 60 min every 7 days;
- recovery clean: 4 h twice per year.

The book reports typical relaxation of 1–2 min every 8–15 min and HF backwash commonly around 2–3 times operating flux. These values are not supplier guarantees.

### 2. Membrane area and train availability

Required membrane area is calculated independently for average and peak hydraulic conditions from net flux. The controlling area is then increased when the selected N+1 train philosophy requires peak flow to be handled with one train unavailable. Area is rounded to whole modules and whole racks per train.

The output explicitly reports the one-train-offline peak flux and whether it remains within the configured peak net-flux capability.

### 3. Fine-screen constraint

Historical planning ranges from Judd are used as warnings only:

- HF: 0.8–1.5 mm;
- FS: 2–3 mm.

Total Bio Design does not replace Total Pretreatment Design. The MBR layer identifies the membrane-side screening constraint so the final screen can be reconciled with the upstream pretreatment design and the current membrane supplier requirement.

### 4. Pump duties

Permeate, backwash and internal recycle pump hydraulic power use the conventional relationship between flow, total dynamic head, fluid density, gravity and pump efficiency. The internal recycle ratio is taken from the solved/current Bio project when an enabled ratio-based recycle is present.

Pump heads and efficiencies remain user/project inputs until the shared pump-performance engine is connected to this MBR equipment layer.

### 5. Biological oxygen demand and blower airflow

The planning oxygen-demand expression follows the source mass-balance structure:

- substrate oxidation;
- biomass synthesis/respiration credit using 1.42 kg O2/kg VSS;
- nitrification at 4.33 kg O2/kg N oxidized;
- denitrification credit at 2.83 kg O2/kg N reduced.

The denitrification credit defaults to zero rather than being silently inferred from total-nitrogen removal. The user may enter the solved/project denitrified-N duty when available.

Process oxygen-transfer efficiency is derived from:

- clean-water OTE per metre of diffuser submergence;
- alpha factor;
- beta factor;
- temperature correction using theta.

The selectable historical MLSS correlation uses alpha = exp(-0.083 × MLSS[g/L]), reflecting the reported decline in oxygen transfer with increasing mixed-liquor solids. A manual alpha-factor mode is also available.

### 6. Membrane-scour blower

Membrane scour airflow is calculated from installed membrane area, SADm and average aeration fraction. The default SADm of 0.47 Nm3/(h·m2) is the average value in the worked design example after cyclic aeration; it is explicitly a historical planning value and must be replaced by the current selected membrane supplier requirement.

### 7. Blower shaft power

Blower power uses adiabatic ideal-gas compression with inlet absolute pressure, inlet temperature, pressure ratio, gamma = 1.4 and blower efficiency. This follows the thermodynamic basis developed in Appendix A. The application reports shaft power and a planning motor-design duty after the selected margin.

### 8. Cleaning quantities

The equipment layer reports through-membrane cleaning-solution volume and reagent mass per event from cleaning flux, installed area, duration and reagent concentration. These values are planning quantities, not final CIP tank sizes: recirculation hold-up, tank geometry, membrane compatibility and supplier cleaning sequence must be confirmed during equipment selection.

Historical ranges retained as reference include:

- maintenance NaOCl: 200–500 mg/L every 3–7 days;
- recovery NaOCl: 0.2–0.3 wt%;
- recovery citric acid: 0.2–0.3 wt%;
- recovery oxalic acid: 0.5–1 wt%.

## Equipment outputs

The current layer produces:

- membrane area;
- installed trains;
- modules and racks per train;
- N+1/cleaning availability check;
- normal and peak net flux;
- permeate pump duty/power;
- backwash pump duty/power;
- backwash event volume;
- backwash tank working volume;
- internal recycle pump duty/power;
- biological aeration airflow and blower power;
- membrane scour airflow and blower power;
- maintenance/recovery cleaning solution and reagent quantities;
- MBR fine-screen constraint;
- warnings/review guidance for high MLSS, screen opening, high flux and low oxygen-transfer efficiency.

## Deliberate exclusions

This implementation does not:

- alter the validated Bio process-network solver;
- claim current commercial membrane product performance from 2006 data;
- select a final vendor membrane module;
- calculate a guaranteed critical/sustainable flux from first principles;
- replace current supplier CIP requirements;
- replace Total Pretreatment Design for final screen sizing;
- replace the shared pump-performance engine for final pump selection;
- perform RO/NF membrane design.

Those boundaries are intentional and should remain during reconciliation.

## UI ownership and placement

MBR equipment sizing is a child capability of the existing audited MBR unit-operation experience. It must not appear as a top-level Suite/Application workspace tab and must not replace the audited MBR page with a sparse standalone screen.

The audited MBR biological and membrane-process page remains intact. The new **MBR Equipment & Mechanical Design** section is appended to that same MBR page, preserving the original workbook-derived inputs and results while adding net-flux availability, membrane trains/racks, blowers, pumps, backwash, cleaning and pretreatment constraints.

When an individual `mbr` or `anmbr` unit is selected from the treatment train, the same augmented section remains tied to the MBR unit context. This keeps MBR as one of many biological unit operations while providing a richer specialist design experience inside that unit.