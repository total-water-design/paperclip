"""Commercial tier vocabulary for Total ZLD Design.

The tier registry is intentionally separate from the engineering equations.  It
controls workflow/UI availability only.  Model maturity remains independent from
subscription tier: a Platinum user does not turn a screening correlation into a
validated physical model.
"""

from __future__ import annotations

from typing import Final

TIER_ORDER: Final[dict[str, int]] = {
    "entry": 0,
    "silver": 1,
    "gold": 2,
    "platinum": 3,
}

TIER_LABELS: Final[dict[str, str]] = {
    "entry": "Entry",
    "silver": "Silver",
    "gold": "Gold",
    "platinum": "Platinum",
}

# maturity values: live, screening, planned.
FEATURES: Final[dict[str, dict[str, str]]] = {
    "project_basis": {"label": "Project Basis", "minimum_tier": "entry", "maturity": "live"},
    "feed_chemistry": {"label": "Feed Chemistry", "minimum_tier": "entry", "maturity": "live"},
    "process_train": {"label": "Process Train", "minimum_tier": "entry", "maturity": "live"},
    "fo_design": {"label": "Forward Osmosis", "minimum_tier": "entry", "maturity": "live"},
    "thermal_concentration": {"label": "Thermal Concentration", "minimum_tier": "entry", "maturity": "screening"},
    "results": {"label": "Calculated Results", "minimum_tier": "entry", "maturity": "live"},
    "project_library": {"label": "Project Library", "minimum_tier": "entry", "maturity": "live"},
    "basic_report": {"label": "Basic Engineering Report", "minimum_tier": "entry", "maturity": "planned"},

    "crystallization": {"label": "Crystallization", "minimum_tier": "silver", "maturity": "screening"},
    "energy_utilities": {"label": "Energy & Utilities", "minimum_tier": "silver", "maturity": "screening"},
    "equipment_sizing": {"label": "Equipment Sizing", "minimum_tier": "silver", "maturity": "screening"},
    "multi_case": {"label": "Multiple Cases", "minimum_tier": "silver", "maturity": "planned"},
    "ro_zld_handoff": {"label": "RO → ZLD Stream Handoff", "minimum_tier": "silver", "maturity": "planned"},

    "advanced_chemistry": {"label": "Advanced High-Salinity Chemistry", "minimum_tier": "gold", "maturity": "planned"},
    "scenario_comparison": {"label": "Scenarios & Comparison", "minimum_tier": "gold", "maturity": "planned"},
    "advanced_crystallization": {"label": "Multi-Salt Crystallization", "minimum_tier": "gold", "maturity": "planned"},

    "optimization": {"label": "Process-Train Optimization", "minimum_tier": "platinum", "maturity": "planned"},
    "system_integration": {"label": "System Integration & Optimization", "minimum_tier": "platinum", "maturity": "planned"},
}


def tier_allows(tier: str, feature_id: str) -> bool:
    tier = str(tier or "entry").lower()
    required = FEATURES[feature_id]["minimum_tier"]
    return TIER_ORDER.get(tier, 0) >= TIER_ORDER[required]


def commercial_payload() -> dict:
    return {
        "tiers": [
            {"id": tier, "label": TIER_LABELS[tier], "rank": rank}
            for tier, rank in TIER_ORDER.items()
        ],
        "features": FEATURES,
        "principle": (
            "Tier gating controls workflow depth and optimization features; it does not "
            "change the underlying engineering equations or model validation status."
        ),
    }
