# Total RO Design — CCRO Engineering Basis

## Scope

This feature branch implements Closed Circuit Reverse Osmosis (CCRO) as a Total RO Design process-design mode. CCRO is available to Entry, Silver, Gold, and Platinum accounts that have access to Total RO Design. It is not classified as an energy-recovery-device entitlement.

The CCRO implementation reuses the existing Total RO Design element-by-element RO membrane, water chemistry, osmotic-pressure, concentration-polarization, pressure-drop, pump-efficiency, acid-dosing, and mineral-saturation primitives. Conventional RO equations are not replaced.

## Closed-circuit sequence

During the closed-circuit portion of a sequence:

- membrane concentrate is recirculated to the membrane feed;
- fresh make-up feed is introduced at approximately the permeate production rate so loop liquid inventory remains constant;
- each recirculation is recalculated with the existing membrane engine;
- feed pressure is solved independently for each recirculation to maintain the requested CC permeate flow.

For loop volume `V_loop`, CC permeate production `Qp_CC`, and CC elapsed time `t_CC`:

`Vperm_CC = Qp_CC × t_CC`

The final fractional recirculation is retained rather than forcing an integer number of cycles.

## Plug-flow portion

The plug-flow (PF) sequence is treated separately from the closed-circuit portion. PF design inputs include PF feed ratio and PF recovery. One loop/system volume is displaced as concentrated brine per completed batch:

`Vbrine_batch = V_loop`

Average batch recovery is evaluated from the complete sequence mass balance:

`Ravg = Vperm_batch / (Vperm_batch + Vbrine_batch)`

The solver does not impose a universal CCRO recovery ceiling.

## Cycle-to-cycle concentration

For Full Water Chemistry, the next membrane-feed composition is obtained by flow-weighted mixing of the preceding membrane concentrate and fresh make-up feed. Carbonate alkalinity/inorganic-carbon state is mixed using the existing Total RO Design carbonate-stream routines.

For TDS-only input, the same loop mass balance is applied on total dissolved solids, but the result is explicitly not considered sufficient to certify high-recovery scaling feasibility.

## Pressure solution

At each closed-circuit recirculation, Total RO Design solves feed pressure `P` such that:

`Qp_model(P, chemistry, membrane state) - Qp_target = 0`

A safeguarded bracket/bisection method is used because element-level concentration-polarization and salt-transport iterations can make numerical derivatives noisy near high-recovery limits.

The converged point is recalculated with detailed carbonate/species reporting.

## Pressure envelope

There is no CCRO-specific 41 bar limit.

The active pressure envelope is:

`Pmax_active = min(Pmax_membrane_recipe, Pmax_equipment)`

when an equipment/system limit is supplied. Otherwise:

`Pmax_active = Pmax_membrane_recipe`

The membrane limit is taken from the actual selected membrane recipe. Standard SWRO membranes can therefore operate to their stored ratings (commonly around 82–83 bar), while UHPRO membranes may use ratings of 120 bar or higher where present in the membrane database.

A pressure-limited CCRO case is reported when the requested permeate duty cannot be achieved below the active pressure envelope because of the evolving osmotic-pressure requirement.

## Water-chemistry / scaling limitation

Full Water Chemistry is evaluated through the CCRO sequence. The result tracks:

- initial practical RO mineral saturation;
- maximum sequence saturation;
- limiting mineral;
- first sequence recovery at which thermodynamic supersaturation occurs;
- final loop chemistry.

Thermodynamic saturation is a screening metric, not a universal hard stop. Practical allowable supersaturation depends on treatment strategy, antiscalant chemistry/dose, acidification, softening, temperature, residence time, concentration polarization, precipitation kinetics, and equipment configuration.

The software therefore reports the limiting chemistry condition instead of applying an arbitrary CCRO recovery cap.

## Energy model

Energy is integrated over the PF and closed-circuit sequence rather than calculated from one average pressure point.

For each time interval:

`E = Pwire × Δt`

The model separately accumulates:

- high-pressure pump energy;
- high-pressure recirculation-pump energy;
- pretreatment energy.

Batch RO SEC is:

`SEC_RO = E_RO,batch / Vperm_batch`

and total SEC is:

`SEC_total = SEC_RO + SEC_pretreatment`

Pump wire power uses the same Total RO Design pump/motor/VFD efficiency model used by conventional RO calculations.

## Interaction with conventional RO

CCRO is additive. It extends the existing mutable calculation registry with the `ccro` mode and calls existing membrane/chemistry primitives.

The following conventional-RO files are intentionally protected from CCRO modification:

- `calculations.py`
- `chemistry_analysis.py`
- `entitlements.py`
- `static/app.js`

CCRO-specific files and bootstrap logic must be reconciled around the latest conventional RO branch, not the reverse.

## UI hierarchy

CCRO belongs inside **Total RO Design**, which remains part of the **Total Water Design Suite**.

The CCRO interface is presented as a first-class Total RO Design process workspace associated with Plant Design. It is not a separate Suite product and is not grouped as an ERD.

Access is available to Entry, Silver, Gold, and Platinum. Engineering readiness may still require a valid Plant Design/water basis before a CCRO run is enabled.
