"""Shared WaterStream v0.6 chemistry-integration contract.

v0.6 is a deliberate pre-v1.0 schema revision that removes two ambiguities
found while mapping the audited v0.5 transport contract to Shared Water
Chemistry WaterState:

* aqueous volume flow is authoritative transport/hydraulic state, so an adapter
  can construct the chemistry facade's mg/L analytical basis before chemistry
  has issued a certificate;
* ``toth_eq_s`` is defined exactly as extensive total alkalinity/proton-condition
  equivalents on the Shared Water Chemistry TA convention.

No equilibrium equations live here. pH, activity, speciation, ionic strength,
saturation state and other derived chemistry remain chemistry-owned.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Protocol

from . import v05 as _v05

# Re-use the already-audited transport primitives/registry.  The package root
# exposes v0.6; these imports are an internal implementation detail.
FrozenDict = _v05.FrozenDict
freeze = _v05.freeze
thaw = _v05.thaw
canonical_json = _v05.canonical_json
content_hash = _v05.content_hash
_num = _v05._num
QuantityType = _v05.QuantityType
TransportRole = _v05.TransportRole
ComponentDefinition = _v05.ComponentDefinition
ComponentRegistry = _v05.ComponentRegistry
DEFAULT_COMPONENT_REGISTRY = _v05.DEFAULT_COMPONENT_REGISTRY
canonical_component_id = _v05.canonical_component_id
validate_authoritative_component = _v05.validate_authoritative_component
ProvenanceRecord = _v05.ProvenanceRecord
RawMeasurement = _v05.RawMeasurement
ReconciliationDecision = _v05.ReconciliationDecision
RawWaterAnalysis = _v05.RawWaterAnalysis
ExtensionTransportPolicy = _v05.ExtensionTransportPolicy
ExtensionSpec = _v05.ExtensionSpec
ExtensionState = _v05.ExtensionState
ExtensionTransformer = _v05.ExtensionTransformer
_transform_extension = _v05._transform_extension
MixingRule = _v05.MixingRule
TrackedTransportPolicy = _v05.TrackedTransportPolicy
TrackedQuantity = _v05.TrackedQuantity
StreamPhase = _v05.StreamPhase
PhaseInventoryItem = _v05.PhaseInventoryItem
StreamDiagnostics = _v05.StreamDiagnostics
ChargeValidationPolicy = _v05.ChargeValidationPolicy
DEFAULT_CHARGE_VALIDATION_POLICY = _v05.DEFAULT_CHARGE_VALIDATION_POLICY
MassLedgerEntry = _v05.MassLedgerEntry
MassLedger = _v05.MassLedger
ReactionTransformation = _v05.ReactionTransformation
UnitOpConformanceResult = _v05.UnitOpConformanceResult

WaterStreamError = _v05.WaterStreamError
ChargeResidualError = _v05.ChargeResidualError
ChemistryCertificateError = _v05.ChemistryCertificateError
UncertifiedChemistryError = _v05.UncertifiedChemistryError
NonVolumetricFlowError = _v05.NonVolumetricFlowError
MixedPhaseThermalError = _v05.MixedPhaseThermalError
SelectiveSplitError = _v05.SelectiveSplitError
ExtensionTransportError = _v05.ExtensionTransportError
TrackedQuantityTransportError = _v05.TrackedQuantityTransportError
MassLedgerClosureError = _v05.MassLedgerClosureError
LedgerConventionError = _v05.LedgerConventionError
UnreconciledAnalysisError = _v05.UnreconciledAnalysisError

SCHEMA_VERSION = "0.6.0"
LEGACY_WATERSTREAM_VERSION = "0.5.0"
RAW_ANALYSIS_SCHEMA_VERSION = "0.5.0"
WATERSTREAM_SCHEMA_ID = _v05.WATERSTREAM_SCHEMA_ID
RAW_ANALYSIS_SCHEMA_ID = _v05.RAW_ANALYSIS_SCHEMA_ID
CHEMISTRY_CERTIFICATE_SCHEMA_ID = _v05.CHEMISTRY_CERTIFICATE_SCHEMA_ID
MASS_LEDGER_SCHEMA_ID = _v05.MASS_LEDGER_SCHEMA_ID
H2O_MOLAR_MASS_G_MOL = _v05.H2O_MOLAR_MASS_G_MOL

# Direct identifier/basis mappings that do not require speciation assumptions.
# The chemistry adapter may use WaterStream.component_mg_l() for these only.
WATERSTATE_DIRECT_COMPOSITION_MAP = FrozenDict({
    "sodium": "sodium",
    "potassium": "potassium",
    "magnesium": "magnesium",
    "calcium": "calcium",
    "strontium": "strontium",
    "barium": "barium",
    "fluoride": "fluoride",
    "chloride": "chloride",
    "sulfate": "sulfate",
    "nitrate": "nitrate",
    "bromide": "bromide",
    "total_boron": "boron",       # mg/L as elemental B
    "total_silica": "silica",     # mg/L as SiO2
})

# These are authoritative WaterStream analytical families, but the validated
# WaterState facade currently exposes species-oriented keys for them.  The
# chemistry-owned adapter must map/extend them deliberately and must never
# silently discard a nonzero family total.
CHEMISTRY_OWNED_ANALYTICAL_FAMILIES = (
    "total_ammonia",
    "total_phosphate",
    "total_iron",
    "total_manganese",
)


@dataclass(frozen=True, slots=True)
class ChemistryCertificate(_v05.ChemistryCertificate):
    """Derived chemistry certificate bound to a v0.6 WaterStream state hash."""

    def to_dict(self):
        out = _v05.ChemistryCertificate.to_dict(self)
        out["version"] = SCHEMA_VERSION
        return out

    @classmethod
    def from_dict(cls, payload):
        if payload.get("schema") != CHEMISTRY_CERTIFICATE_SCHEMA_ID or str(payload.get("version")) != SCHEMA_VERSION:
            raise ChemistryCertificateError("Unsupported ChemistryCertificate schema/version.")
        return cls(
            str(payload.get("state_hash") or ""),
            payload.get("residual_charge_eq_s", 0),
            payload.get("ionic_strength_mol_kg", 0),
            payload.get("solvent_water_kg_s", 0),
            payload.get("density_kg_m3", 0),
            str(payload.get("engine_version") or ""),
            payload.get("solution_mass_kg_s", 0),
            FrozenDict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class WaterStream(_v05.WaterStream):
    """Immutable conserved process state suitable for chemistry reconstruction.

    v0.6 semantics:

    * ``component_totals_mol_s`` are authoritative extensive analytical totals.
    * ``h2o`` is solvent-water mol/s.
    * ``toth_eq_s`` is **total alkalinity equivalent/s**, on the same analytical
      proton-condition convention consumed by Shared Water Chemistry
      ``WaterState.total_alkalinity_mol_kg``. Positive values are positive total
      alkalinity/acid-neutralizing capacity. It is not pH and is never solved
      from pH here.
    * ``aqueous_volume_flow_m3_s`` is authoritative hydraulic volume flow for an
      AQUEOUS stream. It is not chemistry-derived and therefore exists before a
      ChemistryCertificate.
    """

    aqueous_volume_flow_m3_s: float | None = None

    def __post_init__(self):
        _v05.WaterStream.__post_init__(self)
        flow = self.aqueous_volume_flow_m3_s
        if self.phase is StreamPhase.AQUEOUS:
            if flow is None:
                raise WaterStreamError("AQUEOUS WaterStream v0.6 requires aqueous_volume_flow_m3_s.")
            flow = _num(flow, "aqueous_volume_flow_m3_s")
            if flow <= 0:
                raise WaterStreamError("AQUEOUS aqueous_volume_flow_m3_s must be positive.")
            object.__setattr__(self, "aqueous_volume_flow_m3_s", flow)
        else:
            if flow is not None:
                raise WaterStreamError(
                    f"aqueous_volume_flow_m3_s is only valid for a pure AQUEOUS WaterStream; phase is {self.phase.value}."
                )
            object.__setattr__(self, "aqueous_volume_flow_m3_s", None)

    def _state_payload(self):
        return {
            "schema": WATERSTREAM_SCHEMA_ID,
            "version": SCHEMA_VERSION,
            "temperature_c": self.temperature_c,
            "pressure_bar": self.pressure_bar,
            "component_totals_mol_s": self.component_totals_mol_s.to_dict(),
            "toth_eq_s": self.toth_eq_s,
            "aqueous_volume_flow_m3_s": self.aqueous_volume_flow_m3_s,
            "phase": self.phase.value,
            "phase_inventory": [item.to_dict() for item in self.phase_inventory],
            "chemistry_policy": self.chemistry_policy.to_dict(),
        }

    @property
    def flow_m3_s(self):
        if self.phase is not StreamPhase.AQUEOUS:
            raise NonVolumetricFlowError(
                f"flow_m3_s is unavailable for phase {self.phase.value}; use owner phase/hydraulic physics."
            )
        return float(self.aqueous_volume_flow_m3_s)

    @property
    def total_alkalinity_mol_kg_water(self) -> float:
        water = self.solvent_water_kg_s_from_components
        if water <= 0:
            raise WaterStreamError("Total alkalinity mol/kg-water requires positive H2O inventory.")
        return float(self.toth_eq_s) / water

    @property
    def total_inorganic_carbon_mol_kg_water(self) -> float:
        water = self.solvent_water_kg_s_from_components
        if water <= 0:
            raise WaterStreamError("Total inorganic carbon mol/kg-water requires positive H2O inventory.")
        return float(self.component_totals_mol_s.get("total_inorganic_carbon", 0.0)) / water

    def component_mol_kg_water(self, component_id: str) -> float:
        canonical = canonical_component_id(component_id)
        water = self.solvent_water_kg_s_from_components
        if water <= 0:
            raise WaterStreamError("Molality conversion requires positive H2O inventory.")
        return float(self.component_totals_mol_s.get(canonical, 0.0)) / water

    def component_mg_l(self, component_id: str) -> float:
        if self.phase is not StreamPhase.AQUEOUS:
            raise NonVolumetricFlowError("mg/L conversion is defined only for a pure AQUEOUS WaterStream.")
        definition = DEFAULT_COMPONENT_REGISTRY.get(component_id)
        if definition.molar_mass_g_mol is None:
            raise WaterStreamError(f"Component {definition.canonical_id!r} has no declared analytical mass basis.")
        # mol/s * g/mol divided by m3/s = g/m3 = mg/L.
        return (
            float(self.component_totals_mol_s.get(definition.canonical_id, 0.0))
            * float(definition.molar_mass_g_mol)
            / self.flow_m3_s
        )

    @property
    def latest_provenance(self) -> ProvenanceRecord | None:
        return self.provenance[-1] if self.provenance else None

    def chemistry_handoff_report(self, *, require_provenance: bool = True) -> FrozenDict:
        if self.phase is not StreamPhase.AQUEOUS:
            raise WaterStreamError("Shared Chemistry handoff currently requires a pure AQUEOUS WaterStream.")
        if require_provenance and not self.provenance:
            raise WaterStreamError("Production Shared Chemistry handoff requires WaterStream provenance.")
        nonzero_owned = tuple(
            key for key in CHEMISTRY_OWNED_ANALYTICAL_FAMILIES
            if float(self.component_totals_mol_s.get(key, 0.0)) != 0.0
        )
        source = self.latest_provenance
        return FrozenDict({
            "waterstream_schema": WATERSTREAM_SCHEMA_ID,
            "waterstream_version": SCHEMA_VERSION,
            "state_hash": self.state_hash,
            "analytical_basis": "component_totals_mol_s",
            "component_rate_unit": "mol/s",
            "solvent_water_rate_unit": "kg/s",
            "aqueous_volume_flow_unit": "m3/s",
            "toth_definition": "total_alkalinity_equivalents_on_shared_water_chemistry_TA_convention",
            "toth_unit": "eq/s",
            "total_alkalinity_mol_kg_water": self.total_alkalinity_mol_kg_water,
            "total_inorganic_carbon_mol_kg_water": self.total_inorganic_carbon_mol_kg_water,
            "source_application": None if source is None else source.application,
            "source_process": None if source is None else source.process,
            "chemistry_owned_analytical_families_present": nonzero_owned,
        })

    def _validate_certificate(self, cert):
        _v05.WaterStream._validate_certificate(self, cert)
        if not isinstance(cert, ChemistryCertificate):
            raise ChemistryCertificateError("WaterStream v0.6 requires a v0.6 ChemistryCertificate.")

    def to_dict(self):
        out = _v05.WaterStream.to_dict(self)
        out["version"] = SCHEMA_VERSION
        out["aqueous_volume_flow_m3_s"] = self.aqueous_volume_flow_m3_s
        return out

    @classmethod
    def from_dict(cls, payload):
        if payload.get("schema") != WATERSTREAM_SCHEMA_ID or str(payload.get("version")) != SCHEMA_VERSION:
            raise WaterStreamError("Unsupported WaterStream schema/version; use migrate_v05_payload() for v0.5 payloads.")
        forbidden = {
            key for key in payload
            if str(key).lower() in {
                "ph", "p_h", "hydrogen_activity", "flow_m3_s",
                "charge_tolerance_eq_s", "mineral_identity",
            }
        }
        if forbidden:
            raise WaterStreamError(f"Independent derived/legacy fields forbidden: {sorted(forbidden)}")
        known = {
            "schema", "version", "stream_id", "temperature_c", "pressure_bar",
            "component_totals_mol_s", "toth_eq_s", "aqueous_volume_flow_m3_s",
            "phase", "phase_inventory", "chemistry_policy", "tracked_quantities",
            "extensions", "diagnostics", "chemistry_certificate", "provenance",
        }
        return cls(
            str(payload.get("stream_id") or ""),
            payload.get("temperature_c", 25),
            payload.get("pressure_bar", 1.01325),
            FrozenDict(payload.get("component_totals_mol_s") or {}),
            payload.get("toth_eq_s", 0),
            StreamPhase(str(payload.get("phase") or StreamPhase.AQUEOUS.value)),
            tuple(PhaseInventoryItem.from_dict(x) for x in (payload.get("phase_inventory") or ())),
            FrozenDict(payload.get("chemistry_policy") or {}),
            FrozenDict(payload.get("tracked_quantities") or {}),
            FrozenDict(payload.get("extensions") or {}),
            StreamDiagnostics.from_dict(payload.get("diagnostics") or {}),
            None if payload.get("chemistry_certificate") is None else ChemistryCertificate.from_dict(payload["chemistry_certificate"]),
            tuple(ProvenanceRecord.from_dict(x) for x in (payload.get("provenance") or ())),
            FrozenDict({key: value for key, value in payload.items() if key not in known}),
            aqueous_volume_flow_m3_s=payload.get("aqueous_volume_flow_m3_s"),
        )


class ChemistryCertificateIssuer(Protocol):
    engine_version: str
    declared_tolerance: float
    def issue(self, stream: WaterStream, *, warm_start: ChemistryCertificate | None = None) -> ChemistryCertificate: ...


class ChemistryCertificateCache:
    def __init__(self):
        self._cache: dict[tuple[str, str], ChemistryCertificate] = {}
    def get(self, state_hash, engine_version=None):
        state_hash = str(state_hash)
        if engine_version is not None:
            return self._cache.get((state_hash, str(engine_version).strip()))
        matches = [cert for (h, _), cert in self._cache.items() if h == state_hash]
        return matches[0] if len(matches) == 1 else None
    def put(self, certificate):
        if not isinstance(certificate, ChemistryCertificate):
            raise ChemistryCertificateError("v0.6 cache accepts only v0.6 ChemistryCertificate objects.")
        self._cache[(certificate.state_hash, certificate.engine_version)] = certificate
    def clear(self): self._cache.clear()
    def __len__(self): return len(self._cache)


def certify_stream(stream, issuer, *, cache=None, warm_start=None):
    if not isinstance(stream, WaterStream):
        raise WaterStreamError("certify_stream() requires WaterStream v0.6.")
    engine_version = str(getattr(issuer, "engine_version", "")).strip()
    if not engine_version:
        raise ChemistryCertificateError("ChemistryCertificateIssuer.engine_version is required.")
    if cache is not None:
        cached = cache.get(stream.state_hash, engine_version)
        if cached is not None:
            return stream.with_chemistry_certificate(cached)
    cert = issuer.issue(stream, warm_start=warm_start)
    if not isinstance(cert, ChemistryCertificate):
        raise ChemistryCertificateError("Issuer must return ChemistryCertificate v0.6.")
    if cert.engine_version != engine_version:
        raise ChemistryCertificateError(
            f"Issuer engine_version {engine_version!r} disagrees with certificate engine_version {cert.engine_version!r}."
        )
    certified = stream.with_chemistry_certificate(cert)
    if cache is not None:
        cache.put(cert)
    return certified


def _issuer_fixture(high=False):
    comps = {
        "h2o": 1000 * 1000 / H2O_MOLAR_MASS_G_MOL,
        "sodium": 8.0 if high else 0.05,
        "chloride": 8.0 if high else 0.05,
    }
    return WaterStream(
        "issuer-fixture", 25, 2, FrozenDict(comps), 0.0,
        aqueous_volume_flow_m3_s=1.0,
    )


def assert_issuer_conformant(issuer):
    engine_version = str(getattr(issuer, "engine_version", "")).strip()
    if not engine_version:
        raise AssertionError("Issuer must declare nonempty engine_version.")
    tolerance = _num(getattr(issuer, "declared_tolerance", None), "issuer.declared_tolerance")
    if tolerance < 0:
        raise AssertionError("Issuer declared_tolerance must be nonnegative.")
    target = _issuer_fixture(True)
    seed_stream = _issuer_fixture(False)
    seed = issuer.issue(seed_stream, warm_start=None); seed_stream.with_chemistry_certificate(seed)
    cold1 = issuer.issue(target, warm_start=None); target.with_chemistry_certificate(cold1)
    cold2 = issuer.issue(target, warm_start=None); target.with_chemistry_certificate(cold2)
    for cert in (seed, cold1, cold2):
        if not isinstance(cert, ChemistryCertificate):
            raise AssertionError("Issuer returned a non-v0.6 ChemistryCertificate.")
        if cert.engine_version != engine_version:
            raise AssertionError("Issuer returned certificate with inconsistent engine_version.")
    if canonical_json(cold1.to_dict()) != canonical_json(cold2.to_dict()):
        raise AssertionError("Issuer is not deterministic for identical inputs.")
    warm = issuer.issue(target, warm_start=seed); target.with_chemistry_certificate(warm)
    if warm.engine_version != engine_version:
        raise AssertionError("Warm-start certificate engine_version differs from issuer.")
    for field_name in (
        "residual_charge_eq_s", "ionic_strength_mol_kg", "solvent_water_kg_s",
        "density_kg_m3", "solution_mass_kg_s",
    ):
        delta = abs(float(getattr(cold1, field_name)) - float(getattr(warm, field_name)))
        if delta > tolerance:
            raise AssertionError(
                f"Warm-start {field_name} differs from cold by {delta:.12g}, exceeding declared tolerance {tolerance:.12g}."
            )
    return {
        "cold_warm_equivalent": True,
        "deterministic_identical_inputs": True,
        "residual_charge_verified": True,
        "solvent_water_verified": True,
        "trusted_not_independently_verified": (
            "ionic_strength_mol_kg", "density_kg_m3", "solution_mass_kg_s"
        ),
    }


def mix_water_streams(streams, *, stream_id, output_temperature_c=None,
                      extension_transformers=None, engine_version=None,
                      source_application=None, source_process=None):
    rows = tuple(streams)
    if not rows:
        raise WaterStreamError("Mixer needs input streams.")
    if any(not isinstance(stream, WaterStream) for stream in rows):
        raise WaterStreamError("v0.6 mixer accepts only WaterStream v0.6 inputs.")
    policies = [stream.chemistry_policy.to_dict() for stream in rows]
    if any(policy != policies[0] for policy in policies[1:]):
        raise WaterStreamError("Mixer inputs carry different chemistry_policy values; owner policy reconciliation is required.")
    all_aqueous = all(stream.phase is StreamPhase.AQUEOUS for stream in rows)
    flows = None
    output_flow = None
    if all_aqueous:
        flows = [stream.flow_m3_s for stream in rows]
        output_flow = sum(flows)
        temperature = sum(flow * stream.temperature_c for flow, stream in zip(flows, rows)) / output_flow
    else:
        if output_temperature_c is None:
            raise MixedPhaseThermalError(
                "Generic mixer refuses mixed/non-volumetric phase temperature calculation; owner must supply output_temperature_c."
            )
        temperature = _num(output_temperature_c, "output_temperature_c")
    components = {
        key: sum(float(stream.component_totals_mol_s.get(key, 0.0)) for stream in rows)
        for key in set().union(*(stream.component_totals_mol_s.keys() for stream in rows))
    }
    tracked = {
        key: _v05._mix_tracked(key, rows, flows).to_dict()
        for key in set().union(*(stream.tracked_quantities.keys() for stream in rows))
    }
    transformers = dict(extension_transformers or {})
    extensions = {}
    for namespace in set().union(*(stream.extensions.keys() for stream in rows)):
        states = tuple(x for x in (stream.extension(namespace) for stream in rows) if x is not None)
        if len(states) != len(rows) and namespace not in transformers:
            raise ExtensionTransportError(f"Extension {namespace!r} missing from mixer input; owner transform is required.")
        transformed = _transform_extension(
            states, operation="mix", context={"input_count": len(rows)},
            transformer=transformers.get(namespace),
        )
        if transformed is not None:
            extensions[namespace] = transformed.to_dict()
    phase = rows[0].phase if all(stream.phase is rows[0].phase for stream in rows) else StreamPhase.MIXED
    provenance = ProvenanceRecord(
        "mixer", stream_id,
        source_application or "shared-waterstream",
        source_process or "v0.6_mix",
        engine_version,
        tuple(stream.stream_id for stream in rows),
    )
    return WaterStream(
        stream_id=stream_id,
        temperature_c=temperature,
        pressure_bar=min(stream.pressure_bar for stream in rows),
        component_totals_mol_s=FrozenDict(components),
        toth_eq_s=sum(stream.toth_eq_s for stream in rows),
        phase=phase,
        phase_inventory=_v05._inventory_mix(rows),
        chemistry_policy=FrozenDict(policies[0]),
        tracked_quantities=FrozenDict(tracked),
        extensions=FrozenDict(extensions),
        diagnostics=StreamDiagnostics(
            FrozenDict({"mixer_inputs": len(rows)}),
            ("ChemistryCertificate invalidated by mixing; recertification required.",),
        ),
        chemistry_certificate=None,
        provenance=tuple((*rows[0].provenance, provenance)) if len(rows) == 1 else (provenance,),
        aqueous_volume_flow_m3_s=output_flow if phase is StreamPhase.AQUEOUS else None,
    )


def split_water_stream(stream, fractions, *, composition_preserving,
                       daughter_aqueous_volume_flow_m3_s=None,
                       extension_transformers=None, tracked_transformers=None,
                       engine_version=None):
    if not isinstance(stream, WaterStream):
        raise WaterStreamError("v0.6 splitter requires WaterStream v0.6.")
    if not isinstance(composition_preserving, bool):
        raise SelectiveSplitError("composition_preserving must be an explicit boolean.")
    scalar_mode = all(isinstance(value, (int, float)) for value in fractions.values())
    if scalar_mode:
        scalar = {str(key): _num(value, f"split fraction {key}") for key, value in fractions.items()}
        if not scalar or any(value < 0 for value in scalar.values()) or abs(sum(scalar.values()) - 1.0) > 1e-12:
            raise SelectiveSplitError("Scalar split fractions must be nonnegative and sum to 1.0.")
        child_fractions = {
            child: {component: fraction for component in stream.component_totals_mol_s}
            for child, fraction in scalar.items()
        }
    else:
        child_fractions = _v05._normalize_selective(stream, fractions)
        scalar = {}
        if abs(stream.toth_eq_s) > 1e-15:
            raise SelectiveSplitError(
                "Selective split of nonzero total alkalinity/TOTH has no generic partition rule; owner unit-operation physics must assign daughter TOTH explicitly."
            )
    provided_flows = None if daughter_aqueous_volume_flow_m3_s is None else {
        str(key): _num(value, f"daughter aqueous volume flow {key}")
        for key, value in daughter_aqueous_volume_flow_m3_s.items()
    }
    if not scalar_mode and stream.phase is StreamPhase.AQUEOUS:
        if provided_flows is None or set(provided_flows) != set(child_fractions):
            raise SelectiveSplitError(
                "Selective split of an AQUEOUS stream requires daughter_aqueous_volume_flow_m3_s for every daughter."
            )
        if any(value <= 0 for value in provided_flows.values()):
            raise SelectiveSplitError("Selective daughter aqueous volume flows must be positive.")
        tolerance = max(1e-12, 1e-10 * stream.flow_m3_s)
        if abs(sum(provided_flows.values()) - stream.flow_m3_s) > tolerance:
            raise SelectiveSplitError("Selective daughter aqueous volume flows must conserve parent aqueous volume flow.")

    extension_transformers = dict(extension_transformers or {})
    tracked_transformers = dict(tracked_transformers or {})
    output = {}
    for child, component_fractions in child_fractions.items():
        components = {
            key: float(value) * component_fractions[key]
            for key, value in stream.component_totals_mol_s.items()
        }
        toth_fraction = scalar[child] if scalar_mode else 0.0
        inventory = []
        for item in stream.phase_inventory:
            item_components = {
                key: float(value) * component_fractions[key]
                for key, value in item.component_totals_mol_s.items()
            }
            if any(value > 0 for value in item_components.values()):
                inventory.append(PhaseInventoryItem(item.phase, item.identity, FrozenDict(item_components), item.metadata))
        child_phase = _v05._phase_for_inventory(tuple(inventory))
        if child_phase is StreamPhase.AQUEOUS:
            if scalar_mode:
                child_flow = stream.flow_m3_s * scalar[child]
            else:
                if provided_flows is None or child not in provided_flows:
                    raise SelectiveSplitError(
                        f"Selective daughter {child!r} is AQUEOUS and requires explicit aqueous volume flow."
                    )
                child_flow = provided_flows[child]
        else:
            child_flow = None
        tracked = {}
        for key in stream.tracked_quantities:
            quantity = stream.tracked(key)
            if quantity.transport_policy is TrackedTransportPolicy.OWNER_MUST_TRANSFORM:
                if key not in tracked_transformers:
                    raise TrackedQuantityTransportError(
                        f"Tracked quantity {key!r} requires owner {quantity.owner!r} transform for split."
                    )
                quantity = tracked_transformers[key](quantity, "split", FrozenDict({"daughter": child}))
            elif quantity.transport_policy is TrackedTransportPolicy.UNDEFINED_OUTSIDE_MIXER:
                quantity = TrackedQuantity.unavailable(
                    unit=quantity.unit, dimension=quantity.dimension,
                    mixing_rule=quantity.mixing_rule,
                    transport_policy=quantity.transport_policy,
                    owner=quantity.owner,
                    reason=f"{key}: UNDEFINED_OUTSIDE_MIXER for split.",
                )
            elif quantity.mixing_rule is MixingRule.EXTENSIVE_SUM:
                if not scalar_mode:
                    raise TrackedQuantityTransportError(
                        f"Extensive tracked quantity {key!r} requires owner transform for selective split."
                    )
                quantity = replace(quantity, value=float(quantity.value) * scalar[child])
            if quantity is not None:
                tracked[key] = quantity.to_dict()
        extensions = {}
        for namespace in stream.extensions:
            state = stream.extension(namespace)
            context = (
                {"fraction": scalar[child], "flow_fraction": scalar[child]}
                if scalar_mode else {"component_fractions": component_fractions}
            )
            context["composition_preserving"] = composition_preserving
            transformed = _transform_extension(
                (state,), operation="split", context=context,
                transformer=extension_transformers.get(namespace),
            )
            if transformed is not None:
                extensions[namespace] = transformed.to_dict()
        child_stream = WaterStream(
            stream_id=child,
            temperature_c=stream.temperature_c,
            pressure_bar=stream.pressure_bar,
            component_totals_mol_s=FrozenDict(components),
            toth_eq_s=stream.toth_eq_s * toth_fraction,
            phase=child_phase,
            phase_inventory=tuple(inventory),
            chemistry_policy=stream.chemistry_policy,
            tracked_quantities=FrozenDict(tracked),
            extensions=FrozenDict(extensions),
            diagnostics=stream.diagnostics,
            chemistry_certificate=None,
            provenance=stream.provenance,
            aqueous_volume_flow_m3_s=child_flow,
        )
        can_rebind = (
            scalar_mode
            and composition_preserving is True
            and stream.phase is StreamPhase.AQUEOUS
            and stream.chemistry_certificate is not None
        )
        if can_rebind:
            parent_cert = stream.require_valid_chemistry_certificate()
            fraction = scalar[child]
            child_stream = child_stream.with_chemistry_certificate(
                ChemistryCertificate(
                    child_stream.state_hash,
                    parent_cert.residual_charge_eq_s * fraction,
                    parent_cert.ionic_strength_mol_kg,
                    parent_cert.solvent_water_kg_s * fraction,
                    parent_cert.density_kg_m3,
                    parent_cert.engine_version,
                    parent_cert.solution_mass_kg_s * fraction,
                    parent_cert.metadata,
                )
            )
        output[child] = child_stream
    return output


def migrate_v05_payload(payload: Mapping[str, Any], *,
                        aqueous_volume_flow_m3_s: float | None = None,
                        confirm_toth_is_total_alkalinity: bool = False) -> WaterStream:
    """Explicitly migrate a v0.5 payload without guessing chemistry semantics.

    Nonzero v0.5 TOTH had an intentionally generic proton-condition meaning.
    Migration therefore requires explicit confirmation before reinterpreting it
    as the v0.6 Shared-Chemistry TA convention.  A v0.5 chemistry certificate is
    invalidated because both schema identity and state hash change.

    For an aqueous payload, volume flow may be supplied directly.  If omitted,
    it may be recovered from an attached v0.5 certificate's
    ``solution_mass_kg_s / density_kg_m3``.  No other inference is allowed.
    """
    if payload.get("schema") != WATERSTREAM_SCHEMA_ID or str(payload.get("version")) != LEGACY_WATERSTREAM_VERSION:
        raise WaterStreamError("migrate_v05_payload() requires a twds.water-stream v0.5 payload.")
    toth = _num(payload.get("toth_eq_s", 0.0), "legacy toth_eq_s")
    if abs(toth) > 1e-15 and confirm_toth_is_total_alkalinity is not True:
        raise WaterStreamError(
            "Nonzero v0.5 TOTH cannot be silently reinterpreted as v0.6 total alkalinity; set confirm_toth_is_total_alkalinity=True only after verifying the source basis."
        )
    phase = StreamPhase(str(payload.get("phase") or StreamPhase.AQUEOUS.value))
    flow = aqueous_volume_flow_m3_s
    old_cert = payload.get("chemistry_certificate")
    flow_source = "explicit"
    if phase is StreamPhase.AQUEOUS and flow is None and isinstance(old_cert, Mapping):
        density = _num(old_cert.get("density_kg_m3"), "legacy certificate density_kg_m3")
        solution_mass = _num(old_cert.get("solution_mass_kg_s"), "legacy certificate solution_mass_kg_s")
        if density > 0 and solution_mass > 0:
            flow = solution_mass / density
            flow_source = "v0.5_certificate"
    if phase is StreamPhase.AQUEOUS:
        if flow is None:
            raise WaterStreamError(
                "AQUEOUS v0.5 migration requires aqueous_volume_flow_m3_s or a usable v0.5 chemistry certificate."
            )
        flow = _num(flow, "aqueous_volume_flow_m3_s")
        if flow <= 0:
            raise WaterStreamError("Migrated aqueous volume flow must be positive.")
    else:
        flow = None
        flow_source = "not_applicable"

    migrated = dict(payload)
    migrated["version"] = SCHEMA_VERSION
    migrated["aqueous_volume_flow_m3_s"] = flow
    migrated["chemistry_certificate"] = None
    diagnostics = dict(migrated.get("diagnostics") or {})
    warnings = list(diagnostics.get("warnings") or [])
    warnings.append(
        f"Migrated from WaterStream v0.5 to v0.6; chemistry certificate invalidated; aqueous flow source={flow_source}."
    )
    diagnostics["warnings"] = warnings
    migrated["diagnostics"] = diagnostics
    return WaterStream.from_dict(migrated)


class UnitOpConformanceAdapter(Protocol):
    def solve(self, feed: WaterStream, *, tracked_transformers: Mapping | None = None,
              extension_transformers: Mapping | None = None) -> UnitOpConformanceResult: ...
    def solve_selective_split(self, feed: WaterStream, fractions: Mapping[str, Mapping[str, float]],
                              *, composition_preserving: bool,
                              daughter_aqueous_volume_flow_m3_s: Mapping[str, float]) -> UnitOpConformanceResult: ...


def _direct_certificate(stream: WaterStream) -> ChemistryCertificate:
    water = stream.solvent_water_kg_s_from_components
    ionic2 = 0.0
    for key, amount in stream.component_totals_mol_s.items():
        charge = DEFAULT_COMPONENT_REGISTRY.get(key).charge or 0
        ionic2 += float(amount) * charge * charge
    density = 1000.0
    return ChemistryCertificate(
        stream.state_hash,
        stream.fixed_charge_residual_eq_s,
        0.0 if water <= 0 else 0.5 * ionic2 / water,
        water,
        density,
        "unitop-conformance-fixture-v06",
        density * stream.flow_m3_s,
    )


def _base_stream(*, tracked=None, extension=None) -> WaterStream:
    components = {
        "h2o": 1000.0 * 1000.0 / H2O_MOLAR_MASS_G_MOL,
        "sodium": 1.0,
        "chloride": 1.0,
    }
    tracked_values = {} if tracked is None else {tracked[0]: tracked[1].to_dict()}
    extension_values = {} if extension is None else {extension.namespace: extension.to_dict()}
    raw = WaterStream(
        "unitop-conformance-feed", 25.0, 1.5, FrozenDict(components), 0.0,
        tracked_quantities=FrozenDict(tracked_values),
        extensions=FrozenDict(extension_values),
        aqueous_volume_flow_m3_s=1.0,
    )
    return raw.with_chemistry_certificate(_direct_certificate(raw))


def _extract(result):
    if not hasattr(result, "outputs") or not hasattr(result, "ledger"):
        raise AssertionError("UnitOp conformance result must expose .outputs and .ledger.")
    outputs = tuple(result.outputs.values()) if isinstance(result.outputs, Mapping) else tuple(result.outputs)
    if not outputs or any(not isinstance(stream, WaterStream) for stream in outputs):
        raise AssertionError("UnitOp conformance result contains no valid WaterStream v0.6 outputs.")
    if not isinstance(result.ledger, MassLedger):
        raise AssertionError("UnitOp conformance result .ledger must be a MassLedger.")
    return outputs, result.ledger, float(getattr(result, "toth_delta_eq_s", result.ledger.toth_delta_eq_s) or 0.0)


def assert_unitop_fail_closed(adapter: UnitOpConformanceAdapter) -> dict[str, bool]:
    owner_q = TrackedQuantity(
        1.0, "arb", "owner_state", MixingRule.NOT_MIXABLE,
        TrackedTransportPolicy.OWNER_MUST_TRANSFORM, "conformance-owner",
    )
    try:
        adapter.solve(_base_stream(tracked=("owner_state", owner_q)), tracked_transformers=None, extension_transformers=None)
    except TrackedQuantityTransportError:
        tracked_owner_ok = True
    else:
        raise AssertionError("UnitOp did not fail closed for OWNER_MUST_TRANSFORM tracked quantity.")

    extension = ExtensionState(
        ExtensionSpec("conformance:owner-state", "conformance-owner", ExtensionTransportPolicy.OWNER_MUST_TRANSFORM),
        FrozenDict({"state": 1.0}),
    )
    try:
        adapter.solve(_base_stream(extension=extension), tracked_transformers=None, extension_transformers=None)
    except ExtensionTransportError:
        extension_owner_ok = True
    else:
        raise AssertionError("UnitOp did not fail closed for OWNER_MUST_TRANSFORM extension.")

    conserved = TrackedQuantity(
        10.0, "mg/L", "conserved_fixture", MixingRule.FLOW_WEIGHTED,
        TrackedTransportPolicy.CONSERVED,
    )
    feed = _base_stream(tracked=("conserved_state", conserved))
    outputs, ledger, toth_delta = _extract(
        adapter.solve(feed, tracked_transformers={}, extension_transformers={})
    )
    for output in outputs:
        quantity = output.tracked("conserved_state")
        if quantity is None or quantity.transport_policy is not TrackedTransportPolicy.CONSERVED:
            raise AssertionError("UnitOp dropped or reclassified a CONSERVED tracked quantity.")
    MassLedger.from_streams(
        "unitop-conformance-independent", "unitop-conformance", [feed], list(outputs),
        toth_delta_eq_s=toth_delta,
    ).assert_closed()
    ledger.assert_closed()

    selective_feed = _base_stream()
    fractions = {
        "a": {"h2o": 0.8, "sodium": 0.7, "chloride": 0.7},
        "b": {"h2o": 0.2, "sodium": 0.3, "chloride": 0.3},
    }
    daughter_flows = {"a": 0.8, "b": 0.2}
    if not hasattr(adapter, "solve_selective_split"):
        raise AssertionError("UnitOp conformance adapter must expose solve_selective_split().")
    split_outputs, split_ledger, _ = _extract(
        adapter.solve_selective_split(
            selective_feed, fractions, composition_preserving=False,
            daughter_aqueous_volume_flow_m3_s=daughter_flows,
        )
    )
    if any(stream.chemistry_certificate is not None for stream in split_outputs):
        raise AssertionError("UnitOp selective split rebound a ChemistryCertificate.")
    MassLedger.from_streams(
        "unitop-selective-independent", "unitop-selective", [selective_feed], list(split_outputs)
    ).assert_closed()
    split_ledger.assert_closed()

    bad = MassLedgerEntry(
        "calcium", component_in_kg_s=1.0, component_out_kg_s=1.0,
        transferred_to_solid_kg_s=0.1, explicit_solid_outlet=True,
    )
    try:
        bad.assert_convention()
    except LedgerConventionError:
        outlet_ok = True
    else:
        raise AssertionError("Explicit solid outlet double-count convention was not enforced.")

    return {
        "tracked_owner_must_transform": tracked_owner_ok,
        "extension_owner_must_transform": extension_owner_ok,
        "conserved_tracked_preserved": True,
        "mass_and_toth_closed": True,
        "selective_split_certificate_invalidated": True,
        "explicit_outlet_double_count_rejected": outlet_ok,
    }


# Keep the audited v0.5 support types available, but expose v0.6 transport,
# chemistry certificate, cache, mixer/splitter and conformance as canonical.
__all__ = [name for name in globals() if not name.startswith("_") and name not in {"Any", "Mapping", "Protocol", "field"}]
