"""Shared WaterStream v0.5 audit candidate.

v0.5 responds to the fourth Total Water Balance audit attack and consolidates the current contract into one module. It remains pre-v1.0 until the final audit gate passes.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field, replace
from enum import Enum
from math import isfinite
from typing import Any, Callable, Iterable, Protocol, Sequence
import hashlib
import json
import re

SCHEMA_VERSION = "0.5.0"
WATERSTREAM_SCHEMA_ID = "twds.water-stream"
RAW_ANALYSIS_SCHEMA_ID = "twds.raw-water-analysis"
CHEMISTRY_CERTIFICATE_SCHEMA_ID = "twds.chemistry-certificate"
MASS_LEDGER_SCHEMA_ID = "twds.mass-ledger"
H2O_MOLAR_MASS_G_MOL = 18.01528

class WaterStreamError(ValueError): pass
class ChargeResidualError(WaterStreamError): pass
class ChemistryCertificateError(WaterStreamError): pass
class UncertifiedChemistryError(ChemistryCertificateError): pass
class NonVolumetricFlowError(WaterStreamError): pass
class MixedPhaseThermalError(WaterStreamError): pass
class SelectiveSplitError(WaterStreamError): pass
class ExtensionTransportError(WaterStreamError): pass
class TrackedQuantityTransportError(WaterStreamError): pass
class MassLedgerClosureError(WaterStreamError): pass
class LedgerConventionError(WaterStreamError): pass
class UnreconciledAnalysisError(WaterStreamError): pass

class FrozenDict(Mapping[str, Any]):
    __slots__ = ("_items", "_index")
    def __init__(self, values: Mapping[str, Any] | None = None):
        pairs = [(str(k), freeze(v)) for k, v in (values or {}).items()]
        pairs.sort(key=lambda item: item[0]); self._items = tuple(pairs); self._index = dict(self._items)
    def __getitem__(self, key: str) -> Any: return self._index[key]
    def __iter__(self) -> Iterator[str]: return (key for key, _ in self._items)
    def __len__(self) -> int: return len(self._items)
    def __hash__(self) -> int: return hash(self._items)
    def to_dict(self) -> dict[str, Any]: return {k: thaw(v) for k, v in self._items}

def freeze(value: Any) -> Any:
    if isinstance(value, FrozenDict): return value
    if isinstance(value, Mapping): return FrozenDict(value)
    if isinstance(value, (list, tuple)): return tuple(freeze(x) for x in value)
    if isinstance(value, set): return tuple(sorted((freeze(x) for x in value), key=repr))
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    raise TypeError(f"Value of type {type(value).__name__} is not JSON-freezable.")

def thaw(value: Any) -> Any:
    if isinstance(value, FrozenDict): return value.to_dict()
    if isinstance(value, tuple): return [thaw(x) for x in value]
    return value

def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(thaw(freeze(payload)), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def content_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()

def _num(value: Any, name: str) -> float:
    try: result = float(value)
    except (TypeError, ValueError) as exc: raise WaterStreamError(f"{name} must be numeric.") from exc
    if not isfinite(result): raise WaterStreamError(f"{name} must be finite.")
    return result

def _unknown(payload: Mapping[str, Any], known: set[str]) -> FrozenDict: return FrozenDict({k: v for k, v in payload.items() if k not in known})
def _merge(known: dict[str, Any], unknown: FrozenDict) -> dict[str, Any]: out = unknown.to_dict(); out.update(known); return out

class QuantityType(str, Enum):
    FIXED_ION_TOTAL = "fixed_ion_total"; ANALYTICAL_FAMILY_TOTAL = "analytical_family_total"; DERIVED_EQUILIBRIUM_SPECIES = "derived_equilibrium_species"; NEUTRAL_ANALYTICAL_TOTAL = "neutral_analytical_total"
class TransportRole(str, Enum):
    AUTHORITATIVE_TOTAL = "authoritative_total"; DERIVED_ONLY = "derived_only"
@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    canonical_id: str; display_name: str; charge: int | None; molar_mass_g_mol: float | None; quantity_type: QuantityType; transport_role: TransportRole; aliases: tuple[str, ...] = ()
def _norm_alias(value: str) -> str: return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())
_COMPONENTS = (
    ComponentDefinition("h2o","Water (H2O)",0,H2O_MOLAR_MASS_G_MOL,QuantityType.NEUTRAL_ANALYTICAL_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("H2O","water","solvent_water")),
    ComponentDefinition("sodium","Sodium",1,22.989769,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("Na","Na+","ion_sodium")),
    ComponentDefinition("potassium","Potassium",1,39.0983,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("K","K+","ion_potassium")),
    ComponentDefinition("calcium","Calcium",2,40.078,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("Ca","Ca2+","Ca+2","ion_calcium")),
    ComponentDefinition("magnesium","Magnesium",2,24.305,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("Mg","Mg2+","Mg+2","ion_magnesium")),
    ComponentDefinition("strontium","Strontium",2,87.62,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("Sr","Sr2+","Sr+2","ion_strontium")),
    ComponentDefinition("barium","Barium",2,137.327,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("Ba","Ba2+","Ba+2","ion_barium")),
    ComponentDefinition("chloride","Chloride",-1,35.453,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("Cl","Cl-","ion_chloride")),
    ComponentDefinition("sulfate","Sulfate total",-2,96.06,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("SO4","SO4-2","SO4--","ion_sulfate")),
    ComponentDefinition("nitrate","Nitrate",-1,62.0049,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("NO3","NO3-","ion_nitrate")),
    ComponentDefinition("fluoride","Fluoride",-1,18.998403,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("F","F-","ion_fluoride")),
    ComponentDefinition("bromide","Bromide",-1,79.904,QuantityType.FIXED_ION_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("Br","Br-","ion_bromide")),
    ComponentDefinition("total_inorganic_carbon","Total inorganic carbon",None,12.0107,QuantityType.ANALYTICAL_FAMILY_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("TIC","CT","inorganic_carbon_total")),
    ComponentDefinition("total_ammonia","Total ammonia",None,14.0067,QuantityType.ANALYTICAL_FAMILY_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("TAN","NHx","total_ammoniacal_nitrogen")),
    ComponentDefinition("total_phosphate","Total phosphate",None,30.973762,QuantityType.ANALYTICAL_FAMILY_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("TP_inorganic","phosphate_total")),
    ComponentDefinition("total_boron","Total boron",None,10.81,QuantityType.NEUTRAL_ANALYTICAL_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("B","boron_total","ion_boron")),
    ComponentDefinition("total_silica","Total silica",None,60.0843,QuantityType.NEUTRAL_ANALYTICAL_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("SiO2","silica_total","ion_silica")),
    ComponentDefinition("total_iron","Total iron",None,55.845,QuantityType.ANALYTICAL_FAMILY_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("Fe_total","iron_total")),
    ComponentDefinition("total_manganese","Total manganese",None,54.938044,QuantityType.ANALYTICAL_FAMILY_TOTAL,TransportRole.AUTHORITATIVE_TOTAL,("Mn_total","manganese_total")),
    ComponentDefinition("bicarbonate","Bicarbonate",-1,61.0168,QuantityType.DERIVED_EQUILIBRIUM_SPECIES,TransportRole.DERIVED_ONLY,("HCO3","HCO3-","ion_bicarbonate")),
    ComponentDefinition("carbonate","Carbonate",-2,60.0089,QuantityType.DERIVED_EQUILIBRIUM_SPECIES,TransportRole.DERIVED_ONLY,("CO3","CO3--","CO3-2","ion_carbonate")),
    ComponentDefinition("ammonium","Ammonium",1,18.03846,QuantityType.DERIVED_EQUILIBRIUM_SPECIES,TransportRole.DERIVED_ONLY,("NH4","NH4+","ion_ammonium")),
    ComponentDefinition("ammonia","Ammonia",0,17.03052,QuantityType.DERIVED_EQUILIBRIUM_SPECIES,TransportRole.DERIVED_ONLY,("NH3","ion_ammonia")),
)
class ComponentRegistry:
    def __init__(self, definitions: Iterable[ComponentDefinition] = _COMPONENTS):
        defs=tuple(definitions); self._by_id={d.canonical_id:d for d in defs}; aliases={}
        for d in defs:
            for alias in (d.canonical_id,d.display_name,*d.aliases):
                key=_norm_alias(alias); previous=aliases.get(key)
                if previous is not None and previous!=d.canonical_id: raise ValueError(f"Alias collision {alias!r}: {previous!r} vs {d.canonical_id!r}.")
                aliases[key]=d.canonical_id
        self._aliases=aliases
    def resolve(self,value:str)->str:
        key=_norm_alias(value)
        if key not in self._aliases: raise KeyError(f"Unknown Shared WaterStream component identifier/alias {value!r}.")
        return self._aliases[key]
    def get(self,value:str)->ComponentDefinition: return self._by_id[self.resolve(value)]
    @property
    def definitions(self)->tuple[ComponentDefinition,...]: return tuple(self._by_id[k] for k in sorted(self._by_id))
DEFAULT_COMPONENT_REGISTRY=ComponentRegistry()
def canonical_component_id(value:str)->str: return DEFAULT_COMPONENT_REGISTRY.resolve(value)
def validate_authoritative_component(value:str)->str:
    canonical=DEFAULT_COMPONENT_REGISTRY.resolve(value); definition=DEFAULT_COMPONENT_REGISTRY.get(canonical)
    if definition.transport_role is not TransportRole.AUTHORITATIVE_TOTAL: raise ValueError(f"{value!r} resolves to derived equilibrium species {canonical!r}; use its authoritative analytical family total.")
    return canonical

@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    source_type:str; source_id:str|None=None; application:str|None=None; process:str|None=None; engine_version:str|None=None; parent_stream_ids:tuple[str,...]=(); metadata:FrozenDict=field(default_factory=FrozenDict)
    def __post_init__(self): object.__setattr__(self,"source_type",str(self.source_type)); object.__setattr__(self,"parent_stream_ids",tuple(str(x) for x in self.parent_stream_ids)); object.__setattr__(self,"metadata",FrozenDict(self.metadata if not isinstance(self.metadata,FrozenDict) else self.metadata.to_dict()))
    def to_dict(self): return {"source_type":self.source_type,"source_id":self.source_id,"application":self.application,"process":self.process,"engine_version":self.engine_version,"parent_stream_ids":list(self.parent_stream_ids),"metadata":self.metadata.to_dict()}
    @classmethod
    def from_dict(cls,p): return cls(str(p.get("source_type") or ""),p.get("source_id"),p.get("application"),p.get("process"),p.get("engine_version"),tuple(p.get("parent_stream_ids") or ()),FrozenDict(p.get("metadata") or {}))
@dataclass(frozen=True, slots=True)
class RawMeasurement:
    measurement_id:str; original_name:str; value:float; unit:str; basis:str|None=None; canonical_component_id:str|None=None; metadata:FrozenDict=field(default_factory=FrozenDict)
    def to_dict(self): return {"measurement_id":self.measurement_id,"original_name":self.original_name,"value":self.value,"unit":self.unit,"basis":self.basis,"canonical_component_id":self.canonical_component_id,"metadata":self.metadata.to_dict()}
    @classmethod
    def from_dict(cls,p): return cls(str(p.get("measurement_id") or ""),str(p.get("original_name") or ""),_num(p.get("value",0),"raw measurement"),str(p.get("unit") or ""),p.get("basis"),p.get("canonical_component_id"),FrozenDict(p.get("metadata") or {}))
@dataclass(frozen=True, slots=True)
class ReconciliationDecision:
    status:str="unresolved"; method:str|None=None; adjustments:FrozenDict=field(default_factory=FrozenDict); rationale:str|None=None
    @property
    def is_resolved(self): return str(self.status).lower() in {"accepted","adjusted","reconciled"}
    def to_dict(self): return {"status":self.status,"method":self.method,"adjustments":self.adjustments.to_dict(),"rationale":self.rationale}
    @classmethod
    def from_dict(cls,p): return cls(str(p.get("status") or "unresolved"),p.get("method"),FrozenDict(p.get("adjustments") or {}),p.get("rationale"))
@dataclass(frozen=True, slots=True)
class RawWaterAnalysis:
    analysis_id:str; measurements:tuple[RawMeasurement,...]; analytical_charge_imbalance_pct:float|None=None; analytical_charge_residual_meq_l:float|None=None; reconciliation:ReconciliationDecision=field(default_factory=ReconciliationDecision); provenance:tuple[ProvenanceRecord,...]=(); metadata:FrozenDict=field(default_factory=FrozenDict); schema_version:str=SCHEMA_VERSION
    def __post_init__(self):
        if self.schema_version!=SCHEMA_VERSION: raise WaterStreamError(f"RawWaterAnalysis version {self.schema_version!r} is not v0.5.")
        object.__setattr__(self,"measurements",tuple(x if isinstance(x,RawMeasurement) else RawMeasurement.from_dict(x) for x in self.measurements)); object.__setattr__(self,"provenance",tuple(x if isinstance(x,ProvenanceRecord) else ProvenanceRecord.from_dict(x) for x in self.provenance))
    def assert_reconciled(self):
        if not self.reconciliation.is_resolved: raise UnreconciledAnalysisError(f"RawWaterAnalysis {self.analysis_id!r} is unresolved.")
    def to_dict(self): return {"schema":RAW_ANALYSIS_SCHEMA_ID,"version":SCHEMA_VERSION,"analysis_id":self.analysis_id,"measurements":[x.to_dict() for x in self.measurements],"analytical_charge_imbalance_pct":self.analytical_charge_imbalance_pct,"analytical_charge_residual_meq_l":self.analytical_charge_residual_meq_l,"reconciliation":self.reconciliation.to_dict(),"provenance":[x.to_dict() for x in self.provenance],"metadata":self.metadata.to_dict()}
    @classmethod
    def from_dict(cls,p):
        if p.get("schema")!=RAW_ANALYSIS_SCHEMA_ID or str(p.get("version"))!=SCHEMA_VERSION: raise WaterStreamError("Unsupported RawWaterAnalysis schema/version.")
        return cls(str(p.get("analysis_id") or ""),tuple(RawMeasurement.from_dict(x) for x in (p.get("measurements") or ())),p.get("analytical_charge_imbalance_pct"),p.get("analytical_charge_residual_meq_l"),ReconciliationDecision.from_dict(p.get("reconciliation") or {}),tuple(ProvenanceRecord.from_dict(x) for x in (p.get("provenance") or ())),FrozenDict(p.get("metadata") or {}))

class ExtensionTransportPolicy(str,Enum):
    PASS_THROUGH="PASS_THROUGH"; FLOW_PROPORTIONAL="FLOW_PROPORTIONAL"; OWNER_MUST_TRANSFORM="OWNER_MUST_TRANSFORM"; DROP_AT_BOUNDARY="DROP_AT_BOUNDARY"; NONTRANSPORTABLE="NONTRANSPORTABLE"
@dataclass(frozen=True, slots=True)
class ExtensionSpec:
    namespace:str; owner:str; default_policy:ExtensionTransportPolicy; operation_policies:FrozenDict=field(default_factory=FrozenDict); flow_proportional_fields:tuple[str,...]=()
    def __post_init__(self):
        if ":" not in self.namespace: raise WaterStreamError("Extension namespace must be namespaced, e.g. 'bio:asm'.")
        object.__setattr__(self,"default_policy",self.default_policy if isinstance(self.default_policy,ExtensionTransportPolicy) else ExtensionTransportPolicy(str(self.default_policy))); object.__setattr__(self,"operation_policies",FrozenDict(self.operation_policies if not isinstance(self.operation_policies,FrozenDict) else self.operation_policies.to_dict())); object.__setattr__(self,"flow_proportional_fields",tuple(str(x) for x in self.flow_proportional_fields))
    def policy_for(self,operation:str): raw=self.operation_policies.get(operation); return self.default_policy if raw is None else ExtensionTransportPolicy(str(raw))
    def to_dict(self): return {"namespace":self.namespace,"owner":self.owner,"default_policy":self.default_policy.value,"operation_policies":self.operation_policies.to_dict(),"flow_proportional_fields":list(self.flow_proportional_fields)}
    @classmethod
    def from_dict(cls,p): return cls(str(p.get("namespace") or ""),str(p.get("owner") or ""),ExtensionTransportPolicy(str(p.get("default_policy") or ExtensionTransportPolicy.NONTRANSPORTABLE.value)),FrozenDict(p.get("operation_policies") or {}),tuple(p.get("flow_proportional_fields") or ()))
@dataclass(frozen=True, slots=True)
class ExtensionState:
    spec:ExtensionSpec; payload:FrozenDict
    def __post_init__(self):
        if not isinstance(self.spec,ExtensionSpec): object.__setattr__(self,"spec",ExtensionSpec.from_dict(self.spec))
        object.__setattr__(self,"payload",FrozenDict(self.payload if not isinstance(self.payload,FrozenDict) else self.payload.to_dict()))
    @property
    def namespace(self): return self.spec.namespace
    def to_dict(self): return {"spec":self.spec.to_dict(),"payload":self.payload.to_dict()}
    @classmethod
    def from_dict(cls,p): return cls(ExtensionSpec.from_dict(p.get("spec") or {}),FrozenDict(p.get("payload") or {}))
ExtensionTransformer=Callable[[tuple[ExtensionState,...],str,FrozenDict],ExtensionState|None]
def _transform_extension(states:tuple[ExtensionState,...],*,operation:str,context:Mapping[str,Any],transformer:ExtensionTransformer|None):
    if not states:return None
    policies={s.spec.policy_for(operation) for s in states}
    if len(policies)!=1: raise ExtensionTransportError(f"Extension {states[0].namespace!r} declares inconsistent policies.")
    policy=next(iter(policies)); ns=states[0].namespace; ctx=FrozenDict(context)
    if policy is ExtensionTransportPolicy.DROP_AT_BOUNDARY:return None
    if policy is ExtensionTransportPolicy.NONTRANSPORTABLE: raise ExtensionTransportError(f"Extension {ns!r} is NONTRANSPORTABLE for {operation!r}.")
    if policy is ExtensionTransportPolicy.OWNER_MUST_TRANSFORM:
        if transformer is None: raise ExtensionTransportError(f"Extension {ns!r} requires its owner to transform state for operation {operation!r}.")
        return transformer(states,operation,ctx)
    if transformer is not None:return transformer(states,operation,ctx)
    if policy is ExtensionTransportPolicy.PASS_THROUGH:
        first=states[0].to_dict()
        if any(s.to_dict()!=first for s in states[1:]): raise ExtensionTransportError(f"PASS_THROUGH extension {ns!r} differs between inputs.")
        return states[0]
    if policy is ExtensionTransportPolicy.FLOW_PROPORTIONAL:
        fields=states[0].spec.flow_proportional_fields
        if not fields: raise ExtensionTransportError(f"FLOW_PROPORTIONAL extension {ns!r} requires declared fields or owner transform.")
        payload=states[0].payload.to_dict()
        if operation=="split":
            f=float(ctx.get("fraction",ctx.get("flow_fraction",1.0)))
            for key in fields: payload[key]=float(payload[key])*f
            return ExtensionState(states[0].spec,FrozenDict(payload))
        if operation=="mix":
            for key in fields: payload[key]=sum(float(s.payload[key]) for s in states)
            return ExtensionState(states[0].spec,FrozenDict(payload))
    raise ExtensionTransportError(f"No built-in extension algebra for {ns!r} operation {operation!r}.")

class MixingRule(str,Enum): EXTENSIVE_SUM="EXTENSIVE_SUM"; FLOW_WEIGHTED="FLOW_WEIGHTED"; NOT_MIXABLE="NOT_MIXABLE"
class TrackedTransportPolicy(str,Enum): CONSERVED="CONSERVED"; OWNER_MUST_TRANSFORM="OWNER_MUST_TRANSFORM"; UNDEFINED_OUTSIDE_MIXER="UNDEFINED_OUTSIDE_MIXER"
@dataclass(frozen=True, slots=True)
class TrackedQuantity:
    value:float|None; unit:str; dimension:str; mixing_rule:MixingRule; transport_policy:TrackedTransportPolicy=TrackedTransportPolicy.CONSERVED; owner:str|None=None; available:bool=True; diagnostic_reason:str|None=None; metadata:FrozenDict=field(default_factory=FrozenDict)
    def __post_init__(self):
        object.__setattr__(self,"mixing_rule",self.mixing_rule if isinstance(self.mixing_rule,MixingRule) else MixingRule(str(self.mixing_rule))); object.__setattr__(self,"transport_policy",self.transport_policy if isinstance(self.transport_policy,TrackedTransportPolicy) else TrackedTransportPolicy(str(self.transport_policy)))
        if self.transport_policy is TrackedTransportPolicy.OWNER_MUST_TRANSFORM and not self.owner: raise WaterStreamError("OWNER_MUST_TRANSFORM tracked quantity requires owner.")
        if self.available:
            if self.value is None: raise WaterStreamError("Available TrackedQuantity requires numeric value.")
            object.__setattr__(self,"value",_num(self.value,"tracked value"))
        else:
            object.__setattr__(self,"value",None)
            if not self.diagnostic_reason: raise WaterStreamError("Unavailable TrackedQuantity requires diagnostic reason.")
    @classmethod
    def unavailable(cls,*,unit,dimension,mixing_rule,transport_policy,owner,reason): return cls(None,unit,dimension,mixing_rule,transport_policy,owner,False,reason)
    def to_dict(self): return {"value":self.value,"unit":self.unit,"dimension":self.dimension,"mixing_rule":self.mixing_rule.value,"transport_policy":self.transport_policy.value,"owner":self.owner,"available":self.available,"diagnostic_reason":self.diagnostic_reason,"metadata":self.metadata.to_dict()}
    @classmethod
    def from_dict(cls,p): return cls(p.get("value"),str(p.get("unit") or ""),str(p.get("dimension") or ""),MixingRule(str(p.get("mixing_rule") or MixingRule.NOT_MIXABLE.value)),TrackedTransportPolicy(str(p.get("transport_policy") or TrackedTransportPolicy.CONSERVED.value)),p.get("owner"),bool(p.get("available",True)),p.get("diagnostic_reason"),FrozenDict(p.get("metadata") or {}))

class StreamPhase(str,Enum): AQUEOUS="AQUEOUS"; SOLID="SOLID"; GAS="GAS"; MIXED="MIXED"
@dataclass(frozen=True, slots=True)
class PhaseInventoryItem:
    phase:StreamPhase; identity:str|None; component_totals_mol_s:FrozenDict; metadata:FrozenDict=field(default_factory=FrozenDict)
    def __post_init__(self):
        phase=self.phase if isinstance(self.phase,StreamPhase) else StreamPhase(str(self.phase)); object.__setattr__(self,"phase",phase); components={}; raw=self.component_totals_mol_s if isinstance(self.component_totals_mol_s,FrozenDict) else FrozenDict(self.component_totals_mol_s)
        for key,value in raw.items():
            canonical=validate_authoritative_component(key); amount=_num(value,f"phase component {canonical}")
            if amount<0: raise WaterStreamError("Phase component totals cannot be negative.")
            components[canonical]=components.get(canonical,0.0)+amount
        object.__setattr__(self,"component_totals_mol_s",FrozenDict(components)); object.__setattr__(self,"metadata",FrozenDict(self.metadata if not isinstance(self.metadata,FrozenDict) else self.metadata.to_dict()))
    def to_dict(self): return {"phase":self.phase.value,"identity":self.identity,"component_totals_mol_s":self.component_totals_mol_s.to_dict(),"metadata":self.metadata.to_dict()}
    @classmethod
    def from_dict(cls,p): return cls(StreamPhase(str(p.get("phase") or StreamPhase.AQUEOUS.value)),p.get("identity"),FrozenDict(p.get("component_totals_mol_s") or {}),FrozenDict(p.get("metadata") or {}))
@dataclass(frozen=True, slots=True)
class StreamDiagnostics:
    invariant_residuals:FrozenDict=field(default_factory=FrozenDict); warnings:tuple[str,...]=()
    def to_dict(self): return {"invariant_residuals":self.invariant_residuals.to_dict(),"warnings":list(self.warnings)}
    @classmethod
    def from_dict(cls,p): return cls(FrozenDict(p.get("invariant_residuals") or {}),tuple(p.get("warnings") or ()))

@dataclass(frozen=True, slots=True)
class ChemistryCertificate:
    state_hash: str
    residual_charge_eq_s: float
    ionic_strength_mol_kg: float
    solvent_water_kg_s: float
    density_kg_m3: float
    engine_version: str
    solution_mass_kg_s: float
    metadata: FrozenDict = field(default_factory=FrozenDict)
    def __post_init__(self):
        state_hash=str(self.state_hash)
        if len(state_hash)!=64 or any(ch not in "0123456789abcdefABCDEF" for ch in state_hash):
            raise ChemistryCertificateError("state_hash must be 64 hexadecimal SHA-256 characters.")
        object.__setattr__(self,"state_hash",state_hash.lower())
        for name in ("residual_charge_eq_s","ionic_strength_mol_kg","solvent_water_kg_s","density_kg_m3","solution_mass_kg_s"):
            object.__setattr__(self,name,_num(getattr(self,name),name))
        if self.ionic_strength_mol_kg<0 or self.solvent_water_kg_s<0 or self.density_kg_m3<=0 or self.solution_mass_kg_s<self.solvent_water_kg_s:
            raise ChemistryCertificateError("Invalid ChemistryCertificate physical values.")
        engine=str(self.engine_version).strip()
        if not engine: raise ChemistryCertificateError("engine_version is required for certificate provenance.")
        object.__setattr__(self,"engine_version",engine)
        object.__setattr__(self,"metadata",self.metadata if isinstance(self.metadata,FrozenDict) else FrozenDict(self.metadata))
    def to_dict(self):
        return {"schema":CHEMISTRY_CERTIFICATE_SCHEMA_ID,"version":SCHEMA_VERSION,"state_hash":self.state_hash,
                "residual_charge_eq_s":self.residual_charge_eq_s,"ionic_strength_mol_kg":self.ionic_strength_mol_kg,
                "solvent_water_kg_s":self.solvent_water_kg_s,"density_kg_m3":self.density_kg_m3,
                "engine_version":self.engine_version,"solution_mass_kg_s":self.solution_mass_kg_s,"metadata":self.metadata.to_dict()}
    @classmethod
    def from_dict(cls,p):
        if p.get("schema")!=CHEMISTRY_CERTIFICATE_SCHEMA_ID or str(p.get("version"))!=SCHEMA_VERSION:
            raise ChemistryCertificateError("Unsupported ChemistryCertificate schema/version.")
        return cls(str(p.get("state_hash") or ""),p.get("residual_charge_eq_s",0),p.get("ionic_strength_mol_kg",0),
                   p.get("solvent_water_kg_s",0),p.get("density_kg_m3",0),str(p.get("engine_version") or ""),
                   p.get("solution_mass_kg_s",0),FrozenDict(p.get("metadata") or {}))

@dataclass(frozen=True, slots=True)
class ChargeValidationPolicy:
    abs_tolerance_eq_s: float=1e-9
    relative_tolerance: float=1e-8
    def tolerance_for(self,s): return max(_num(self.abs_tolerance_eq_s,"absolute tolerance"),_num(self.relative_tolerance,"relative tolerance")*s.charge_throughput_eq_s)
    def validate(self,s):
        c=s.require_valid_chemistry_certificate(); t=self.tolerance_for(s)
        if abs(c.residual_charge_eq_s)>t: raise ChargeResidualError(f"Charge residual {c.residual_charge_eq_s:.6g} eq/s exceeds {t:.6g} eq/s.")
        return t
DEFAULT_CHARGE_VALIDATION_POLICY=ChargeValidationPolicy()

@dataclass(frozen=True, slots=True)
class WaterStream:
    stream_id:str
    temperature_c:float
    pressure_bar:float
    component_totals_mol_s:FrozenDict
    toth_eq_s:float
    phase:StreamPhase=StreamPhase.AQUEOUS
    phase_inventory:tuple[PhaseInventoryItem,...]=()
    chemistry_policy:FrozenDict=field(default_factory=FrozenDict)
    tracked_quantities:FrozenDict=field(default_factory=FrozenDict)
    extensions:FrozenDict=field(default_factory=FrozenDict)
    diagnostics:StreamDiagnostics=field(default_factory=StreamDiagnostics)
    chemistry_certificate:ChemistryCertificate|None=None
    provenance:tuple[ProvenanceRecord,...]=()
    unknown_fields:FrozenDict=field(default_factory=FrozenDict)
    def __post_init__(self):
        if not str(self.stream_id).strip(): raise WaterStreamError("stream_id is required.")
        object.__setattr__(self,"temperature_c",_num(self.temperature_c,"temperature_c")); object.__setattr__(self,"pressure_bar",_num(self.pressure_bar,"pressure_bar")); object.__setattr__(self,"toth_eq_s",_num(self.toth_eq_s,"toth_eq_s"))
        phase=self.phase if isinstance(self.phase,StreamPhase) else StreamPhase(str(self.phase)); object.__setattr__(self,"phase",phase)
        comps={}
        raw=self.component_totals_mol_s if isinstance(self.component_totals_mol_s,FrozenDict) else FrozenDict(self.component_totals_mol_s)
        for key,value in raw.items():
            try: canonical=validate_authoritative_component(key)
            except (KeyError,ValueError) as exc: raise WaterStreamError(str(exc)) from exc
            amount=_num(value,f"component {canonical}")
            if amount<0: raise WaterStreamError("Component totals cannot be negative.")
            comps[canonical]=comps.get(canonical,0.0)+amount
        if phase is StreamPhase.AQUEOUS and comps.get("h2o",0)<=0: raise WaterStreamError("AQUEOUS stream requires positive H2O inventory.")
        object.__setattr__(self,"component_totals_mol_s",FrozenDict(comps))
        inventory=tuple(x if isinstance(x,PhaseInventoryItem) else PhaseInventoryItem.from_dict(x) for x in self.phase_inventory)
        if not inventory: inventory=(PhaseInventoryItem(phase,None,FrozenDict(comps)),)
        phases={x.phase for x in inventory if any(float(v)>0 for v in x.component_totals_mol_s.values())}
        if phase is StreamPhase.MIXED and len(phases)<2: raise WaterStreamError("MIXED stream phase_inventory must contain at least two phases.")
        if phase is not StreamPhase.MIXED and any(p is not phase for p in phases): raise WaterStreamError(f"{phase.value} stream phase_inventory contains another phase.")
        sums={}
        for item in inventory:
            for key,value in item.component_totals_mol_s.items(): sums[key]=sums.get(key,0.0)+float(value)
        for key in set(sums)|set(comps):
            expected=float(comps.get(key,0)); actual=float(sums.get(key,0))
            if abs(actual-expected)>max(1e-12,1e-10*max(abs(expected),1.0)):
                raise WaterStreamError(f"phase_inventory does not close to stream component {key!r}: {actual} vs {expected}.")
        object.__setattr__(self,"phase_inventory",inventory)
        object.__setattr__(self,"chemistry_policy",self.chemistry_policy if isinstance(self.chemistry_policy,FrozenDict) else FrozenDict(self.chemistry_policy))
        tracked={str(k):(v if isinstance(v,TrackedQuantity) else TrackedQuantity.from_dict(thaw(v))) for k,v in (self.tracked_quantities if isinstance(self.tracked_quantities,FrozenDict) else FrozenDict(self.tracked_quantities)).items()}
        object.__setattr__(self,"tracked_quantities",FrozenDict({k:v.to_dict() for k,v in tracked.items()}))
        extensions={}
        for key,value in (self.extensions if isinstance(self.extensions,FrozenDict) else FrozenDict(self.extensions)).items():
            state=value if isinstance(value,ExtensionState) else ExtensionState.from_dict(thaw(value))
            if key!=state.namespace: raise WaterStreamError("Extension mapping key does not match namespace.")
            extensions[key]=state
        object.__setattr__(self,"extensions",FrozenDict({k:v.to_dict() for k,v in extensions.items()}))
        object.__setattr__(self,"diagnostics",self.diagnostics if isinstance(self.diagnostics,StreamDiagnostics) else StreamDiagnostics.from_dict(self.diagnostics))
        object.__setattr__(self,"provenance",tuple(x if isinstance(x,ProvenanceRecord) else ProvenanceRecord.from_dict(x) for x in self.provenance))
        object.__setattr__(self,"unknown_fields",self.unknown_fields if isinstance(self.unknown_fields,FrozenDict) else FrozenDict(self.unknown_fields))
        cert=self.chemistry_certificate if isinstance(self.chemistry_certificate,(ChemistryCertificate,type(None))) else ChemistryCertificate.from_dict(self.chemistry_certificate)
        object.__setattr__(self,"chemistry_certificate",cert)
        if cert is not None:self._validate_certificate(cert)
    def _state_payload(self):
        return {"schema":WATERSTREAM_SCHEMA_ID,"version":SCHEMA_VERSION,"temperature_c":self.temperature_c,"pressure_bar":self.pressure_bar,
                "component_totals_mol_s":self.component_totals_mol_s.to_dict(),"toth_eq_s":self.toth_eq_s,"phase":self.phase.value,
                "phase_inventory":[x.to_dict() for x in self.phase_inventory],"chemistry_policy":self.chemistry_policy.to_dict()}
    @property
    def state_hash(self): return content_hash(self._state_payload())
    @property
    def content_hash(self): return content_hash(self.to_dict())
    @property
    def water_mol_s(self): return float(self.component_totals_mol_s.get("h2o",0))
    @property
    def solvent_water_kg_s_from_components(self): return self.water_mol_s*H2O_MOLAR_MASS_G_MOL/1000.0
    @property
    def charge_throughput_eq_s(self): return sum(abs(DEFAULT_COMPONENT_REGISTRY.get(k).charge or 0)*float(v) for k,v in self.component_totals_mol_s.items())
    @property
    def fixed_charge_residual_eq_s(self): return sum((DEFAULT_COMPONENT_REGISTRY.get(k).charge or 0)*float(v) for k,v in self.component_totals_mol_s.items())
    def _validate_certificate(self,c):
        if c.state_hash!=self.state_hash: raise ChemistryCertificateError("Certificate state_hash does not match stream state_hash.")
        expected_water=self.solvent_water_kg_s_from_components; wt=max(1e-12,1e-12*max(abs(expected_water),1.0))
        if abs(c.solvent_water_kg_s-expected_water)>wt: raise ChemistryCertificateError("Certificate solvent_water_kg_s disagrees with H2O component inventory.")
        expected_residual=self.fixed_charge_residual_eq_s; rt=max(1e-12,1e-12*max(self.charge_throughput_eq_s,1.0))
        if abs(c.residual_charge_eq_s-expected_residual)>rt:
            raise ChemistryCertificateError(f"Certificate residual_charge_eq_s {c.residual_charge_eq_s:.12g} disagrees with independently recomputed stream charge {expected_residual:.12g} eq/s.")
    def require_valid_chemistry_certificate(self):
        if self.chemistry_certificate is None: raise UncertifiedChemistryError("ChemistryCertificate invalid/missing; recertification required.")
        self._validate_certificate(self.chemistry_certificate); return self.chemistry_certificate
    @property
    def flow_m3_s(self):
        if self.phase is not StreamPhase.AQUEOUS: raise NonVolumetricFlowError(f"flow_m3_s is unavailable for phase {self.phase.value}.")
        c=self.require_valid_chemistry_certificate(); return c.solution_mass_kg_s/c.density_kg_m3
    @property
    def ionic_strength_mol_kg(self): return self.require_valid_chemistry_certificate().ionic_strength_mol_kg
    def with_chemistry_certificate(self,c): return replace(self,chemistry_certificate=c)
    def tracked(self,key):
        raw=self.tracked_quantities.get(str(key)); return None if raw is None else (raw if isinstance(raw,TrackedQuantity) else TrackedQuantity.from_dict(thaw(raw)))
    def extension(self,namespace):
        raw=self.extensions.get(str(namespace)); return None if raw is None else (raw if isinstance(raw,ExtensionState) else ExtensionState.from_dict(thaw(raw)))
    def to_dict(self):
        out={"schema":WATERSTREAM_SCHEMA_ID,"version":SCHEMA_VERSION,"stream_id":self.stream_id,"temperature_c":self.temperature_c,"pressure_bar":self.pressure_bar,
             "component_totals_mol_s":self.component_totals_mol_s.to_dict(),"toth_eq_s":self.toth_eq_s,"phase":self.phase.value,
             "phase_inventory":[x.to_dict() for x in self.phase_inventory],"chemistry_policy":self.chemistry_policy.to_dict(),"tracked_quantities":self.tracked_quantities.to_dict(),
             "extensions":self.extensions.to_dict(),"diagnostics":self.diagnostics.to_dict(),"chemistry_certificate":None if self.chemistry_certificate is None else self.chemistry_certificate.to_dict(),
             "provenance":[x.to_dict() for x in self.provenance]}
        out.update(self.unknown_fields.to_dict()); return out
    @classmethod
    def from_dict(cls,p):
        if p.get("schema")!=WATERSTREAM_SCHEMA_ID or str(p.get("version"))!=SCHEMA_VERSION: raise WaterStreamError("Unsupported WaterStream schema/version.")
        forbidden={k for k in p if str(k).lower() in {"ph","p_h","hydrogen_activity","flow_m3_s","charge_tolerance_eq_s","mineral_identity"}}
        if forbidden: raise WaterStreamError(f"Independent derived/legacy fields forbidden: {sorted(forbidden)}")
        known={"schema","version","stream_id","temperature_c","pressure_bar","component_totals_mol_s","toth_eq_s","phase","phase_inventory","chemistry_policy","tracked_quantities","extensions","diagnostics","chemistry_certificate","provenance"}
        return cls(str(p.get("stream_id") or ""),p.get("temperature_c",25),p.get("pressure_bar",1.01325),FrozenDict(p.get("component_totals_mol_s") or {}),p.get("toth_eq_s",0),
                   StreamPhase(str(p.get("phase") or StreamPhase.AQUEOUS.value)),tuple(PhaseInventoryItem.from_dict(x) for x in (p.get("phase_inventory") or ())),
                   FrozenDict(p.get("chemistry_policy") or {}),FrozenDict(p.get("tracked_quantities") or {}),FrozenDict(p.get("extensions") or {}),StreamDiagnostics.from_dict(p.get("diagnostics") or {}),
                   None if p.get("chemistry_certificate") is None else ChemistryCertificate.from_dict(p["chemistry_certificate"]),tuple(ProvenanceRecord.from_dict(x) for x in (p.get("provenance") or ())),
                   FrozenDict({k:v for k,v in p.items() if k not in known}))

class ChemistryCertificateIssuer(Protocol):
    engine_version:str
    declared_tolerance:float
    def issue(self,stream:WaterStream,*,warm_start:ChemistryCertificate|None=None)->ChemistryCertificate: ...

class ChemistryCertificateCache:
    def __init__(self): self._cache:dict[tuple[str,str],ChemistryCertificate]={}
    def get(self,state_hash,engine_version=None):
        state_hash=str(state_hash)
        if engine_version is not None: return self._cache.get((state_hash,str(engine_version).strip()))
        matches=[cert for (h,_),cert in self._cache.items() if h==state_hash]
        return matches[0] if len(matches)==1 else None
    def put(self,certificate): self._cache[(certificate.state_hash,certificate.engine_version)]=certificate
    def clear(self): self._cache.clear()
    def __len__(self): return len(self._cache)

def certify_stream(stream,issuer,*,cache=None,warm_start=None):
    engine_version=str(getattr(issuer,"engine_version","")).strip()
    if not engine_version: raise ChemistryCertificateError("ChemistryCertificateIssuer.engine_version is required.")
    if cache is not None:
        cached=cache.get(stream.state_hash,engine_version)
        if cached is not None:return stream.with_chemistry_certificate(cached)
    cert=issuer.issue(stream,warm_start=warm_start)
    if cert.engine_version!=engine_version: raise ChemistryCertificateError(f"Issuer engine_version {engine_version!r} disagrees with certificate engine_version {cert.engine_version!r}.")
    certified=stream.with_chemistry_certificate(cert)
    if cache is not None:cache.put(cert)
    return certified

def _issuer_fixture(high=False):
    comps={"h2o":1000*1000/H2O_MOLAR_MASS_G_MOL,"sodium":8.0 if high else .05,"chloride":8.0 if high else .05}
    return WaterStream("issuer-fixture",25,2,FrozenDict(comps),0)

def assert_issuer_conformant(issuer):
    engine_version=str(getattr(issuer,"engine_version","")).strip()
    if not engine_version: raise AssertionError("Issuer must declare nonempty engine_version.")
    tol=_num(getattr(issuer,"declared_tolerance",None),"issuer.declared_tolerance")
    if tol<0: raise AssertionError("Issuer declared_tolerance must be nonnegative.")
    target=_issuer_fixture(True); seed_stream=_issuer_fixture(False)
    seed=issuer.issue(seed_stream,warm_start=None); seed_stream.with_chemistry_certificate(seed)
    cold1=issuer.issue(target,warm_start=None); target.with_chemistry_certificate(cold1)
    cold2=issuer.issue(target,warm_start=None); target.with_chemistry_certificate(cold2)
    for cert in (seed,cold1,cold2):
        if cert.engine_version!=engine_version: raise AssertionError("Issuer returned certificate with inconsistent engine_version.")
    if canonical_json(cold1.to_dict())!=canonical_json(cold2.to_dict()): raise AssertionError("Issuer is not deterministic for identical inputs.")
    warm=issuer.issue(target,warm_start=seed); target.with_chemistry_certificate(warm)
    if warm.engine_version!=engine_version: raise AssertionError("Warm-start certificate engine_version differs from issuer.")
    fields=("residual_charge_eq_s","ionic_strength_mol_kg","solvent_water_kg_s","density_kg_m3","solution_mass_kg_s")
    for field_name in fields:
        delta=abs(float(getattr(cold1,field_name))-float(getattr(warm,field_name)))
        if delta>tol: raise AssertionError(f"Warm-start {field_name} differs from cold by {delta:.12g}, exceeding declared tolerance {tol:.12g}.")
    return {"cold_warm_equivalent":True,"deterministic_identical_inputs":True,"residual_charge_verified":True,"solvent_water_verified":True,
            "trusted_not_independently_verified":("ionic_strength_mol_kg","density_kg_m3","solution_mass_kg_s")}

def _mix_tracked(key, rows, flows):
    values=[s.tracked(key) for s in rows]; template=next(v for v in values if v is not None)
    if any(v is None or not v.available for v in values):
        return TrackedQuantity.unavailable(unit=template.unit,dimension=template.dimension,mixing_rule=template.mixing_rule,transport_policy=template.transport_policy,owner=template.owner,reason=f"{key}: missing/unavailable mixer input.")
    if len({(v.unit,v.dimension,v.mixing_rule,v.transport_policy,v.owner) for v in values}) != 1: raise WaterStreamError(f"Tracked quantity {key!r} definitions differ.")
    if template.mixing_rule is MixingRule.NOT_MIXABLE:
        return TrackedQuantity.unavailable(unit=template.unit,dimension=template.dimension,mixing_rule=template.mixing_rule,transport_policy=template.transport_policy,owner=template.owner,reason=f"{key}: declared NOT_MIXABLE; no mixed value was fabricated.")
    if template.mixing_rule is MixingRule.EXTENSIVE_SUM: result=sum(float(v.value) for v in values)
    else:
        if flows is None: raise MixedPhaseThermalError(f"FLOW_WEIGHTED tracked quantity {key!r} unavailable for mixed/non-volumetric mixing.")
        result=sum(q*float(v.value) for q,v in zip(flows,values))/sum(flows)
    return TrackedQuantity(result,template.unit,template.dimension,template.mixing_rule,template.transport_policy,template.owner)

def _inventory_mix(rows):
    grouped={}; metadata={}
    for stream in rows:
        for item in stream.phase_inventory:
            key=(item.phase,item.identity); bucket=grouped.setdefault(key,{})
            for component,amount in item.component_totals_mol_s.items(): bucket[component]=bucket.get(component,0.0)+float(amount)
            metadata.setdefault(key,item.metadata)
    return tuple(PhaseInventoryItem(phase,identity,FrozenDict(components),metadata[(phase,identity)]) for (phase,identity),components in sorted(grouped.items(),key=lambda x:(x[0][0].value,x[0][1] or "")) if any(v>0 for v in components.values()))

def mix_water_streams(streams,*,stream_id,output_temperature_c=None,extension_transformers=None,engine_version=None):
    rows=tuple(streams)
    if not rows: raise WaterStreamError("Mixer needs input streams.")
    policies=[s.chemistry_policy.to_dict() for s in rows]
    if any(p!=policies[0] for p in policies[1:]): raise WaterStreamError("Mixer inputs carry different chemistry_policy values; owner policy reconciliation is required.")
    all_aqueous=all(s.phase is StreamPhase.AQUEOUS for s in rows); flows=None
    if all_aqueous:
        flows=[s.flow_m3_s for s in rows]; temperature=sum(q*s.temperature_c for q,s in zip(flows,rows))/sum(flows)
    else:
        if output_temperature_c is None: raise MixedPhaseThermalError("Generic mixer refuses mixed/non-volumetric phase temperature calculation; owner must supply output_temperature_c.")
        temperature=_num(output_temperature_c,"output_temperature_c")
    components={key:sum(float(s.component_totals_mol_s.get(key,0.0)) for s in rows) for key in set().union(*(s.component_totals_mol_s.keys() for s in rows))}
    tracked={key:_mix_tracked(key,rows,flows).to_dict() for key in set().union(*(s.tracked_quantities.keys() for s in rows))}
    transformers=dict(extension_transformers or {}); extensions={}
    for namespace in set().union(*(s.extensions.keys() for s in rows)):
        states=tuple(x for x in (s.extension(namespace) for s in rows) if x is not None)
        if len(states)!=len(rows) and namespace not in transformers: raise ExtensionTransportError(f"Extension {namespace!r} missing from mixer input; owner transform is required.")
        transformed=_transform_extension(states,operation="mix",context={"input_count":len(rows)},transformer=transformers.get(namespace))
        if transformed is not None: extensions[namespace]=transformed.to_dict()
    phase=rows[0].phase if all(s.phase is rows[0].phase for s in rows) else StreamPhase.MIXED
    return WaterStream(stream_id,temperature,min(s.pressure_bar for s in rows),FrozenDict(components),sum(s.toth_eq_s for s in rows),phase,_inventory_mix(rows),FrozenDict(policies[0]),FrozenDict(tracked),FrozenDict(extensions),StreamDiagnostics(FrozenDict({"mixer_inputs":len(rows)}),("ChemistryCertificate invalidated by mixing; recertification required.",)),None,(ProvenanceRecord("mixer",stream_id,"shared-waterstream","v0.5_mix",engine_version,tuple(s.stream_id for s in rows)),))

def _normalize_selective(stream,fractions):
    children={str(child):dict(values) for child,values in fractions.items()}
    if not children: raise SelectiveSplitError("At least one split daughter is required.")
    canonical={child:{} for child in children}
    for child,values in children.items():
        for key,fraction in values.items():
            component=canonical_component_id(key)
            if component not in stream.component_totals_mol_s: raise SelectiveSplitError(f"Selective split specifies component {component!r} not present in feed.")
            value=_num(fraction,f"selective fraction {child}:{component}")
            if not 0<=value<=1: raise SelectiveSplitError("Selective split fractions must be between 0 and 1.")
            canonical[child][component]=value
    for component in stream.component_totals_mol_s:
        missing=[child for child in canonical if component not in canonical[child]]
        if missing: raise SelectiveSplitError(f"Selective split must specify {component!r} for every daughter; missing {missing}.")
        total=sum(canonical[child][component] for child in canonical)
        if abs(total-1.0)>1e-12: raise SelectiveSplitError(f"Selective fractions for {component!r} must sum to 1.0; got {total}.")
        locations=[item for item in stream.phase_inventory if float(item.component_totals_mol_s.get(component,0.0))>0.0]
        if len(locations)>1:
            loc=[(item.phase.value,item.identity) for item in locations]
            raise SelectiveSplitError(f"Selective split cannot partition shared component {component!r} across multiple phase_inventory items {loc}; owner unit-operation physics must transform the phase inventory.")
    return canonical

def _phase_for_inventory(inventory):
    phases={x.phase for x in inventory if any(float(v)>0 for v in x.component_totals_mol_s.values())}
    return next(iter(phases)) if len(phases)==1 else StreamPhase.MIXED

def split_water_stream(stream,fractions,*,composition_preserving,extension_transformers=None,tracked_transformers=None,engine_version=None):
    if not isinstance(composition_preserving,bool): raise SelectiveSplitError("composition_preserving must be an explicit boolean.")
    scalar_mode=all(isinstance(v,(int,float)) for v in fractions.values())
    if scalar_mode:
        scalar={str(k):_num(v,f"split fraction {k}") for k,v in fractions.items()}
        if not scalar or any(v<0 for v in scalar.values()) or abs(sum(scalar.values())-1)>1e-12: raise SelectiveSplitError("Scalar split fractions must be nonnegative and sum to 1.0.")
        child_fractions={child:{component:f for component in stream.component_totals_mol_s} for child,f in scalar.items()}
    else:
        child_fractions=_normalize_selective(stream,fractions); scalar={}
    extension_transformers=dict(extension_transformers or {}); tracked_transformers=dict(tracked_transformers or {}); output={}
    for child,cf in child_fractions.items():
        components={key:float(value)*cf[key] for key,value in stream.component_totals_mol_s.items()}
        if scalar_mode:
            toth_fraction=scalar[child]
        elif abs(stream.toth_eq_s)>1e-15:
            raise SelectiveSplitError("Selective split of nonzero TOTH has no generic partition rule; owner unit-operation physics must assign daughter TOTH explicitly.")
        else:
            toth_fraction=0.0
        inventory=[]
        for item in stream.phase_inventory:
            item_components={key:float(value)*cf[key] for key,value in item.component_totals_mol_s.items()}
            if any(v>0 for v in item_components.values()): inventory.append(PhaseInventoryItem(item.phase,item.identity,FrozenDict(item_components),item.metadata))
        tracked={}
        for key in stream.tracked_quantities:
            q=stream.tracked(key)
            if q.transport_policy is TrackedTransportPolicy.OWNER_MUST_TRANSFORM:
                if key not in tracked_transformers: raise TrackedQuantityTransportError(f"Tracked quantity {key!r} requires owner {q.owner!r} transform for split.")
                q=tracked_transformers[key](q,"split",FrozenDict({"daughter":child}))
            elif q.transport_policy is TrackedTransportPolicy.UNDEFINED_OUTSIDE_MIXER:
                q=TrackedQuantity.unavailable(unit=q.unit,dimension=q.dimension,mixing_rule=q.mixing_rule,transport_policy=q.transport_policy,owner=q.owner,reason=f"{key}: UNDEFINED_OUTSIDE_MIXER for split.")
            elif q.mixing_rule is MixingRule.EXTENSIVE_SUM:
                if not scalar_mode: raise TrackedQuantityTransportError(f"Extensive tracked quantity {key!r} requires owner transform for selective split.")
                q=replace(q,value=float(q.value)*scalar[child])
            if q is not None: tracked[key]=q.to_dict()
        extensions={}
        for namespace in stream.extensions:
            state=stream.extension(namespace); context={"fraction":scalar[child],"flow_fraction":scalar[child]} if scalar_mode else {"component_fractions":cf}; context["composition_preserving"]=composition_preserving
            transformed=_transform_extension((state,),operation="split",context=context,transformer=extension_transformers.get(namespace))
            if transformed is not None: extensions[namespace]=transformed.to_dict()
        child_stream=WaterStream(child,stream.temperature_c,stream.pressure_bar,FrozenDict(components),stream.toth_eq_s*toth_fraction,_phase_for_inventory(tuple(inventory)),tuple(inventory),stream.chemistry_policy,FrozenDict(tracked),FrozenDict(extensions),stream.diagnostics,None,stream.provenance)
        can_rebind=scalar_mode and composition_preserving is True and stream.phase is StreamPhase.AQUEOUS and stream.chemistry_certificate is not None
        if can_rebind:
            cert=stream.require_valid_chemistry_certificate(); f=scalar[child]
            child_stream=child_stream.with_chemistry_certificate(ChemistryCertificate(child_stream.state_hash,cert.residual_charge_eq_s*f,cert.ionic_strength_mol_kg,cert.solvent_water_kg_s*f,cert.density_kg_m3,cert.engine_version,cert.solution_mass_kg_s*f,cert.metadata))
        output[child]=child_stream
    return output

def component_mass_kg_s(stream,component_id):
    definition=DEFAULT_COMPONENT_REGISTRY.get(component_id)
    if definition.molar_mass_g_mol is None: raise WaterStreamError(f"No mass basis for {component_id!r}.")
    return float(stream.component_totals_mol_s.get(definition.canonical_id,0.0))*definition.molar_mass_g_mol/1000.0
@dataclass(frozen=True, slots=True)
class MassLedgerEntry:
    component_id:str; component_in_kg_s:float=0.0; component_out_kg_s:float=0.0; generated_kg_s:float=0.0; consumed_kg_s:float=0.0; transferred_to_solid_kg_s:float=0.0; transferred_to_gas_kg_s:float=0.0; chemical_dose_added_kg_s:float=0.0; accumulation_kg_s:float=0.0; explicit_solid_outlet:bool=False; explicit_gas_outlet:bool=False
    @property
    def residual_kg_s(self): return self.component_in_kg_s+self.generated_kg_s+self.chemical_dose_added_kg_s-self.consumed_kg_s-self.component_out_kg_s-self.transferred_to_solid_kg_s-self.transferred_to_gas_kg_s-self.accumulation_kg_s
    def assert_convention(self):
        if self.explicit_solid_outlet and self.transferred_to_solid_kg_s: raise LedgerConventionError(f"{self.component_id}: explicit SOLID outlet cannot also use transferred_to_solid.")
        if self.explicit_gas_outlet and self.transferred_to_gas_kg_s: raise LedgerConventionError(f"{self.component_id}: explicit GAS outlet cannot also use transferred_to_gas.")
@dataclass(frozen=True, slots=True)
class ReactionTransformation: reaction_id:str; from_component_id:str|None; to_component_id:str|None; extent_mol_s:float; stoichiometric_coefficient:float=1.0
@dataclass(frozen=True, slots=True)
class MassLedger:
    ledger_id:str; unit_operation_id:str; entries:tuple[MassLedgerEntry,...]=(); transformations:tuple[ReactionTransformation,...]=(); toth_in_eq_s:float=0.0; toth_out_eq_s:float=0.0; toth_delta_eq_s:float=0.0
    @property
    def toth_residual_eq_s(self): return self.toth_in_eq_s+self.toth_delta_eq_s-self.toth_out_eq_s
    @classmethod
    def from_streams(cls,ledger_id,unit_operation_id,inputs,outputs,*,toth_delta_eq_s=0.0,transformations=()):
        keys=set().union(*(s.component_totals_mol_s.keys() for s in (*inputs,*outputs))); entries=[]
        for key in sorted(keys): entries.append(MassLedgerEntry(key,sum(component_mass_kg_s(s,key) for s in inputs),sum(component_mass_kg_s(s,key) for s in outputs),explicit_solid_outlet=any(any(item.phase is StreamPhase.SOLID and item.component_totals_mol_s.get(key,0.0)>0 for item in s.phase_inventory) for s in outputs),explicit_gas_outlet=any(any(item.phase is StreamPhase.GAS and item.component_totals_mol_s.get(key,0.0)>0 for item in s.phase_inventory) for s in outputs)))
        return cls(ledger_id,unit_operation_id,tuple(entries),tuple(transformations),sum(s.toth_eq_s for s in inputs),sum(s.toth_eq_s for s in outputs),toth_delta_eq_s)
    def assert_closed(self,abs_tol_kg_s=1e-12,rel_tol=1e-9,toth_abs_tol_eq_s=1e-12,toth_rel_tol=1e-9):
        failures=[]
        for entry in self.entries:
            entry.assert_convention(); tolerance=max(abs_tol_kg_s,rel_tol*max(entry.component_in_kg_s,entry.component_out_kg_s,1e-30))
            if abs(entry.residual_kg_s)>tolerance: failures.append((entry.component_id,entry.residual_kg_s,tolerance))
        toth_tol=max(toth_abs_tol_eq_s,toth_rel_tol*max(abs(self.toth_in_eq_s),abs(self.toth_out_eq_s),1e-30))
        if abs(self.toth_residual_eq_s)>toth_tol: raise MassLedgerClosureError(f"TOTH residual {self.toth_residual_eq_s:.6g} eq/s exceeds {toth_tol:.6g}.")
        if failures: raise MassLedgerClosureError(f"MassLedger did not close: {failures}")
        return True


@dataclass(frozen=True)
class UnitOpConformanceResult:
    outputs: Mapping[str, WaterStream]
    ledger: MassLedger
    toth_delta_eq_s: float = 0.0

class UnitOpConformanceAdapter(Protocol):
    def solve(self, feed: WaterStream, *, tracked_transformers: Mapping | None = None,
              extension_transformers: Mapping | None = None) -> UnitOpConformanceResult: ...
    def solve_selective_split(self, feed: WaterStream, fractions: Mapping[str, Mapping[str, float]],
                              *, composition_preserving: bool) -> UnitOpConformanceResult: ...

def _direct_certificate(stream: WaterStream) -> ChemistryCertificate:
    import shared_waterstream as sw
    water=stream.solvent_water_kg_s_from_components; solution_mass=0.0; ionic2=0.0
    for key,amount in stream.component_totals_mol_s.items():
        definition=sw.DEFAULT_COMPONENT_REGISTRY.get(key)
        if definition.molar_mass_g_mol is not None: solution_mass+=float(amount)*definition.molar_mass_g_mol/1000.0
        charge=definition.charge or 0; ionic2+=float(amount)*charge*charge
    return ChemistryCertificate(stream.state_hash,stream.fixed_charge_residual_eq_s,
        0.0 if water<=0 else 0.5*ionic2/water,water,1000.0,
        "unitop-conformance-fixture",solution_mass)

def _base_stream(*, tracked=None, extension=None) -> WaterStream:
    components={"h2o":1000.0*1000.0/H2O_MOLAR_MASS_G_MOL,"sodium":1.0,"chloride":1.0}
    tracked_values={} if tracked is None else {tracked[0]:tracked[1].to_dict()}
    extension_values={} if extension is None else {extension.namespace:extension.to_dict()}
    raw=WaterStream("unitop-conformance-feed",25.0,1.5,FrozenDict(components),0.0,
        tracked_quantities=FrozenDict(tracked_values),extensions=FrozenDict(extension_values))
    return raw.with_chemistry_certificate(_direct_certificate(raw))

def _extract(result):
    if not hasattr(result,"outputs") or not hasattr(result,"ledger"):
        raise AssertionError("UnitOp conformance result must expose .outputs and .ledger.")
    outputs=result.outputs
    if isinstance(outputs,Mapping): outputs=tuple(outputs.values())
    else: outputs=tuple(outputs)
    if not outputs or any(not isinstance(x,WaterStream) for x in outputs):
        raise AssertionError("UnitOp conformance result contains no valid WaterStream outputs.")
    if not isinstance(result.ledger,MassLedger):
        raise AssertionError("UnitOp conformance result .ledger must be a MassLedger.")
    return outputs,result.ledger,float(getattr(result,"toth_delta_eq_s",result.ledger.toth_delta_eq_s) or 0.0)

def assert_unitop_fail_closed(adapter: UnitOpConformanceAdapter) -> dict[str,bool]:
    owner_q=TrackedQuantity(1.0,"arb","owner_state",MixingRule.NOT_MIXABLE,
        TrackedTransportPolicy.OWNER_MUST_TRANSFORM,"conformance-owner")
    try: adapter.solve(_base_stream(tracked=("owner_state",owner_q)),tracked_transformers=None,extension_transformers=None)
    except TrackedQuantityTransportError: tracked_owner_ok=True
    else: raise AssertionError("UnitOp did not fail closed for OWNER_MUST_TRANSFORM tracked quantity.")

    extension=ExtensionState(ExtensionSpec("conformance:owner-state","conformance-owner",
        ExtensionTransportPolicy.OWNER_MUST_TRANSFORM),FrozenDict({"state":1.0}))
    try: adapter.solve(_base_stream(extension=extension),tracked_transformers=None,extension_transformers=None)
    except ExtensionTransportError: extension_owner_ok=True
    else: raise AssertionError("UnitOp did not fail closed for OWNER_MUST_TRANSFORM extension.")

    conserved=TrackedQuantity(10.0,"mg/L","conserved_fixture",MixingRule.FLOW_WEIGHTED,
        TrackedTransportPolicy.CONSERVED)
    feed=_base_stream(tracked=("conserved_state",conserved))
    outputs,ledger,toth_delta=_extract(adapter.solve(feed,tracked_transformers={},extension_transformers={}))
    for output in outputs:
        q=output.tracked("conserved_state")
        if q is None or q.transport_policy is not TrackedTransportPolicy.CONSERVED:
            raise AssertionError("UnitOp dropped or reclassified a CONSERVED tracked quantity.")
    independent=MassLedger.from_streams("unitop-conformance-independent","unitop-conformance",
        [feed],list(outputs),toth_delta_eq_s=toth_delta)
    independent.assert_closed(); ledger.assert_closed()

    selective_feed=_base_stream()
    fractions={"a":{"h2o":0.8,"sodium":0.7,"chloride":0.7},
               "b":{"h2o":0.2,"sodium":0.3,"chloride":0.3}}
    if not hasattr(adapter,"solve_selective_split"):
        raise AssertionError("UnitOp conformance adapter must expose solve_selective_split().")
    split_outputs,split_ledger,_=_extract(
        adapter.solve_selective_split(selective_feed,fractions,composition_preserving=False))
    if any(x.chemistry_certificate is not None for x in split_outputs):
        raise AssertionError("UnitOp selective split rebound a ChemistryCertificate.")
    MassLedger.from_streams("unitop-selective-independent","unitop-selective",
        [selective_feed],list(split_outputs)).assert_closed(); split_ledger.assert_closed()

    bad=MassLedgerEntry("calcium",component_in_kg_s=1.0,component_out_kg_s=1.0,
        transferred_to_solid_kg_s=0.1,explicit_solid_outlet=True)
    try: bad.assert_convention()
    except LedgerConventionError: outlet_ok=True
    else: raise AssertionError("Explicit solid outlet double-count convention was not enforced.")

    return {"tracked_owner_must_transform":tracked_owner_ok,
        "extension_owner_must_transform":extension_owner_ok,
        "conserved_tracked_preserved":True,"mass_and_toth_closed":True,
        "selective_split_certificate_invalidated":True,
        "explicit_outlet_double_count_rejected":outlet_ok}


__all__=[name for name in globals() if not name.startswith("_")]
