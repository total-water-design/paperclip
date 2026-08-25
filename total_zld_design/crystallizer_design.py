"""Crystallizer sizing and selection support for Total ZLD Design.

The sizing relations are anchored to ideal MSMPR population-balance concepts:
characteristic size = G*tau, moment-mean sizes L10/L21/L32/L43 = 1/2/3/4
multiples of G*tau, and tau = V/Q.  Equipment-type selection is intentionally
advisory: FC/DTB/Oslo/batch recommendations are heuristic engineering screening,
not a vendor design or a substitute for pilot data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

MeanSizeBasis = Literal["L10", "L21", "L32", "L43"]
Risk = Literal["low", "medium", "high"]
Priority = Literal["low", "medium", "high"]

_MEAN_FACTORS = {"L10": 1.0, "L21": 2.0, "L32": 3.0, "L43": 4.0}


@dataclass(frozen=True)
class MSMPRSizingResult:
    mean_size_basis: str
    target_mean_size_mm: float
    growth_rate_mm_h: float
    characteristic_size_mm: float
    residence_time_h: float
    slurry_throughput_m3_h: float
    working_volume_m3: float
    design_volume_m3: float
    suspension_density_kg_m3: float
    crystal_inventory_kg: float
    nominal_solids_withdrawal_kg_h: float
    volume_margin_fraction: float

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class CrystallizerSelectionInput:
    evaporation_required: bool = True
    scaling_fouling_risk: Risk = "high"
    viscosity_risk: Risk = "medium"
    solids_loading_risk: Risk = "high"
    large_crystal_priority: Priority = "medium"
    narrow_csd_priority: Priority = "medium"
    fines_control_priority: Priority = "medium"
    heat_sensitive: bool = False
    batch_flexibility_priority: Priority = "low"


@dataclass(frozen=True)
class CrystallizerRecommendation:
    crystallizer_type: str
    score: float
    rank: int
    strengths: tuple[str, ...]
    cautions: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


def ideal_msmpr_residence_time_h(
    target_mean_size_mm: float,
    growth_rate_mm_h: float,
    mean_size_basis: MeanSizeBasis = "L43",
) -> float:
    """Residence time needed for a target ideal-MSMPR mean crystal size.

    For size-independent growth with negligible birth size:
      L10 = G*tau, L21 = 2G*tau, L32 = 3G*tau, L43 = 4G*tau.
    """
    if target_mean_size_mm <= 0 or growth_rate_mm_h <= 0:
        raise ValueError("Target crystal size and growth rate must be positive.")
    try:
        factor = _MEAN_FACTORS[mean_size_basis]
    except KeyError as exc:
        raise ValueError(f"Unsupported mean-size basis: {mean_size_basis}") from exc
    return target_mean_size_mm / (factor * growth_rate_mm_h)


def size_ideal_msmpr(
    slurry_throughput_m3_h: float,
    target_mean_size_mm: float,
    growth_rate_mm_h: float,
    suspension_density_kg_m3: float,
    mean_size_basis: MeanSizeBasis = "L43",
    volume_margin_fraction: float = 0.15,
) -> MSMPRSizingResult:
    """Preliminary working-volume and solids-inventory sizing.

    ``suspension_density_kg_m3`` is crystal mass per slurry volume, not total
    slurry density.  The nominal solids withdrawal Q*M_T follows the ideal
    mixed-product-removal interpretation and should be replaced by the full
    solids mass balance when recycle/classification is modeled.
    """
    if slurry_throughput_m3_h <= 0:
        raise ValueError("Slurry throughput must be positive.")
    if suspension_density_kg_m3 < 0:
        raise ValueError("Suspension crystal density cannot be negative.")
    if volume_margin_fraction < 0:
        raise ValueError("Volume margin cannot be negative.")
    tau = ideal_msmpr_residence_time_h(target_mean_size_mm, growth_rate_mm_h, mean_size_basis)
    characteristic = growth_rate_mm_h * tau
    working = slurry_throughput_m3_h * tau
    design = working * (1.0 + volume_margin_fraction)
    inventory = working * suspension_density_kg_m3
    withdrawal = slurry_throughput_m3_h * suspension_density_kg_m3
    return MSMPRSizingResult(
        mean_size_basis=mean_size_basis,
        target_mean_size_mm=target_mean_size_mm,
        growth_rate_mm_h=growth_rate_mm_h,
        characteristic_size_mm=characteristic,
        residence_time_h=tau,
        slurry_throughput_m3_h=slurry_throughput_m3_h,
        working_volume_m3=working,
        design_volume_m3=design,
        suspension_density_kg_m3=suspension_density_kg_m3,
        crystal_inventory_kg=inventory,
        nominal_solids_withdrawal_kg_h=withdrawal,
        volume_margin_fraction=volume_margin_fraction,
    )


def _level(value: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}[value]


def recommend_crystallizer_types(data: CrystallizerSelectionInput) -> list[CrystallizerRecommendation]:
    """Rank common crystallizer configurations for screening.

    The ranking is deliberately qualitative.  It expresses established process
    trade-offs but does not claim that one configuration is universally best.
    Final selection requires species thermodynamics/kinetics, heat balance,
    hydraulic limits, materials, antiscalant carryover, and vendor/pilot review.
    """
    for value in (
        data.scaling_fouling_risk,
        data.viscosity_risk,
        data.solids_loading_risk,
        data.large_crystal_priority,
        data.narrow_csd_priority,
        data.fines_control_priority,
        data.batch_flexibility_priority,
    ):
        _level(value)  # validates literals at runtime

    candidates = {
        "Forced-circulation evaporative crystallizer": {
            "score": 0.0,
            "strengths": ["robust circulation for scaling/high-solids service", "well suited to evaporative ZLD duty"],
            "cautions": ["high recirculation power", "broad CSD unless classification/fines control is added"],
        },
        "Draft-tube-baffle (DTB) crystallizer": {
            "score": 0.0,
            "strengths": ["strong slurry suspension with controlled internal circulation", "supports fines control and larger product crystals"],
            "cautions": ["greater mechanical/process complexity", "classification performance is design-sensitive"],
        },
        "Oslo / classified growth crystallizer": {
            "score": 0.0,
            "strengths": ["favours growth on retained crystals", "good candidate when large/narrow product CSD is valuable"],
            "cautions": ["less forgiving of severe scaling/fouling", "requires reliable classification and manageable liquor rheology"],
        },
        "Batch stirred crystallizer": {
            "score": 0.0,
            "strengths": ["flexible for campaigns and variable feeds", "useful for kinetic development and specialty operation"],
            "cautions": ["cyclic production and variable CSD", "usually unattractive for large continuous ZLD baseload"],
        },
    }

    sf = _level(data.scaling_fouling_risk)
    vis = _level(data.viscosity_risk)
    solids = _level(data.solids_loading_risk)
    large = _level(data.large_crystal_priority)
    narrow = _level(data.narrow_csd_priority)
    fines = _level(data.fines_control_priority)
    batch = _level(data.batch_flexibility_priority)

    fc = candidates["Forced-circulation evaporative crystallizer"]
    fc["score"] += 4 if data.evaporation_required else 1
    fc["score"] += 2.0 * sf + 1.5 * solids + 1.0 * vis
    fc["score"] -= 0.5 * narrow
    if data.heat_sensitive:
        fc["score"] -= 2

    dtb = candidates["Draft-tube-baffle (DTB) crystallizer"]
    dtb["score"] += 2 if data.evaporation_required else 1
    dtb["score"] += 1.0 * solids + 1.5 * large + 2.0 * fines + 1.0 * narrow
    dtb["score"] -= 0.5 * sf + 0.5 * vis

    oslo = candidates["Oslo / classified growth crystallizer"]
    oslo["score"] += 0.5 if data.evaporation_required else 1.5
    oslo["score"] += 2.5 * large + 2.0 * narrow + 1.5 * fines
    oslo["score"] -= 1.5 * sf + 1.0 * vis + 0.5 * solids

    bt = candidates["Batch stirred crystallizer"]
    bt["score"] += 3.0 * batch
    bt["score"] += 1.5 if data.heat_sensitive else 0
    bt["score"] -= 2.0 if data.evaporation_required and batch == 0 else 0
    bt["score"] -= 1.0 * solids

    ranked = sorted(candidates.items(), key=lambda kv: (-float(kv[1]["score"]), kv[0]))
    return [
        CrystallizerRecommendation(
            crystallizer_type=name,
            score=round(float(info["score"]), 3),
            rank=index + 1,
            strengths=tuple(info["strengths"]),
            cautions=tuple(info["cautions"]),
        )
        for index, (name, info) in enumerate(ranked)
    ]


def crystallizer_design_capabilities() -> dict[str, object]:
    return {
        "status": "preliminary sizing + advisory configuration screening",
        "source_anchored": [
            "ideal MSMPR characteristic size G*tau",
            "L10/L21/L32/L43 = 1/2/3/4 times G*tau",
            "mean residence time tau = V/Q",
            "crystal inventory from suspension density times working volume",
        ],
        "selection_candidates": [
            "forced-circulation evaporative",
            "draft-tube-baffle",
            "Oslo/classified growth",
            "batch stirred",
        ],
        "selection_warning": "Ranking is engineering screening, not final vendor selection.",
        "required_before_final_design": [
            "species-specific solubility and supersaturation",
            "validated nucleation/growth kinetics",
            "antiscalant/impurity effects",
            "population-balance/CSD target",
            "evaporation and heat-transfer duty",
            "slurry rheology and circulation hydraulics",
            "materials/corrosion review",
            "classification/fines strategy",
            "pilot or vendor validation where warranted",
        ],
    }
