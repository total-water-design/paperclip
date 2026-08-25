# Total Water Academy — Membrane Transport & Concentration Polarization Module v1.0

Owner: `app/total-water-academy`
Curriculum target: Level 4, especially `L04-M01` and `L04-M03`.

## Named peer-reviewed sources

1. Kim, S.; Hoek, E.M.V. (2005). “Modeling concentration polarization in reverse osmosis processes.” Desalination 186, 111–128. DOI: 10.1016/j.desal.2005.05.017.
2. Wang, J.; Dlamini, D.S.; Mishra, A.K.; Pendergast, M.T.M.; Wong, M.C.Y.; Mamba, B.B.; Freger, V.; Verliefde, A.R.D.; Hoek, E.M.V. (2014). “A critical review of transport through osmotic membranes.” Journal of Membrane Science 454, 516–537. DOI: 10.1016/j.memsci.2013.12.034.

These sources must be cited in Academy lesson provenance whenever their results, model comparisons, or scientific framing are materially used. Do not copy publisher figures, tables, or prose; build original Academy visuals and cite the source.

## L04-M01 — Membrane Transport and Separation

Teach the physical picture before the mathematics. Core learners should understand water flux, solute flux, osmotic pressure, permeability coefficients, and observed versus real/intrinsic rejection.

Use solution–diffusion as the principal first model. Introduce the common engineering form `Jw = A(DeltaP - DeltaPi)` and explain that water and solute transport respond differently to membrane properties and driving forces.

Advanced learners should compare, at a model-literacy level rather than by rote derivation:
- solution–diffusion and solution–diffusion-imperfection approaches;
- pore-flow approaches;
- Kedem–Katchalsky / Spiegler–Kedem thermodynamic descriptions;
- extended Nernst–Planck concepts for charged species;
- modern structure–performance approaches involving selective-layer thickness, porosity/free volume, effective diffusive path length, partitioning, and membrane–solute interactions.

Primary source basis: Wang et al. (2014), Sections 2–4.

## L04-M03 — Concentration Polarization, Activity, Scaling & Fouling

Teach concentration polarization as a mass-transfer balance:

bulk flow -> convection toward membrane -> preferential water permeation -> rejected-solute buildup -> diffusive back-transport -> elevated membrane-surface concentration.

Students must connect that surface enrichment to:
- higher effective transmembrane osmotic pressure;
- lower effective water-driving force;
- changes in observed salt passage/rejection;
- local saturation, scaling, and fouling risk.

Introduce the CP modulus as membrane-surface concentration divided by bulk concentration. Explain the mass-transfer coefficient as a hydrodynamic/diffusive transport quantity rather than a fudge factor.

Reconnect Level 2 unit operations by introducing Reynolds, Schmidt, and Sherwood numbers, cross-flow velocity, wall shear, and mass-transfer coefficients. Students should understand why higher effective cross-flow mass transfer tends to reduce CP, while pressure drop and energy constraints prevent unlimited cross-flow.

### Film theory versus rigorous modeling

Kim & Hoek (2005) compared classical film theory with a two-dimensional numerical convection–diffusion model and experimental RO data. Use this to teach why a simple engineering model can remain useful when its assumptions and operating range are understood.

Their approximately 16 gfd local-flux observation must be presented only as a result for the tested laboratory geometry and conditions, not as a universal TWDS design limit or membrane rule.

### External, internal, and fouling-enhanced CP

Core RO learners must master external concentration polarization (ECP). Advanced learners should also understand internal concentration polarization (ICP), especially in osmotic-membrane support layers, and fouling-enhanced ECP in NF/RO where a cake layer can hinder salt back-diffusion and increase the osmotic-pressure penalty in addition to adding hydraulic resistance.

Primary source basis: Kim & Hoek (2005), especially Sections 2 and 4–5; Wang et al. (2014), Section 5.

## Interactive Academy exercises

1. Boundary-layer explorer: vary flux, cross-flow, concentration, diffusivity, and rejection while observing bulk, surface, and permeate concentration.
2. Observed-versus-real-rejection mission: keep intrinsic rejection fixed while changing CP.
3. Model-selection mission: choose film theory versus more rigorous convection–diffusion treatment and defend the choice.
4. Fouling-enhanced CP mission: separate hydraulic cake resistance from hindered back-diffusion/osmotic effects.
5. Tail-element scaling mission: use validated Total RO Design and Shared Water Chemistry outputs to follow local risk through an RO train.

## Beginner / advanced split

Beginner: original diagrams, sliders, plain-language physical explanation.
Intermediate: `Jw`, CP modulus, mass-transfer coefficient, observed versus intrinsic rejection, Re/Sc/Sh interpretation.
Advanced: model assumptions, convection–diffusion comparison, structure–performance models, electrokinetic concepts, ECP/ICP, and cake-enhanced CP.

## Citation and scientific-age policy

Learner-facing lessons materially based on these papers should show a “Research basis” or “Sources & Further Reading” attribution. These papers are strong peer-reviewed foundations, but they should not alone be described as the final 2026 state of the art. Material explicitly labeled current state of the art requires periodic review of newer peer-reviewed literature.

## Engineering-authority boundary

Academy owns pedagogy and original educational visualizations. Authoritative project calculations remain with `app/total-ro-design`, `engine/shared-water-chemistry`, `engine/shared-waterstream`, `app/total-water-balance`, and the shared membrane data owner. Academy must use validated adapters when a learning exercise needs professional numerical outputs.
