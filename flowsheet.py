"""Generalized multi-pass RO flowsheet foundation for Total RO Design v0.25.

The module is deliberately separate from membrane physics.  It reuses the
validated ``calculations.membrane_stage`` kernel and the existing carbonate /
activity chemistry layer, while adding plant topology, conservative stream
mixing, downstream-concentrate recycle, pump-suction mixing, partial downstream
permeate treatment, and nonlinear tear-stream convergence.

v0.25 Alpha scope:
* 1-8 serial membrane passes;
* fractional permeate routing to the next pass;
* any downstream pass concentrate recycled to any upstream pass suction;
* recycle specified by source fraction or absolute flow;
* multiple/nested/crossing recycle links represented as tear streams;
* conservative chemistry mixing; pH is never a tear/conserved variable;
* damped fixed-point + Anderson, with JFNK/GMRES fallback;
* actual HPP flow includes all recycle entering its suction;
* overall plant recovery uses only external feed and exported product.

Element-interface split-permeate hydraulics are represented in the data model
but remain experimental in this Alpha and are not silently approximated by a
post-calculation flow split.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterable
import math

from calculations import multistage as ro_multistage, _pump_wire_power_kw
from membrane_db import get_membrane
from water_chemistry import SPECIES, normalize_composition, total_tds_mg_l
from chemistry_analysis import solve_carbonate_state, analytical_alkalinity_mol_kg, mix_carbonate_streams
from solver import AndersonMixer
from solver.root_scalar import brent_root
from solver.jfnk import solve_jfnk


class FlowsheetConvergenceError(ValueError):
    pass


@dataclass
class Stream:
    flow_m3h: float
    pressure_bar: float = 1.0
    temperature_c: float = 25.0
    tds_mg_l: float = 0.0
    composition_mg_l: dict[str, float] | None = None
    carbonate_state: dict[str, Any] | None = None
    name: str = "stream"

    @property
    def full_chemistry(self) -> bool:
        return bool(self.composition_mg_l)

    @property
    def ph(self) -> float | None:
        try: return float(self.carbonate_state.get("ph")) if self.carbonate_state else None
        except Exception: return None

    def allocated(self, flow_m3h: float, *, name: str | None = None) -> "Stream":
        q=max(0.0,min(float(flow_m3h),max(0.0,float(self.flow_m3h))))
        return Stream(q,self.pressure_bar,self.temperature_c,self.tds_mg_l,
                      dict(self.composition_mg_l or {}) or None,
                      dict(self.carbonate_state or {}) or None,name or self.name)

    def fraction(self, fraction: float, *, name: str | None = None) -> "Stream":
        f=max(0.0,min(1.0,float(fraction)))
        return self.allocated(self.flow_m3h*f,name=name)

    def to_dict(self) -> dict[str, Any]:
        return {"name":self.name,"flow_m3h":self.flow_m3h,"pressure_bar":self.pressure_bar,
                "temperature_c":self.temperature_c,"tds_mg_l":self.tds_mg_l,"ph":self.ph,
                "composition_mg_l":dict(self.composition_mg_l or {}),
                "alkalinity_mg_l_as_hco3":(self.carbonate_state or {}).get("total_alkalinity_mg_l_as_hco3")}


@dataclass
class Junction:
    junction_id: str
    kind: str = "closed"  # closed or open/gas_equilibrium
    pressure_bar: float | None = None
    pco2_atm: float | None = None


@dataclass
class SplitPermeateConfig:
    interface_after_element: int
    zone_a_backpressure_bar: float = 0.0
    zone_b_backpressure_bar: float = 0.0
    enabled: bool = True


@dataclass
class Element:
    position: int


@dataclass
class Vessel:
    elements: list[Element] = field(default_factory=list)


@dataclass
class Stage:
    vessels: int
    elements_per_vessel: int
    membrane_id: str = ""
    permeate_pressure_bar: float = 0.0
    interstage_boost_bar: float = 0.0


@dataclass
class Pass:
    pass_id: str

    # Legacy one-stage representation. These fields remain accepted so existing
    # v0.25 payloads and regression fixtures continue to load unchanged.
    membrane_id: str = ""
    vessels: int = 0
    elements_per_vessel: int = 7

    feed_pressure_bar: float | None = None
    target_recovery: float | None = None
    permeate_pressure_bar: float = 0.0
    pump_efficiency: float = 0.85
    motor_efficiency: float = 0.97
    vfd_efficiency: float = 0.97
    fouling_factor: float = 1.0
    salt_passage_factor: float = 1.0
    permeate_to_next_fraction: float = 1.0
    split_permeate: SplitPermeateConfig | None = None

    # New authoritative Pass -> Stage hierarchy.
    # A Pass may contain 1-4 serial RO stages. Each stage is solved by the
    # existing Total RO Design multistage engine.
    stages: list[Stage] = field(default_factory=list)


@dataclass
class RecycleLink:
    link_id: str
    source_pass: str
    source_port: str = "concentrate"  # concentrate/permeate
    destination_pass: str = "P1"
    destination: str = "suction"      # v0.25 supports pass suction explicitly
    fraction: float | None = 1.0
    absolute_flow_m3h: float | None = None
    enabled: bool = True


@dataclass
class Splitter:
    source: str
    fraction_to_primary: float


@dataclass
class PassResult:
    spec: Pass
    suction: Stream
    membrane_feed: Stream
    permeate: Stream
    concentrate: Stream
    membrane: dict[str, Any]
    hpp_power_kw: float


@dataclass
class FlowsheetResult:
    converged: bool
    iterations: int
    method: str
    residual_norm: float
    passes: dict[str, PassResult]
    recycles: dict[str, Stream]
    products: list[Stream]
    rejects: list[Stream]
    external_feed: Stream
    overall_recovery: float
    water_closure_m3h: float
    component_closure_mg_h: dict[str,float]
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"converged":self.converged,"iterations":self.iterations,"method":self.method,"residual_norm":self.residual_norm,
                "external_feed":self.external_feed.to_dict(),"overall_recovery":self.overall_recovery,"water_closure_m3h":self.water_closure_m3h,
                "component_closure_mg_h":self.component_closure_mg_h,"recycles":{k:v.to_dict() for k,v in self.recycles.items()},
                "products":[x.to_dict() for x in self.products],"rejects":[x.to_dict() for x in self.rejects],
                "passes":{k:{"suction":v.suction.to_dict(),"membrane_feed":v.membrane_feed.to_dict(),"permeate":v.permeate.to_dict(),
                              "concentrate":v.concentrate.to_dict(),"hpp_power_kw":v.hpp_power_kw,"membrane":v.membrane} for k,v in self.passes.items()},
                "diagnostics":self.diagnostics}


def stream_from_payload(data: dict[str,Any], *, name: str="External feed") -> Stream:
    q=float(data.get("flow_m3h") or 0); t=float(data.get("temperature_c") or 25); p=float(data.get("pressure_bar") or 1)
    comp=normalize_composition(data.get("composition_mg_l") or {}) if data.get("composition_mg_l") else None
    tds=float(data.get("tds_mg_l") or (total_tds_mg_l(comp) if comp else 0))
    state=None
    if comp:
        ph=float(data.get("ph") or 7.0)
        ta=analytical_alkalinity_mol_kg(comp,t)
        state=solve_carbonate_state(comp,t,ph=ph,total_alkalinity_mol_kg=ta)
        comp=normalize_composition(state["composition"]); tds=total_tds_mg_l(comp)
    return Stream(q,p,t,tds,comp,state,name)


def _state_from_stage(result: dict[str,Any], port: str, *, pressure_bar: float, name: str) -> Stream:
    q=float(result["permeate_flow"] if port=="permeate" else result["reject_flow"])
    t=float(result.get("temperature_c",25)); tds=float(result["permeate_tds_ppm"] if port=="permeate" else result["concentrate_tds_ppm"])
    comp=result.get("permeate_composition_mg_l" if port=="permeate" else "concentrate_composition_mg_l")
    state=None
    if comp:
        comp=normalize_composition(comp)
        ta=result.get(f"{port}_total_alkalinity_mol_kg")
        ct=result.get(f"{port}_total_inorganic_carbon_mol_kg")
        try:
            if ta is not None and ct is not None:
                state=solve_carbonate_state(comp,t,total_alkalinity_mol_kg=float(ta),total_inorganic_carbon_mol_kg=float(ct))
        except Exception: state=None
    return Stream(q,float(pressure_bar),t,tds,dict(comp or {}) or None,state,name)


def mix_streams(streams: Iterable[Stream], *, junction: Junction | None=None, name: str="Mixed feed") -> Stream:
    rows=[s for s in streams if s and s.flow_m3h>1e-12]
    if not rows: return Stream(0.0,name=name)
    q=sum(s.flow_m3h for s in rows); temp=sum(s.flow_m3h*s.temperature_c for s in rows)/q
    pressure=float(junction.pressure_bar) if junction and junction.pressure_bar is not None else min(s.pressure_bar for s in rows)
    if all(s.full_chemistry and s.carbonate_state for s in rows):
        mixed=mix_carbonate_streams([{"flow":s.flow_m3h,"composition":s.composition_mg_l,"state":s.carbonate_state} for s in rows],temp)
        comp=normalize_composition(mixed["composition"])
        # Open/gas-equilibrium support is intentionally explicit.  In v0.25 the
        # receiving tank is equilibrated by solving the carbonate state at a
        # user-specified pCO2 approximation only when requested; closed is default.
        if junction and junction.kind.lower() in {"open","gas_equilibrium"} and junction.pco2_atm:
            # Current chemistry core exposes robust TA/CT solving; atmospheric
            # gas transfer kinetics are not fabricated.  Retain TA and flag pCO2
            # for future gas-equilibrium boundary refinement.
            mixed={**mixed,"gas_equilibrium_pco2_atm":float(junction.pco2_atm),"junction_model":"open_boundary_pending_mass_transfer"}
        return Stream(q,pressure,temp,total_tds_mg_l(comp),comp,mixed,name)
    # Quick/TDS mode: TDS is conservative; pH is deliberately not averaged.
    tds=sum(s.flow_m3h*s.tds_mg_l for s in rows)/q
    return Stream(q,pressure,temp,tds,None,None,name)



def _pass_stage_specs(spec: Pass) -> list[Stage]:
    """Return the authoritative ordered Stage list for one RO Pass."""
    if spec.stages:
        stages = list(spec.stages)
    else:
        stages = [
            Stage(
                vessels=int(spec.vessels or 0),
                elements_per_vessel=int(spec.elements_per_vessel or 7),
                membrane_id=str(spec.membrane_id or ""),
                permeate_pressure_bar=float(spec.permeate_pressure_bar or 0.0),
                interstage_boost_bar=0.0,
            )
        ]

    if not 1 <= len(stages) <= 4:
        raise ValueError(
            f"{spec.pass_id}: each RO pass must contain between 1 and 4 stages."
        )

    normalized = []

    for i, stage in enumerate(stages, 1):
        membrane_id = str(stage.membrane_id or spec.membrane_id or "").strip()
        vessels = int(stage.vessels or 0)
        epv = int(stage.elements_per_vessel or 0)

        if not membrane_id:
            raise ValueError(
                f"{spec.pass_id} Stage {i}: select a membrane."
            )

        if vessels <= 0:
            raise ValueError(
                f"{spec.pass_id} Stage {i}: pressure vessels must be greater than zero."
            )

        if not 1 <= epv <= 8:
            raise ValueError(
                f"{spec.pass_id} Stage {i}: elements per vessel must be from 1 to 8."
            )

        normalized.append(
            Stage(
                vessels=vessels,
                elements_per_vessel=epv,
                membrane_id=membrane_id,
                permeate_pressure_bar=float(
                    stage.permeate_pressure_bar
                    if stage.permeate_pressure_bar is not None
                    else spec.permeate_pressure_bar
                ),
                interstage_boost_bar=(
                    0.0 if i == 1
                    else float(stage.interstage_boost_bar or 0.0)
                ),
            )
        )

    return normalized


def _multistage_request(
    feed: Stream,
    spec: Pass,
    pressure_bar: float,
    *,
    fast: bool = False,
) -> dict[str, Any]:
    """
    Translate one generalized flowsheet Pass into the established Total RO
    Design 1-4 stage Plant Design input schema.

    This deliberately does not reproduce membrane physics in flowsheet.py.
    """
    stages = _pass_stage_specs(spec)

    data: dict[str, Any] = {
        "flow_unit": "m3/h",
        "pressure_unit": "bar",
        "water_mode": "full" if feed.full_chemistry else "tds",
        "feed_flow": float(feed.flow_m3h),
        "feed_tds": float(feed.tds_mg_l),
        "analysis_tds": float(feed.tds_mg_l),
        "temperature_c": float(feed.temperature_c),
        "feed_ph": float(feed.ph or 7.0),

        "membrane_coupling": True,
        "design_mode": "manual",
        "solve_basis": "pressure",
        "stage_count": len(stages),

        "membrane_pressure_1": float(pressure_bar),
        "suction_pressure": float(feed.pressure_bar),
        "pretreatment_discharge_pressure": float(feed.pressure_bar),

        "pump_eff": float(spec.pump_efficiency),
        "motor_eff": float(spec.motor_efficiency),
        "vfd_eff": float(spec.vfd_efficiency),
        "pump_no_vfd": False,

        "fouling_factor": float(spec.fouling_factor),
        "salt_passage_factor": float(spec.salt_passage_factor),

        # The source Stream already represents any upstream conditioning.
        # Never re-dose acid inside each recycle evaluation.
        "acid_enabled": False,
        "acid_type": "none",

        "interstage_control_objective": "manual",
        "_solver_fast": bool(fast),
    }

    if feed.composition_mg_l:
        for species in SPECIES:
            data[f"ion_{species}"] = float(
                feed.composition_mg_l.get(species, 0.0)
            )

    for i, stage in enumerate(stages, 1):
        data[f"membrane_{i}"] = stage.membrane_id
        data[f"vessels_{i}"] = int(stage.vessels)
        data[f"elements_per_vessel_{i}"] = int(stage.elements_per_vessel)
        data[f"permeate_pressure_{i}"] = float(stage.permeate_pressure_bar)

        if i > 1:
            boost = float(stage.interstage_boost_bar or 0.0)
            data[f"interstage_boost_{i}"] = boost
            data[f"interstage_equipment_{i}"] = (
                "pump" if boost > 0 else "none"
            )

    return data


def _first_numeric(result: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = result.get(key)
        if value in (None, ""):
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            return value
    return None


def _pass_result_stage_count(result: dict[str, Any], spec: Pass) -> int:
    try:
        n = int(float(result.get("stage_count") or 0))
    except Exception:
        n = 0

    return n if n > 0 else len(_pass_stage_specs(spec))


def _stream_from_multistage_result(
    result: dict[str, Any],
    spec: Pass,
    port: str,
) -> Stream:
    """
    Reconstruct one conservative external Pass stream from the authoritative
    multistage result state.
    """
    n = _pass_result_stage_count(result, spec)
    temp = float(result.get("temperature_c") or 25.0)

    if port == "permeate":
        q = _first_numeric(
            result,
            "product_flow",
            "composite_permeate_flow",
            f"stage{n}_permeate_flow",
            "permeate_flow",
        )

        # Prefer an authoritative composite value when the established
        # multistage engine exposes one. In TDS mode it may expose only
        # stage-specific permeate streams, in which case construct the
        # collected permeate header by conservative flow-weighted mass balance.
        tds = _first_numeric(
            result,
            "composite_permeate_tds_ppm",
            "permeate_tds_ppm",
        )

        if tds is None:
            stage_perm = []

            for i in range(1, n + 1):
                qi = _first_numeric(
                    result,
                    f"stage{i}_permeate_flow",
                )
                ci = _first_numeric(
                    result,
                    f"stage{i}_permeate_tds_ppm",
                )

                if qi is not None and ci is not None and qi > 0:
                    stage_perm.append((qi, ci))

            qsum = sum(qi for qi, _ in stage_perm)

            if qsum > 0:
                tds = (
                    sum(qi * ci for qi, ci in stage_perm)
                    / qsum
                )

        comp = result.get(
            "composite_permeate_composition_mg_l"
        )

        # A single-stage full-chemistry calculation may legitimately expose
        # only the stage-specific permeate composition.
        if comp is None and n == 1:
            comp = result.get(
                "stage1_permeate_composition_mg_l"
            )

        ph = _first_numeric(
            result,
            "composite_permeate_ph",
            f"stage{n}_permeate_ph",
        )

        ta = _first_numeric(
            result,
            "composite_permeate_total_alkalinity_mol_kg",
            f"stage{n}_permeate_total_alkalinity_mol_kg",
        )

        ct = _first_numeric(
            result,
            "composite_permeate_total_inorganic_carbon_mol_kg",
            f"stage{n}_permeate_total_inorganic_carbon_mol_kg",
        )

        # Composite permeate is treated as a collected header. Where different
        # stage backpressures exist, the physically conservative collection
        # pressure is the lowest connected permeate pressure.
        stage_pressures = [
            float(x.permeate_pressure_bar)
            for x in _pass_stage_specs(spec)
        ]
        pressure = min(stage_pressures) if stage_pressures else 0.0
        name = f"{spec.pass_id} permeate"

    else:
        q = _first_numeric(
            result,
            "reject_flow_final",
            f"reject_flow_{n}",
            f"stage{n}_reject_flow",
            "reject_flow",
        )

        tds = _first_numeric(
            result,
            f"stage{n}_concentrate_tds_ppm",
            "final_concentrate_tds_ppm",
            "concentrate_tds_ppm",
        )

        comp = result.get(
            f"stage{n}_concentrate_composition_mg_l"
        ) or result.get("final_concentrate_composition_mg_l")

        ph = _first_numeric(
            result,
            f"stage{n}_concentrate_ph",
            "final_concentrate_ph",
        )

        ta = _first_numeric(
            result,
            f"stage{n}_concentrate_total_alkalinity_mol_kg",
            "final_concentrate_total_alkalinity_mol_kg",
        )

        ct = _first_numeric(
            result,
            f"stage{n}_concentrate_total_inorganic_carbon_mol_kg",
            "final_concentrate_total_inorganic_carbon_mol_kg",
        )

        pressure = _first_numeric(
            result,
            "reject_pressure_final",
            f"reject_pressure_{n}",
            f"stage{n}_reject_pressure_bar",
            f"stage{n}_concentrate_pressure_bar",
        )

        if pressure is None:
            pressure = float(spec.feed_pressure_bar or 0.0)

        name = f"{spec.pass_id} concentrate"

    if q is None:
        raise ValueError(
            f"{spec.pass_id}: multistage result did not expose {port} flow."
        )

    if tds is None:
        if comp:
            tds = total_tds_mg_l(comp)
        else:
            raise ValueError(
                f"{spec.pass_id}: multistage result did not expose {port} TDS."
            )

    normalized = None
    state = None

    if comp:
        normalized = normalize_composition(comp)

        try:
            if ta is not None and ct is not None:
                state = solve_carbonate_state(
                    normalized,
                    temp,
                    total_alkalinity_mol_kg=float(ta),
                    total_inorganic_carbon_mol_kg=float(ct),
                )
            elif ph is not None:
                state = solve_carbonate_state(
                    normalized,
                    temp,
                    ph=float(ph),
                    total_alkalinity_mol_kg=
                        analytical_alkalinity_mol_kg(normalized, temp),
                )
        except Exception:
            state = None

    return Stream(
        float(q),
        float(pressure),
        temp,
        float(tds),
        normalized,
        state,
        name,
    )


def _pass_wire_power_kw(
    result: dict[str, Any],
    feed: Stream,
    pressure_bar: float,
    spec: Pass,
) -> float:
    """
    Prefer the authoritative multistage pump-energy result when exposed.
    Fall back only to the Pass HPP duty if the legacy result lacks a total.
    """
    value = _first_numeric(
        result,
        "total_pump_wire_power_kw",
        "total_pump_power_kw",
        "gross_pump_power_kw",
        "hpp_power_kw",
        "hp_pump_power_kw",
        "pump_power_kw",
    )

    if value is not None:
        return float(value)

    dp = max(0.0, float(pressure_bar) - float(feed.pressure_bar))

    return float(
        _pump_wire_power_kw(
            feed.flow_m3h,
            dp,
            spec.pump_efficiency,
            spec.motor_efficiency,
            spec.vfd_efficiency,
        )
    )


def _pass_pressure_for_recovery(feed: Stream, spec: Pass) -> float:
    target=float(spec.target_recovery or 0)
    if not 0<target<0.98: raise ValueError(f"{spec.pass_id}: target recovery must be between 0 and 98%.")
    lead_stage=_pass_stage_specs(spec)[0]
    m=get_membrane(lead_stage.membrane_id)
    maxp=float(m.get("max_pressure_bar") or m.get("max_operating_pressure_bar") or 83)
    low=max(feed.pressure_bar+0.5,1.0); high=max(low+1.0,maxp)
    def calc(p):
        r=_run_membrane(feed,spec,p,resolve_carbonate_streams=False)
        return float(r["recovery"])-target
    # Scan because low-pressure membrane evaluations may collapse to zero flux.
    points=[low+(high-low)*i/16 for i in range(17)]; vals=[]
    for p in points:
        try: vals.append((p,calc(p)))
        except Exception: vals.append((p,None))
    for (a,fa),(b,fb) in zip(vals,vals[1:]):
        if fa is None or fb is None: continue
        if fa==0:return a
        if fa*fb<=0: return brent_root(calc,a,b,xtol=2e-5,rtol=2e-6,max_iter=60)[0]
    raise ValueError(f"{spec.pass_id}: requested recovery is not bracketed within the membrane pressure limit.")


def _run_membrane(feed: Stream, spec: Pass, pressure: float, *, resolve_carbonate_streams: bool=True) -> dict[str,Any]:
    if spec.split_permeate and spec.split_permeate.enabled:
        raise NotImplementedError(
            "Element-interface split-permeate hydraulics remain experimental "
            "and are not approximated as a post-solve split."
        )

    data = _multistage_request(
        feed,
        spec,
        pressure,
        fast=not resolve_carbonate_streams,
    )

    return ro_multistage(data)


def solve_pass(feed: Stream, spec: Pass) -> PassResult:
    if feed.flow_m3h <= 0:
        raise ValueError(f"{spec.pass_id}: feed flow must be positive.")

    pressure = (
        float(spec.feed_pressure_bar)
        if spec.feed_pressure_bar is not None
        else _pass_pressure_for_recovery(feed, spec)
    )

    result = _run_membrane(
        feed,
        spec,
        pressure,
        resolve_carbonate_streams=True,
    )

    membrane_feed = Stream(
        feed.flow_m3h,
        pressure,
        feed.temperature_c,
        feed.tds_mg_l,
        feed.composition_mg_l,
        feed.carbonate_state,
        f"{spec.pass_id} membrane feed",
    )

    perm = _stream_from_multistage_result(
        result,
        spec,
        "permeate",
    )

    conc = _stream_from_multistage_result(
        result,
        spec,
        "concentrate",
    )

    power = _pass_wire_power_kw(
        result,
        feed,
        pressure,
        spec,
    )

    return PassResult(
        spec,
        feed,
        membrane_feed,
        perm,
        conc,
        result,
        float(power),
    )


class Flowsheet:
    def __init__(self, external_feed: Stream, passes: list[Pass], recycles: list[RecycleLink] | None=None):
        self.external_feed=external_feed; self.passes=passes; self.recycles=[r for r in (recycles or []) if r.enabled]
        if not passes: raise ValueError("Flowsheet requires at least one RO pass.")
        ids=[p.pass_id for p in passes]
        if len(ids)!=len(set(ids)): raise ValueError("Pass IDs must be unique.")
        self.index={p.pass_id:i for i,p in enumerate(passes)}
        for r in self.recycles:
            if r.source_pass not in self.index or r.destination_pass not in self.index: raise ValueError(f"Recycle {r.link_id} references an unknown pass.")
            if r.destination!="suction": raise ValueError("v0.25 Alpha currently supports recycle destination at a pass HPP suction junction.")
        self._validate_allocations()

    def _validate_allocations(self):
        by_source={}
        for r in self.recycles:
            if r.fraction is not None:
                key=(r.source_pass,r.source_port); by_source[key]=by_source.get(key,0.0)+float(r.fraction)
        bad=[k for k,v in by_source.items() if v>1.0+1e-10]
        if bad: raise ValueError(f"Recycle source allocation exceeds 100% for {bad[0][0]} {bad[0][1]}.")

    def _empty_tears(self) -> dict[str,Stream]:
        return {r.link_id:Stream(0.0,self.external_feed.pressure_bar,self.external_feed.temperature_c,0.0,None,None,r.link_id) for r in self.recycles}

    def _evaluate(self, tears: dict[str,Stream]) -> tuple[dict[str,PassResult],dict[str,Stream],list[Stream],list[Stream]]:
        results={}; actual={}; products=[]; rejects=[]; forward_feed=self.external_feed
        for i,spec in enumerate(self.passes):
            incoming=[forward_feed]
            incoming += [tears[r.link_id] for r in self.recycles if r.destination_pass==spec.pass_id and tears.get(r.link_id) and tears[r.link_id].flow_m3h>0]
            suction=mix_streams(incoming,junction=Junction(f"{spec.pass_id}_suction","closed",pressure_bar=forward_feed.pressure_bar),name=f"{spec.pass_id} HPP suction")
            pr=solve_pass(suction,spec); results[spec.pass_id]=pr
            # Determine allocations from each source port after pass solves are available.
            frac_next=max(0.0,min(1.0,float(spec.permeate_to_next_fraction if i<len(self.passes)-1 else 0.0)))
            if i<len(self.passes)-1:
                forward_feed=pr.permeate.fraction(frac_next,name=f"{spec.pass_id} permeate to {self.passes[i+1].pass_id}")
                if frac_next<1.0: products.append(pr.permeate.fraction(1-frac_next,name=f"{spec.pass_id} product bypass"))
            else:
                products.append(pr.permeate)

        # Build actual recycle streams after all source streams exist.
        allocated_fraction={}
        allocated_abs={}
        for r in self.recycles:
            src_res=results[r.source_pass]; src=src_res.concentrate if r.source_port=="concentrate" else src_res.permeate
            if r.absolute_flow_m3h is not None:
                q=float(r.absolute_flow_m3h); allocated_abs[(r.source_pass,r.source_port)]=allocated_abs.get((r.source_pass,r.source_port),0.0)+q
            else:
                q=src.flow_m3h*float(r.fraction if r.fraction is not None else 0.0); allocated_fraction[(r.source_pass,r.source_port)]=allocated_fraction.get((r.source_pass,r.source_port),0.0)+q
            if q>src.flow_m3h+1e-9: raise ValueError(f"Recycle {r.link_id} requests more flow than its source stream provides.")
            # Conventional low-pressure return: elevated source pressure is dissipated to receiver suction.
            dest_idx=self.index[r.destination_pass]
            recv_pressure=self.external_feed.pressure_bar if dest_idx==0 else results[self.passes[dest_idx-1].pass_id].permeate.pressure_bar
            actual[r.link_id]=src.allocated(q,name=r.link_id); actual[r.link_id].pressure_bar=recv_pressure
        # External rejects are un-recycled concentrate fractions.
        for spec in self.passes:
            src=results[spec.pass_id].concentrate; qrec=sum(s.flow_m3h for rid,s in actual.items() if next(r for r in self.recycles if r.link_id==rid).source_pass==spec.pass_id and next(r for r in self.recycles if r.link_id==rid).source_port=="concentrate")
            if src.flow_m3h-qrec>1e-9: rejects.append(src.allocated(src.flow_m3h-qrec,name=f"{spec.pass_id} final concentrate"))
        return results,actual,products,rejects

    def _vector_layout(self):
        # Fixed layout per recycle: Q, Q*T, TDS mass OR species mass + Q*TA + Q*CT.
        full=self.external_feed.full_chemistry
        names=[]
        for r in self.recycles:
            names += [f"{r.link_id}:Q",f"{r.link_id}:QT"]
            if full:
                names += [f"{r.link_id}:{sp}" for sp in SPECIES] + [f"{r.link_id}:TA",f"{r.link_id}:CT"]
            else: names += [f"{r.link_id}:TDS"]
        return full,names

    def _pack(self, tears: dict[str,Stream]) -> list[float]:
        full,_=self._vector_layout(); out=[]
        for r in self.recycles:
            s=tears.get(r.link_id) or Stream(0); q=max(0.0,s.flow_m3h); out += [q,q*s.temperature_c]
            if full:
                comp=normalize_composition(s.composition_mg_l or {})
                out += [q*float(comp.get(sp,0.0)) for sp in SPECIES]
                st=s.carbonate_state or {}; out += [q*float(st.get("total_alkalinity_mol_kg",0.0)),q*float(st.get("total_inorganic_carbon_mol_kg",0.0))]
            else: out += [q*s.tds_mg_l]
        return out

    def _unpack(self, x: list[float]) -> dict[str,Stream]:
        full,_=self._vector_layout(); out={}; k=0
        for r in self.recycles:
            q=max(0.0,float(x[k])); qt=float(x[k+1]); k+=2; temp=qt/q if q>1e-12 else self.external_feed.temperature_c
            if full:
                masses={sp:max(0.0,float(x[k+i])) for i,sp in enumerate(SPECIES)}; k+=len(SPECIES)
                ta_flow=float(x[k]); ct_flow=max(0.0,float(x[k+1])); k+=2
                comp={sp:(masses[sp]/q if q>1e-12 else 0.0) for sp in SPECIES}; state=None
                if q>1e-12:
                    try: state=solve_carbonate_state(comp,temp,total_alkalinity_mol_kg=ta_flow/q,total_inorganic_carbon_mol_kg=ct_flow/q)
                    except Exception:
                        # Invalid Newton/Krylov trial is rejected by the caller.
                        raise ValueError(f"Recycle {r.link_id} trial chemistry could not be speciated.")
                out[r.link_id]=Stream(q,self.external_feed.pressure_bar,temp,total_tds_mg_l(comp),comp,state,r.link_id)
            else:
                tds_mass=max(0.0,float(x[k])); k+=1; out[r.link_id]=Stream(q,self.external_feed.pressure_bar,temp,tds_mass/q if q>1e-12 else 0.0,None,None,r.link_id)
        return out

    def solve(self, *, max_iter:int=30, rel_tol:float=2e-7, method:str="auto") -> FlowsheetResult:
        if not self.recycles:
            passes,actual,products,rejects=self._evaluate({}); return self._finalize(passes,actual,products,rejects,True,1,"sequential",0.0,{})
        tears=self._empty_tears()
        # One no-recycle evaluation provides a physically meaningful initial recycle estimate.
        passes,actual,products,rejects=self._evaluate(tears)
        for lid,s in actual.items(): tears[lid]=s.fraction(0.5,name=lid)
        mixer=AndersonMixer(memory=4); prev=math.inf; stagnation=0; history=[]
        for it in range(1,max_iter+1):
            passes,actual,products,rejects=self._evaluate(tears)
            x=self._pack(tears); gx=self._pack(actual)
            scales=[max(abs(a),abs(b),1.0) for a,b in zip(x,gx)]
            residual=[(b-a)/s for a,b,s in zip(x,gx,scales)]; norm=math.sqrt(sum(v*v for v in residual)/max(1,len(residual)))
            history.append(norm)
            if norm<rel_tol: return self._finalize(passes,actual,products,rejects,True,it,"anderson/damped",norm,{"residual_history":history})
            proposal=mixer.propose(x,gx)
            if proposal is None or it<3: proposal=[a+0.45*(b-a) for a,b in zip(x,gx)]
            try: tears=self._unpack(proposal)
            except Exception: tears=self._unpack([a+0.2*(b-a) for a,b in zip(x,gx)])
            if norm>=prev*0.995: stagnation+=1
            else: stagnation=0
            prev=norm
            if stagnation>=4 and method in {"auto","jfnk"}:
                # Switch to JFNK on the same conservative tear variables.
                x0=self._pack(tears); base_scales=[max(abs(v),1.0) for v in x0]
                def res(v):
                    tt=self._unpack(list(v)); _,aa,_,_=self._evaluate(tt); gg=self._pack(aa); return [g-z for g,z in zip(gg,v)]
                def project(arr):
                    # Q, Q*T and component mass flows must remain nonnegative; TA flow may be signed.
                    a=arr.copy(); full,_=self._vector_layout(); idx=0
                    for _r in self.recycles:
                        a[idx]=max(0.0,a[idx]); idx+=1; a[idx]=max(0.0,a[idx]); idx+=1
                        if full:
                            for _ in SPECIES: a[idx]=max(0.0,a[idx]); idx+=1
                            idx+=1; a[idx]=max(0.0,a[idx]); idx+=1
                        else: a[idx]=max(0.0,a[idx]); idx+=1
                    return a
                jr=solve_jfnk(res,x0,scales=base_scales,residual_scales=base_scales,project=project,max_newton=10,gmres_max=min(28,len(x0)))
                if jr.converged:
                    tears=self._unpack(jr.x); passes,actual,products,rejects=self._evaluate(tears)
                    return self._finalize(passes,actual,products,rejects,True,it+jr.newton_iterations,"JFNK/GMRES",jr.residual_norm,{"residual_history":history,"jfnk":jr.__dict__})
                mixer.reset(); stagnation=0
        raise FlowsheetConvergenceError(f"RO flowsheet recycle did not converge after {max_iter} outer iterations. Last scaled residual={prev:.3e}.")

    def _finalize(self,passes,recycles,products,rejects,converged,iterations,method,residual_norm,diagnostics):
        qprod=sum(x.flow_m3h for x in products); qreject=sum(x.flow_m3h for x in rejects); water_close=self.external_feed.flow_m3h-qprod-qreject
        comp_close={}
        if self.external_feed.full_chemistry:
            feed=normalize_composition(self.external_feed.composition_mg_l or {})
            for sp in SPECIES:
                incoming=self.external_feed.flow_m3h*feed.get(sp,0.0)
                outgoing=sum(s.flow_m3h*(s.composition_mg_l or {}).get(sp,0.0) for s in products+rejects)
                comp_close[sp]=incoming-outgoing
        return FlowsheetResult(converged,iterations,method,float(residual_norm),passes,recycles,products,rejects,self.external_feed,
                               qprod/max(self.external_feed.flow_m3h,1e-12),water_close,comp_close,diagnostics)


def pass_from_payload(data: dict[str,Any], index:int) -> Pass:
    split = None

    if (
        isinstance(data.get("split_permeate"), dict)
        and data["split_permeate"].get("enabled")
    ):
        raw = data["split_permeate"]

        split = SplitPermeateConfig(
            int(raw.get("interface_after_element") or 0),
            float(raw.get("zone_a_backpressure_bar") or 0),
            float(raw.get("zone_b_backpressure_bar") or 0),
            True,
        )

    raw_stages = data.get("stages")
    stages: list[Stage] = []

    if isinstance(raw_stages, list) and raw_stages:
        for i, row in enumerate(raw_stages, 1):
            if not isinstance(row, dict):
                raise ValueError(
                    f"Pass {index+1} Stage {i}: invalid stage definition."
                )

            stages.append(
                Stage(
                    vessels=int(row.get("vessels") or 0),
                    elements_per_vessel=int(
                        row.get("elements_per_vessel") or 7
                    ),
                    membrane_id=str(
                        row.get("membrane_id")
                        or data.get("membrane_id")
                        or ""
                    ),
                    permeate_pressure_bar=float(
                        row.get(
                            "permeate_pressure_bar",
                            data.get("permeate_pressure_bar", 0),
                        )
                        or 0
                    ),
                    interstage_boost_bar=float(
                        row.get("interstage_boost_bar") or 0
                    ),
                )
            )

    legacy_membrane = str(data.get("membrane_id") or "")
    legacy_vessels = int(data.get("vessels") or 0)
    legacy_epv = int(data.get("elements_per_vessel") or 7)

    if stages:
        legacy_membrane = legacy_membrane or stages[0].membrane_id
        legacy_vessels = legacy_vessels or stages[0].vessels
        legacy_epv = legacy_epv or stages[0].elements_per_vessel

    return Pass(
        pass_id=str(data.get("pass_id") or f"P{index+1}"),
        membrane_id=legacy_membrane,
        vessels=legacy_vessels,
        elements_per_vessel=legacy_epv,
        feed_pressure_bar=(
            None
            if data.get("feed_pressure_bar") in {None, ""}
            else float(data.get("feed_pressure_bar"))
        ),
        target_recovery=(
            None
            if data.get("target_recovery") in {None, ""}
            else float(data.get("target_recovery"))
        ),
        permeate_pressure_bar=float(
            data.get("permeate_pressure_bar") or 0
        ),
        pump_efficiency=float(data.get("pump_efficiency") or .85),
        motor_efficiency=float(data.get("motor_efficiency") or .97),
        vfd_efficiency=float(data.get("vfd_efficiency") or .97),
        fouling_factor=float(data.get("fouling_factor") or 1),
        salt_passage_factor=float(
            data.get("salt_passage_factor") or 1
        ),
        permeate_to_next_fraction=float(
            data.get("permeate_to_next_fraction", 1.0)
        ),
        split_permeate=split,
        stages=stages,
    )


def recycle_from_payload(data:dict[str,Any],index:int)->RecycleLink:
    return RecycleLink(link_id=str(data.get("link_id") or f"R{index+1}"),source_pass=str(data.get("source_pass") or ""),source_port=str(data.get("source_port") or "concentrate"),destination_pass=str(data.get("destination_pass") or "P1"),destination=str(data.get("destination") or "suction"),
                       fraction=None if data.get("absolute_flow_m3h") not in {None,""} else float(data.get("fraction",1.0)),absolute_flow_m3h=None if data.get("absolute_flow_m3h") in {None,""} else float(data.get("absolute_flow_m3h")),enabled=bool(data.get("enabled",True)))


def solve_payload(payload:dict[str,Any], *, effective_tier:str="platinum") -> dict[str,Any]:
    passes=[pass_from_payload(x,i) for i,x in enumerate(payload.get("passes") or [])]
    limits={"entry":3,"silver":8,"gold":8,"platinum":8}; tier=str(effective_tier or "entry").lower()
    if len(passes)>limits.get(tier,3): raise PermissionError(f"{tier.title()} tier permits up to {limits.get(tier,3)} RO passes.")
    if any(p.split_permeate and p.split_permeate.enabled for p in passes) and tier not in {"gold","platinum"}: raise PermissionError("Split-partial permeate requires Gold or Platinum tier.")
    feed=stream_from_payload(payload.get("external_feed") or {})
    recycles=[recycle_from_payload(x,i) for i,x in enumerate(payload.get("recycles") or [])]
    result=Flowsheet(feed,passes,recycles).solve(max_iter=int(payload.get("max_iterations") or 30),method=str(payload.get("solver") or "auto"))
    return result.to_dict()
