# Total RO Design — Batch RO Engineering Basis v0.1

## Scope

The Batch RO specialist is an additive Total RO Design calculation mode. It does not replace conventional RO or CCRO. It models fully-batch concentration in which fresh feed is charged before the productive batch and is not continuously mixed into the concentrating inventory.

Three equipment arrangements are represented:

1. **Atmospheric batch tank + isobaric PX** — low-pressure tank with pressure exchange, HPP make-up duty, high-pressure recirculation and PX/booster losses.
2. **Variable-volume high-pressure tank** — fully pressurized batch inventory without PX transfer irreversibility.
3. **Dual-compartment / moving-divider batch** — alternating isolated batch volumes; refill/purge work is counted while productive downtime is treated as overlapping production.

## Numerical model

At each recovery increment the existing Total RO Design membrane engine is solved to the active permeate target. The applied pressure is then increased as needed, bounded by the lower of the selected membrane rating and any user-entered system pressure rating. The accepted instantaneous membrane state uses the same membrane database, temperature-corrected solution-diffusion A/B transport, salt passage, concentration polarization, element-by-element pressure drop and full-ion osmotic basis as conventional Total RO Design.

The batch inventory is then advanced by the permeate increment. Species leaving in permeate are subtracted from the closed inventory. In Full Water Analysis mode, total alkalinity and total inorganic carbon are treated as extensive conserved quantities and re-equilibrated after every increment. The shared chemistry engine screens mineral saturation along the recovery path.

External liquid volume is explicit. Membrane-channel volume is estimated from membrane area, feed-channel height and porosity. Piping/dead volume and any end-of-cycle tank heel are retained in the final brine inventory. This controls the required starting tank volume and product volume per batch.

## Productivity and reset

For a specified average plant product flow, active permeate flow is solved from batch product volume and reset downtime. Consequently the active membrane flux rises when reset time is non-zero. The result reports both active flux and effective flux over the complete productive + reset cycle.

Dual-compartment mode treats switching/refill as overlapping production. It still counts low-pressure purge/refill energy.

## Energy accounting

Cycle energy includes:

- high-pressure make-up pumping;
- high-pressure recirculation pressure loss;
- PX transfer/booster loss for the atmospheric-tank configuration;
- low-pressure refill/purge work;
- pretreatment pumping as a separate SEC contribution.

The engine integrates power over the productive cycle and normalizes by actual permeate volume.

## Engineering warnings

The calculator warns on high end-of-cycle external volume, non-zero tank heel, reset fraction, active flux, pressure-envelope utilization, membrane pressure-drop limits, mineral saturation and batch salt-balance residual.

## Current model boundary

The model is a transient inventory model coupled to quasi-steady converged membrane passes. It does not claim CFD or a resolved 1-D external-pipe axial dispersion solution. PX mixing is represented as an explicit user-controlled concentration blend for the instantaneous membrane feed. Valve dynamics, moving-divider leakage, pressure-vessel fatigue and antiscalant kinetics remain equipment/process-design checks outside the solver.

## Literature / source basis supplied for this implementation

- Swaminathan et al. (2017), *Effect of Practical Losses on Optimal Design of Batch RO Systems*.
- Warsinger et al. (2016), *Energy efficiency of batch and semi-batch (CCRO) reverse osmosis desalination*.
- EP 2 234 701 B1, *Batch-operated reverse osmosis system*.
- ES 2 908 623 T3 / EP 3 525 919, moving-divider Batch RO system.
