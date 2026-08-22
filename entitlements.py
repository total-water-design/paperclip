"""Central Total RO Design subscription-tier entitlement registry.

The current desktop alpha runs in an administrator preview context.  The same
registry is intentionally framework-neutral so a future authenticated server can
replace environment defaults with signed account claims without changing the
engineering modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

TIER_ORDER: Mapping[str, int] = {
    "entry": 0,
    "silver": 1,
    "gold": 2,
    "platinum": 3,
}

FEATURE_MIN_TIER: Mapping[str, str] = {
    # Entry — accurate manual membrane projection.
    "water_quality": "entry",
    "manual_plant_design": "entry",
    "hybrid_membrane_design": "entry",
    "basic_results": "entry",
    "basic_report": "entry",
    "project_save_load": "entry",
    "multi_pass": "entry",

    # Silver — professional manual design and hydraulic/pump study.
    "multi_case": "silver",
    "hydraulic_envelope": "silver",
    "case_comparison": "silver",
    "full_engineering_report": "silver",
    "vcmp_pump_selection": "silver",
    "advanced_recycle": "silver",

    # Gold — automatic design, ERD and economics.
    "advanced_design": "gold",
    "auto_design": "silver",
    "erd": "gold",
    "economics": "gold",
    "split_partial_permeate": "gold",

    # Platinum — large searches / portfolio-style analysis.
    "design_optimizer": "platinum",
    "scenario_matrix": "platinum",
    "background_optimizer": "platinum",
    "operations_normalization": "platinum",
}

FEATURE_LABELS: Mapping[str, str] = {
    "water_quality": "Water Quality",
    "manual_plant_design": "Plant Design",
    "hybrid_membrane_design": "Hybrid membrane design",
    "basic_results": "Results",
    "basic_report": "Basic projection report",
    "project_save_load": "Project save/load",
    "multi_pass": "Multi-pass RO",
    "multi_case": "Multiple cases",
    "hydraulic_envelope": "Hydraulic Envelope",
    "case_comparison": "Case comparison",
    "full_engineering_report": "Full Engineering Report",
    "vcmp_pump_selection": "VCMP pump database",
    "advanced_recycle": "Advanced recycle topology",
    "advanced_design": "Advance Design",
    "auto_design": "Auto Design",
    "erd": "Energy-recovery devices",
    "economics": "Economics",
    "split_partial_permeate": "Split-partial permeate",
    "design_optimizer": "Design Optimizer",
    "scenario_matrix": "Scenario Matrix",
    "background_optimizer": "Background Optimizer",
    "operations_normalization": "Operations / normalization",
}

# "stable" features are customer-visible when entitled.  "internal" entries
# are deliberately visible only in the administrator Platinum preview until
# their engineering/UI acceptance criteria are completed.
FEATURE_MATURITY: Mapping[str, str] = {
    **{feature: "stable" for feature in FEATURE_MIN_TIER},
    "scenario_matrix": "internal",
    "background_optimizer": "internal",
    "operations_normalization": "internal",
}


class EntitlementError(PermissionError):
    def __init__(self, feature_id: str, required_tier: str, effective_tier: str):
        self.feature_id = feature_id
        self.required_tier = required_tier
        self.effective_tier = effective_tier
        label = FEATURE_LABELS.get(feature_id, feature_id.replace("_", " ").title())
        super().__init__(
            f"{label} requires the {required_tier.title()} tier or higher "
            f"(current preview: {effective_tier.title()})."
        )


def normalize_tier(value: object, fallback: str = "entry") -> str:
    tier = str(value or "").strip().lower()
    return tier if tier in TIER_ORDER else fallback


def tier_allows(tier: object, feature_id: str) -> bool:
    effective = normalize_tier(tier)
    required = FEATURE_MIN_TIER.get(feature_id)
    if required is None:
        raise KeyError(f"Unknown Total RO Design feature entitlement: {feature_id}")
    return TIER_ORDER[effective] >= TIER_ORDER[required]


def clamp_preview_tier(requested: object, licensed_tier: object, role: object) -> str:
    licensed = normalize_tier(licensed_tier, "entry")
    if str(role or "").strip().lower() != "admin":
        # Customer accounts always use their signed/licensed entitlement.  A
        # request header or browser manipulation cannot elevate it.
        return licensed
    # Administrators are product testers: they must be able to emulate all four
    # customer experiences even when the administrative account itself is not
    # sold a commercial tier.  This changes only the effective preview for the
    # current session; it never changes the licensed account claim.
    return normalize_tier(requested, licensed)


@dataclass(frozen=True)
class EntitlementContext:
    role: str
    licensed_tier: str
    effective_tier: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def allows(self, feature_id: str) -> bool:
        if not tier_allows(self.effective_tier, feature_id):
            return False
        maturity = FEATURE_MATURITY.get(feature_id, "stable")
        return maturity == "stable" or self.is_admin

    def require(self, feature_id: str) -> None:
        if not self.allows(feature_id):
            raise EntitlementError(
                feature_id,
                FEATURE_MIN_TIER[feature_id],
                self.effective_tier,
            )

    def as_dict(self) -> dict:
        return {
            "role": self.role,
            "licensed_tier": self.licensed_tier,
            "effective_tier": self.effective_tier,
            "is_admin": self.is_admin,
            "tier_order": dict(TIER_ORDER),
            "features": {
                feature_id: {
                    "minimum_tier": minimum_tier,
                    "label": FEATURE_LABELS.get(feature_id, feature_id),
                    "maturity": FEATURE_MATURITY.get(feature_id, "stable"),
                    "allowed": self.allows(feature_id),
                }
                for feature_id, minimum_tier in FEATURE_MIN_TIER.items()
            },
        }
