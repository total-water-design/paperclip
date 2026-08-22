"""Total Water Design Suite product catalog and release-status vocabulary.

This module is intentionally independent from Flask/SQLAlchemy so the catalog can
be shared by the authenticated server, Windows launcher, tests, and future APIs.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Mapping

SUITE_NAME = "Total Water Design Suite"
SUITE_VERSION = "0.25"
SUITE_TAGLINE = "One connected engineering environment for water treatment design, analysis, and optimization."
SUITE_HEADLINE = "Design the complete water treatment train in one connected engineering environment."
SUITE_ENDORSEMENT = "Part of the Total Water Design Suite."

STATUS_ORDER: Mapping[str, int] = {
    "planned": 0,
    "coming_soon": 1,
    "in_development": 2,
    "early_access": 3,
    "beta": 4,
    "available": 5,
    "retired": -1,
}


@dataclass(frozen=True)
class ProductDefinition:
    product_id: str
    name: str
    short_name: str
    category: str
    status: str
    route: str
    accent: str
    icon_asset: str
    logo_asset: str | None
    description: str
    public_tiers: tuple[str, ...] = ()
    launch_priority: int = 100

    def as_dict(self) -> dict:
        data = asdict(self)
        data["public_tiers"] = list(self.public_tiers)
        return data


PRODUCTS: tuple[ProductDefinition, ...] = (
    ProductDefinition(
        product_id="pretreatment",
        name="Total Pretreatment Design",
        short_name="Pretreatment",
        category="design",
        status="coming_soon",
        route="/pretreatment",
        accent="#8B5A00",
        icon_asset="branding/suite/total_pretreatment_design_icon_512.png",
        logo_asset="branding/suite/total_pretreatment_design_logo.png",
        description="Design and evaluate upstream water-treatment and pretreatment processes before the membrane system.",
        launch_priority=20,
    ),
    ProductDefinition(
        product_id="bio",
        name="Total Bio Design",
        short_name="Bio",
        category="design",
        status="in_development",
        route="/apps/bio/",
        accent="#0E7A55",
        icon_asset="branding/suite/total_bio_design_icon_512.png",
        logo_asset="branding/suite/total_bio_design_logo.png",
        description="Engineering environment for biological wastewater treatment and process-performance evaluation.",
        launch_priority=10,
    ),
    ProductDefinition(
        product_id="ro",
        name="Total RO Design",
        short_name="RO",
        category="design",
        status="available",
        route="/ro",
        accent="#1769D2",
        icon_asset="branding/suite/total_ro_design_icon_512.png",
        logo_asset="branding/suite/total_ro_design_logo.png",
        description="Integrated membrane, water-chemistry, hydraulic and energy design for desalination and high-purity water systems.",
        public_tiers=("entry", "silver", "gold", "platinum"),
        launch_priority=0,
    ),
    ProductDefinition(
        product_id="zld",
        name="Total ZLD Design",
        short_name="ZLD",
        category="design",
        status="in_development",
        route="/zld/",
        accent="#6B4FD3",
        icon_asset="branding/suite/total_zld_design_icon_512.png",
        logo_asset="branding/suite/total_zld_design_logo.png",
        description="Engineering tools for concentrate management, brine concentration and zero-liquid-discharge process design.",
        launch_priority=30,
    ),
    ProductDefinition(
        product_id="balance",
        name="Total Water Balance",
        short_name="Water Balance",
        category="analysis",
        status="coming_soon",
        route="/balance",
        accent="#007A86",
        icon_asset="branding/suite/total_water_balance_icon_512.png",
        logo_asset="branding/suite/total_water_balance_logo.png",
        description="Connect process streams and evaluate plant-wide water, recycle, reject and material balances.",
        launch_priority=40,
    ),
    ProductDefinition(
        product_id="economics",
        name="Total Water Economics",
        short_name="Water Economics",
        category="analysis",
        status="coming_soon",
        route="/economics-suite",
        accent="#985A00",
        icon_asset="branding/suite/total_water_economics_icon_512.png",
        logo_asset="branding/suite/total_water_economics_logo.png",
        description="Compare capital, operating and lifecycle economics across treatment alternatives and design scenarios.",
        launch_priority=50,
    ),
    ProductDefinition(
        product_id="system_integration",
        name="Total Water Design — System Integration & Optimization",
        short_name="System Integration & Optimization",
        category="analysis",
        status="in_development",
        route="/integrate",
        accent="#3651B5",
        icon_asset="branding/suite/total_water_design_system_integration_icon_512.png",
        logo_asset="branding/suite/total_water_design_system_integration_logo.png",
        description="Bring individual process designs together to evaluate and optimize the complete water-treatment system.",
        launch_priority=60,
    ),
)

PRODUCT_BY_ID: Mapping[str, ProductDefinition] = {product.product_id: product for product in PRODUCTS}


def product_catalog() -> list[dict]:
    return [p.as_dict() for p in PRODUCTS]


def status_label(value: str) -> str:
    labels = {
        "planned": "Planned",
        "coming_soon": "Coming Soon",
        "in_development": "In Development",
        "early_access": "Early Access",
        "beta": "Beta",
        "available": "Available",
        "retired": "Retired",
    }
    return labels.get(str(value or "").strip().lower(), "Planned")
