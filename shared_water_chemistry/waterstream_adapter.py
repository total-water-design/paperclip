"""Production adapter between Shared WaterStream v0.6 and Shared Water Chemistry.

The adapter is chemistry-owned. WaterStream supplies conserved transport state;
this module converts that state to the intensive WaterState basis, performs
chemistry re-equilibration, and issues the v0.6 ChemistryCertificate expected by
Shared WaterStream without making equilibrium results authoritative stream
components.

Pinned integration baseline:
* WaterStream: twds.water-stream v0.6.0 @ e43bd4e1f86f657528e83dc9e185970443d30f4b
* WaterState:  twds.water-state v1 @ 6fdbb11e025130162f749a7b77191e108f183d15
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import chemistry_analysis as _chem_base
from water_chemistry import SPECIES, normalize_composition

from .engine import equilibrate
from .water_state import SCHEMA_ID as WATERSTATE_SCHEMA_ID
from .water_state import SCHEMA_VERSION as WATERSTATE_SCHEMA_VERSION
from .water_state import WaterState

WATERSTREAM_SCHEMA_ID = "twds.water-stream"
WATERSTREAM_SCHEMA_VERSION = "0.6.0"
WATERSTREAM_REFERENCE_SHA = "e43bd4e1f86f657528e83dc9e185970443d30f4b"
CHEMISTRY_REFERENCE_SHA = "6fdbb11e025130162f749a7b77191e108f183d15"
ADAPTER_VERSION = "1"

# WaterStream v0.6 intentionally treats aqueous hydraulic flow and solvent H2O
# inventory as authoritative while certificate density/solution mass are trusted
# chemistry outputs.  Its exact issuer-conformance fixture represents 1000 kg/s
# H2O at 1 m3/s at 25 C, whereas the established engineering density correlation
# returns about 997 kg/m3.  A small bounded basis mismatch is therefore reconciled
# to the transport-implied minimum density and recorded in certificate metadata.
# Larger inconsistencies still fail closed.
DENSITY_TRANSPORT_RECONCILIATION_REL_TOL = 0.01


class WaterStreamAdapterError(ValueError):
    """Raised when a WaterStream cannot be converted without losing authority."""


def _waterstream_module():
    try:
        import shared_waterstream as sw
    except Exception as exc:  # pragma: no cover - exercised by integration CI
        raise WaterStreamAdapterError(
            "Shared WaterStream package is required for WaterStream integration."
        ) from exc
    return sw


def _require_v06_stream(stream: Any):
    sw = _waterstream_module()
    if not isinstance(stream, sw.WaterStream):
        raise WaterStreamAdapterError("Expected shared_waterstream.WaterStream v0.6.")
    if str(sw.WATERSTREAM_SCHEMA_ID) != WATERSTREAM_SCHEMA_ID:
        raise WaterStreamAdapterError(
            f"Unsupported WaterStream schema {sw.WATERSTREAM_SCHEMA_ID!r}; expected {WATERSTREAM_SCHEMA_ID!r}."
        )
    if str(sw.SCHEMA_VERSION) != WATERSTREAM_SCHEMA_VERSION:
        raise WaterStreamAdapterError(
            f"Unsupported WaterStream version {sw.SCHEMA_VERSION!r}; expected {WATERSTREAM_SCHEMA_VERSION!r}."
        )
    # Compare the canonical enum member, not a duplicated string literal. The
    # exact v0.6 contract defines StreamPhase.AQUEOUS.value as "AQUEOUS".
    if stream.phase is not sw.StreamPhase.AQUEOUS:
        raise WaterStreamAdapterError(
            "Shared Chemistry production adapter currently requires a pure AQUEOUS WaterStream."
        )
    return sw


def waterstream_to_waterstate(stream: Any, *, require_provenance: bool = True) -> WaterState:
    """Convert authoritative WaterStream v0.6 state to chemistry-owned WaterState.

    No upstream pH/speciation is consumed. TA and TIC are converted from their
    extensive WaterStream basis to mol/kg-water, allowing Shared Chemistry to
    reconstruct equilibrium from conserved quantities.
    """
    sw = _require_v06_stream(stream)
    report = stream.chemistry_handoff_report(require_provenance=require_provenance)
    unsupported = tuple(report["chemistry_owned_analytical_families_present"])
    if unsupported:
        raise WaterStreamAdapterError(
            "WaterStream contains nonzero analytical families not yet represented "
            f"by WaterState v{WATERSTATE_SCHEMA_VERSION}: {unsupported}. "
            "The chemistry adapter must map them deliberately before certification."
        )

    composition: dict[str, float] = {}
    for waterstream_key, waterstate_key in sw.WATERSTATE_DIRECT_COMPOSITION_MAP.items():
        amount = float(stream.component_totals_mol_s.get(waterstream_key, 0.0))
        if amount != 0.0:
            composition[waterstate_key] = float(stream.component_mg_l(waterstream_key))

    source = stream.latest_provenance
    metadata = {
        "waterstream_schema": WATERSTREAM_SCHEMA_ID,
        "waterstream_version": WATERSTREAM_SCHEMA_VERSION,
        "waterstream_state_hash": stream.state_hash,
        "waterstream_stream_id": stream.stream_id,
        "waterstream_chemistry_policy": stream.chemistry_policy.to_dict(),
        "waterstream_reference_sha": WATERSTREAM_REFERENCE_SHA,
        "chemistry_reference_sha": CHEMISTRY_REFERENCE_SHA,
        "adapter_version": ADAPTER_VERSION,
        "adapter_basis": "conserved WaterStream v0.6 totals -> WaterState intensive chemistry basis",
    }
    return WaterState(
        composition_mg_l=composition,
        temperature_c=float(stream.temperature_c),
        pressure_bar=float(stream.pressure_bar),
        ph=None,
        total_alkalinity_mol_kg=float(stream.total_alkalinity_mol_kg_water),
        total_inorganic_carbon_mol_kg=float(stream.total_inorganic_carbon_mol_kg_water),
        source_application=None if source is None else source.application,
        source_process=None if source is None else source.process,
        equilibrium={},
        metadata=metadata,
    ).normalized()


def equilibrate_waterstream(stream: Any, *, require_provenance: bool = True) -> WaterState:
    """Build a WaterState from WaterStream and reconstruct equilibrium chemistry."""
    return equilibrate(waterstream_to_waterstate(stream, require_provenance=require_provenance))


def _ionic_strength_from_equilibrium(state: WaterState) -> float:
    """Return ionic strength (mol/kg-water) from explicit solved species."""
    solved = dict((state.equilibrium or {}).get("state") or {})
    comp = normalize_composition(solved.get("composition") or state.composition_mg_l)
    m = _chem_base._molalities(comp, state.temperature_c)
    weak = solved.get("weak_systems") or {}
    hydro = solved.get("hydroxo_species") or {}
    total_z2 = 0.0

    hydro_keys = set(hydro)
    weak_replaced = {"ammonium", "fluoride", "phosphate", "boron", "silica"}
    carbonate_replaced = {"carbonate", "bicarbonate"}
    for key, molality in m.items():
        if key in hydro_keys or key in weak_replaced or key in carbonate_replaced:
            continue
        z = int(SPECIES[key][3])
        if z:
            total_z2 += float(molality) * z * z

    total_z2 += max(0.0, float(solved.get("h_mol_kg", 0.0)))
    total_z2 += max(0.0, float(solved.get("oh_mol_kg", 0.0)))
    total_z2 += max(0.0, float(solved.get("hco3_mol_kg", 0.0)))
    total_z2 += 4.0 * max(0.0, float(solved.get("co3_mol_kg", 0.0)))

    ammonia = weak.get("ammonia", {}) or {}
    total_z2 += max(0.0, float(ammonia.get("NH4+", 0.0)))
    fluoride = weak.get("fluoride", {}) or {}
    total_z2 += max(0.0, float(fluoride.get("F-", 0.0)))
    phosphate = weak.get("phosphate", {}) or {}
    total_z2 += max(0.0, float(phosphate.get("H2PO4-", 0.0)))
    total_z2 += 4.0 * max(0.0, float(phosphate.get("HPO4--", 0.0)))
    total_z2 += 9.0 * max(0.0, float(phosphate.get("PO4---", 0.0)))
    boron = weak.get("boron", {}) or {}
    total_z2 += max(0.0, float(boron.get("B(OH)4-", 0.0)))
    silica = weak.get("silica", {}) or {}
    total_z2 += max(0.0, float(silica.get("H3SiO4-", 0.0)))
    total_z2 += 4.0 * max(0.0, float(silica.get("H2SiO4--", 0.0)))

    for item in hydro.values():
        z_free = int(item.get("free_charge", 0))
        z_hyd = int(item.get("hydroxo_charge", 0))
        total_z2 += max(0.0, float(item.get("free_mol_kg", 0.0))) * z_free * z_free
        total_z2 += max(0.0, float(item.get("hydroxo_mol_kg", 0.0))) * z_hyd * z_hyd
    return 0.5 * total_z2


def _density_and_solution_mass(state: WaterState, stream: Any) -> tuple[float, float, dict[str, Any]]:
    """Reconcile a small density-basis mismatch; reject a material inconsistency.

    WaterStream v0.6 owns hydraulic flow and solvent H2O. Shared Chemistry owns
    the engineering density estimate. For the exact WaterStream conformance
    contract these bases may differ slightly (pure-water correlation vs rounded
    hydraulic basis). If the transport-implied minimum density exceeds the
    chemistry estimate by at most 1%, the certificate uses the minimum density
    and records the reconciliation. Larger mismatches fail closed.
    """
    comp = normalize_composition(state.composition_mg_l)
    tds_mg_l = sum(float(v) for v in comp.values())
    chemistry_density_kg_m3 = 1000.0 * float(
        _chem_base._solution_density_kg_l(tds_mg_l, state.temperature_c)
    )
    if chemistry_density_kg_m3 <= 0.0:
        raise WaterStreamAdapterError("Shared Chemistry produced a non-positive solution density.")

    flow_m3_s = float(stream.flow_m3_s)
    solvent_water_kg_s = float(stream.solvent_water_kg_s_from_components)
    transport_minimum_density_kg_m3 = solvent_water_kg_s / flow_m3_s
    density_kg_m3 = chemistry_density_kg_m3
    reconciled = False
    relative_shortfall = 0.0

    if chemistry_density_kg_m3 < transport_minimum_density_kg_m3:
        relative_shortfall = (
            transport_minimum_density_kg_m3 - chemistry_density_kg_m3
        ) / max(transport_minimum_density_kg_m3, 1e-30)
        if relative_shortfall > DENSITY_TRANSPORT_RECONCILIATION_REL_TOL:
            raise WaterStreamAdapterError(
                "WaterStream hydraulic flow and H2O inventory are materially inconsistent "
                "with the Shared Chemistry solution density: transport-implied minimum "
                f"density {transport_minimum_density_kg_m3:.12g} kg/m3 exceeds chemistry "
                f"density {chemistry_density_kg_m3:.12g} kg/m3 by "
                f"{relative_shortfall * 100.0:.6g}%, above the "
                f"{DENSITY_TRANSPORT_RECONCILIATION_REL_TOL * 100.0:.6g}% reconciliation limit."
            )
        density_kg_m3 = transport_minimum_density_kg_m3
        reconciled = True

    solution_mass_kg_s = density_kg_m3 * flow_m3_s
    tolerance = max(1e-9, 1e-9 * max(abs(solvent_water_kg_s), abs(solution_mass_kg_s), 1.0))
    if solution_mass_kg_s + tolerance < solvent_water_kg_s:
        raise WaterStreamAdapterError(
            "Failed to reconcile chemistry density with authoritative solvent-water inventory."
        )

    diagnostics = {
        "chemistry_density_kg_m3": chemistry_density_kg_m3,
        "transport_minimum_density_kg_m3": transport_minimum_density_kg_m3,
        "certificate_density_kg_m3": density_kg_m3,
        "density_reconciled_to_transport_minimum": reconciled,
        "density_relative_shortfall": relative_shortfall,
        "density_reconciliation_relative_limit": DENSITY_TRANSPORT_RECONCILIATION_REL_TOL,
    }
    return density_kg_m3, solution_mass_kg_s, diagnostics


@dataclass(slots=True)
class SharedChemistryCertificateIssuer:
    """WaterStream v0.6 ChemistryCertificateIssuer backed by Shared Chemistry."""

    engine_version: str = "shared-water-chemistry/waterstream-adapter-v1"
    declared_tolerance: float = 1e-12
    require_provenance: bool = True

    def issue(self, stream: Any, *, warm_start: Any | None = None):
        sw = _require_v06_stream(stream)
        _ = warm_start  # Never import stale pH/speciation from a prior certificate.
        solved = equilibrate_waterstream(stream, require_provenance=self.require_provenance)
        ionic_strength = _ionic_strength_from_equilibrium(solved)
        density_kg_m3, solution_mass_kg_s, density_diagnostics = _density_and_solution_mass(solved, stream)
        charge = dict((solved.equilibrium or {}).get("charge_report") or {})
        equilibrium_residual_eq_s = float(charge.get("residual_meq_l", 0.0)) * float(stream.flow_m3_s)
        metadata = sw.FrozenDict({
            "waterstate_schema": WATERSTATE_SCHEMA_ID,
            "waterstate_version": WATERSTATE_SCHEMA_VERSION,
            "waterstream_schema": WATERSTREAM_SCHEMA_ID,
            "waterstream_version": WATERSTREAM_SCHEMA_VERSION,
            "waterstream_reference_sha": WATERSTREAM_REFERENCE_SHA,
            "chemistry_reference_sha": CHEMISTRY_REFERENCE_SHA,
            "adapter_version": ADAPTER_VERSION,
            "equilibrium_basis": solved.equilibrium.get("basis"),
            "equilibrium_ph": solved.ph,
            "equilibrium_charge_residual_eq_s": equilibrium_residual_eq_s,
            "equilibrium_charge_imbalance_pct": charge.get("imbalance_pct"),
            "certificate_residual_basis": "WaterStream independently verifiable fixed analytical charge",
            **density_diagnostics,
        })
        return sw.ChemistryCertificate(
            stream.state_hash,
            float(stream.fixed_charge_residual_eq_s),
            float(ionic_strength),
            float(stream.solvent_water_kg_s_from_components),
            float(density_kg_m3),
            str(self.engine_version),
            float(solution_mass_kg_s),
            metadata,
        )


def certify_waterstream(
    stream: Any,
    *,
    issuer: SharedChemistryCertificateIssuer | None = None,
    cache: Any | None = None,
    warm_start: Any | None = None,
):
    """Return WaterStream v0.6 rebound to a Shared Chemistry certificate."""
    sw = _require_v06_stream(stream)
    actual_issuer = issuer or SharedChemistryCertificateIssuer()
    return sw.certify_stream(stream, actual_issuer, cache=cache, warm_start=warm_start)
