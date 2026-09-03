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
    admin_preview_enabled: bool = False
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
        admin_preview_enabled=True,
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
    # Dedicated Post-Treatment artwork is not yet published. Use the official
    # Suite master icon as a neutral portfolio placeholder until dedicated
    # Post-Treatment branding is approved; never borrow another product icon.
    ProductDefinition(
        product_id="post_treatment",
        name="Total Post-Treatment Design",
        short_name="Post-Treatment",
        category="design",
        status="in_development",
        route="/post-treatment/",
        accent="#455468",
        icon_asset="branding/suite/total_water_design_suite_icon_512.png",
        logo_asset=None,
        description=(
            "Engineering tools in development for product-water stabilization, remineralization, blending, "
            "pH and alkalinity adjustment, calcite/CO2 foundations, and finished-water conditioning after "
            "membrane treatment; disinfection and corrosion-control capabilities will follow as validated."
        ),
        launch_priority=25,
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
        admin_preview_enabled=True,
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
    ProductDefinition(
        product_id="academy",
        name="Total Water Academy",
        short_name="Academy",
        category="education",
        status="in_development",
        route="/academy",
        accent="#1A7F8E",
        icon_asset="branding/suite/total_water_academy_icon.svg",
        logo_asset="branding/suite/total_water_academy_logo.svg",
        description="Learn water-treatment engineering by completing progressive concepts, quizzes and hands-on design missions in the Total Water Design Suite.",
        admin_preview_enabled=True,
        launch_priority=70,
    ),
)

PRODUCT_BY_ID: Mapping[str, ProductDefinition] = {product.product_id: product for product in PRODUCTS}

# This is the single customer-facing status source.  Public routes, cards and
# product-page badges read the ProductDefinition rather than maintaining copy
# of statuses in templates.
PUBLIC_PRODUCT_IDS = ("ro", "pretreatment", "bio", "zld", "balance", "economics", "system_integration")

PUBLIC_PRODUCT_COPY: Mapping[str, Mapping[str, object]] = {
    "ro": {"tagline": "Reverse osmosis design beyond the conventional array.", "current": ["Conventional RO plant design", "Element, stage and system results", "Cases, hydraulic review and engineering reports"], "development": ["True Batch RO and Semi-Batch RO release labels are synchronized to the deployed entitlement.", "Advanced workflows remain subject to their stated maturity label."], "inputs": "Feed-water chemistry, membrane selection, duty, limits and operating basis.", "outputs": "Traceable membrane, hydraulic, energy and report outputs.", "assumptions": "Engineer-supplied design basis, membrane data and operating constraints.", "limitations": "Results require engineering review, vendor limits and project-specific verification.", "integration": "Available application in the Suite integration foundation; automatic whole-train handoffs are not implied."},
    "pretreatment": {"tagline": "Build the pretreatment train the water requires.", "current": ["Engineering-preview pretreatment train foundation", "Reviewable feed-water and downstream-target basis"], "development": ["Clarification, flotation, filtration, dosing, residuals and dewatering coverage"], "inputs": "Raw-water quality, downstream targets and user assumptions.", "outputs": "Reviewable treatment-train basis and preliminary sizing context.", "assumptions": "Removal, cleaning and source-data assumptions remain visible.", "limitations": "Cleaner data are not endorsements; no generic removal guarantee is made.", "integration": "Designed to protect downstream processes as progressive handoffs mature."},
    "bio": {"tagline": "Biological treatment as a configurable process train.", "current": ["Process-family and treatment-train development foundation"], "development": ["Activated sludge, MBR and reuse process coverage under active validation"], "inputs": "Influent characteristics, treatment objectives and operating assumptions.", "outputs": "Preliminary process-train context and transparent assumptions.", "assumptions": "Configuration breadth is separate from validated solver coverage.", "limitations": "Not every catalog process is a complete released solver.", "integration": "Planned to exchange controlled stream context, not universal automated handoffs."},
    "zld": {"tagline": "Make concentrate management and residuals visible.", "current": ["Brine, recovered-water, solids and recycle design foundation"], "development": ["Forward osmosis, falling-film evaporation and crystallization screening workflows"], "inputs": "Brine properties, concentration targets, energy and recycle basis.", "outputs": "Screening outputs for water, solids, recycle and energy discussion.", "assumptions": "Vendor data, correlations and constraints must be stated for each case.", "limitations": "Screening is not final vendor equipment design; out-of-range cases need independent verification.", "integration": "Future concentration and recycle handoffs are progressive."},
    "balance": {"tagline": "Close the loop on where the water goes.", "current": ["Implemented engine foundation for stream lineage and residual diagnostics"], "development": ["Customer-facing plant balance workspace and recycle detection"], "inputs": "Named streams, flow, composition, units and recycle definitions.", "outputs": "Closure, residual and lineage diagnostics.", "assumptions": "Engine foundations do not by themselves establish customer availability.", "limitations": "Coming Soon: no customer availability is implied.", "integration": "Foundation for controlled cross-process context as applications mature."},
    "economics": {"tagline": "Compare design alternatives with assumptions in view.", "current": ["Economic-summary foundation and scenario framing"], "development": ["Capital, operating and lifecycle comparison workflows"], "inputs": "Scenario, energy, consumable, labor and user cost assumptions.", "outputs": "Transparent preliminary comparison summaries.", "assumptions": "Costs, escalation and operating conditions are user-supplied or explicitly sourced.", "limitations": "Not financial, tax, investment or bankability advice.", "integration": "Designed to receive controlled engineering summaries as the Suite evolves."},
    "system_integration": {"tagline": "System integration and optimization, built progressively.", "current": ["Shared project, stream, chemistry, unit, assumption and revision foundations"], "development": ["Whole-Suite reporting, visual flowsheets and system-level optimization"], "inputs": "Approved application outputs, shared assumptions and constraints.", "outputs": "Traceable integration context and future system trade-off views.", "assumptions": "Each application continues to own its physics and engineering scope.", "limitations": "In Development: no promise of universal automatic handoffs or optimization.", "integration": "Integration maturity is progressive and explicitly disclosed."},
}


def public_product_catalog() -> list[dict]:
    """Customer-facing seven-product catalog with controlled status and copy."""
    return [{**PRODUCT_BY_ID[product_id].as_dict(), **PUBLIC_PRODUCT_COPY[product_id]}
            for product_id in PUBLIC_PRODUCT_IDS]


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
