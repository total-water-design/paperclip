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
    "ro": {"tagline": "Reverse osmosis design beyond the conventional array.", "what_it_designs": "Conventional RO, True Batch RO, Semi-Batch RO, and eligible energy-recovery configurations from one membrane basis.", "current": ["Available conventional one- to four-stage design with one to eight elements per vessel", "Element-level flux, salt passage, pressure drop, chemistry and scaling screening", "Hydraulic-envelope cases, case comparison, project revisions and engineering reports where entitled"], "development": ["True Batch and Semi-Batch mode labels remain synchronized to the exact deployed release", "Advanced optimization remains subject to its stated release and validation maturity"], "configurations": ["Conventional single- and multistage RO", "True Batch: atmospheric PX, high-pressure tank, dual-compartment arrangements", "Semi-Batch: displacement, recirculation and purge sequence", "Eligible brackish and seawater isobaric, turbo, Pelton and interstage ERD alternatives"], "inputs": "Flow, temperature, pH, ionic analysis or TDS-only basis, membrane data, arrays, pressure limits, pump/ERD data, and batch or recirculation inventory assumptions.", "outputs": "Stage and element performance, recovery, permeate/concentrate quality, pressure/flux profile, pump and recovered power, SEC, warnings, cycle profile and report snapshot.", "assumptions": "Selected membrane and vendor data, stated operating duty and discrete quasi-steady increments for batch modes; full chemistry is needed to review high-recovery scaling.", "limitations": "Engineering review, codes, vendor curves, pretreatment strategy and project-specific verification remain required. TDS-only mass balance does not certify chemistry feasibility.", "integration": "Available application in the Suite foundation; automatic whole-train handoffs are not implied.", "time_range": "3–9 h conventional projection; 8–22 h advanced multi-configuration study", "sample_report": "Sample-report library: conventional RO, True Batch, Semi-Batch and brackish ERD examples are version-identified when published.", "release": "Total RO Design v0.25 · status Available", "seo_title": "Total RO Design | Conventional, Batch and Semi-Batch RO Software", "seo_description": "Design conventional RO, True Batch RO, Semi-Batch RO and eligible energy-recovery configurations with membrane, chemistry, hydraulic and energy analysis."},
    "pretreatment": {"tagline": "Build the pretreatment train the water requires.", "what_it_designs": "Feed-water-driven pretreatment basis, downstream protection targets, UF/MF cleaning and future treatment-train workflows.", "current": ["Engineering-preview feed-water and downstream-target basis", "Flexible unit ordering and technology-specific basis fields", "UF/MF screening with CEB/CIP chemical, volume, pump, heater, rinse and spent-solution bookkeeping"], "development": ["Clarification, flotation, filtration, dosing, hydraulics, sludge and dewatering workflows", "Validated removal performance and whole-train hydraulics remain under development"], "configurations": ["Source-water and target basis", "UF/MF configuration and cleaning-system screening", "Planned clarification, filtration, softening, residuals and recovery"], "inputs": "Design flow, source, temperature, pH, turbidity, TSS, SDI, TOC/DOC, metals, oil, algae risk and downstream targets.", "outputs": "Reviewable train basis, CEB/CIP consumption, preliminary pump/heater duties, rinse and spent-cleaning streams.", "assumptions": "Jar/pilot/plant data take precedence; cleaner and removal assumptions remain explicit.", "limitations": "Coming Soon. No generic removal guarantee, cleaner endorsement, final equipment selection or unsupported value is implied.", "integration": "Designed to protect downstream processes; treated-water, additions and waste context may be handed off as maturity permits.", "time_range": "3–9 h focused UF/MF cleaning study; 6–20 h conceptual train", "sample_report": "UF/MF CEB/CIP design-basis sample state: planned publication.", "release": "Status Coming Soon · engineering-preview scope", "seo_title": "Total Pretreatment Design | Water Pretreatment Engineering Software", "seo_description": "Build feed-water-driven pretreatment trains with UF/MF configuration, cleaning-system design and future treatment-train workflows."},
    "bio": {"tagline": "Biological treatment as a configurable process train.", "what_it_designs": "Municipal and industrial biological-treatment concepts from influent characterization through aeration, sludge, MBR planning and reuse context.", "current": ["In-development process-family and treatment-train foundation", "MBR equipment-planning basis with transparent historical defaults", "Influent, treatment objective and assumption context"], "development": ["Activated sludge, MBR, reuse, aeration and residuals coverage under validation", "Complete validated solver coverage is not claimed for every catalog process"], "configurations": ["Conceptual biological train", "MBR equipment planning", "Planned activated sludge, reuse and downstream membrane handoff"], "inputs": "Influent flow, BOD/COD, TSS, nutrients, temperature, targets, operating assumptions and MBR availability basis.", "outputs": "Preliminary train context, process/MBR planning values, energy and residuals framing with visible assumptions.", "assumptions": "Configuration breadth is separate from validated solver coverage; historical flux defaults are editable assumptions.", "limitations": "In Development. Not an OEM guarantee or complete released solver; ionic chemistry remains necessary for RO reuse evaluation.", "integration": "Designed to provide treated-effluent and sludge context; receiving applications retain their own physics.", "time_range": "6–18 h conceptual biological-treatment study", "sample_report": "Biological process and MBR planning sample state: planned publication.", "release": "Status In Development", "seo_title": "Total Bio Design | Biological Wastewater Treatment Design Software", "seo_description": "Configure biological treatment trains, aeration, sludge and MBR planning in a traceable engineering workflow."},
    "zld": {"tagline": "Make the brine path visible.", "what_it_designs": "Concentrate management, brine pre-concentration, thermal screening, crystallization and solids pathways.", "current": ["Engineering-preview project/feed basis, ionic input and mass-balance streams", "Forward-osmosis regression foundation and configurable train state", "FFE screening with warnings and preliminary energy/equipment summaries"], "development": ["Arbitrary-order coupled train, multi-effect energy cascade and rigorous high-molality properties", "Multi-salt crystallization and optimization after model validation"], "configurations": ["FO pre-concentration", "Falling-film evaporator screening", "Crystallization and recovered-water/solids pathways"], "inputs": "Brine flow, composition, concentration target, energy/recycle basis, tube geometry and vendor or user property assumptions.", "outputs": "Screening water/solids/recycle/energy discussion, mass balance, duty, area, tube count and warnings.", "assumptions": "Vendor data, correlation applicability and constraints are stated per case.", "limitations": "In Development. FFE correlation is limited to its disclosed range; no full MEE cascade or final mechanical exchanger design.", "integration": "Selected concentrate or residual streams may form a downstream ZLD basis with preserved provenance and maturity.", "time_range": "8–28 h ZLD screening and configuration study", "sample_report": "ZLD falling-film evaporator screening sample state: planned publication.", "release": "Status In Development · FO/FFE engineering preview and screening", "seo_title": "Total ZLD Design | Brine Concentration and Crystallization Software", "seo_description": "Evaluate brine concentration, thermal screening, crystallization and solids pathways with disclosed applicability boundaries."},
    "balance": {"tagline": "Know where every cubic metre and component goes.", "what_it_designs": "Plant topology, stream lineage, closure, recycle accounting and facility-level diagnostics without replacing specialist calculations.", "current": ["Implemented engine foundation for canonical WaterStream v0.6 input and typed topology", "Graph validation, lineage, recycle detection and component/H2O/TOTH closure", "Unit/facility residual diagnostics, recovery and fail-closed supported aqueous recycle"], "development": ["Customer-facing workspace, Project Library persistence, direct specialist adapters and report provider", "Production deployment remains deferred"], "configurations": ["Facility topology", "Closure and residual diagnostics", "Recycle/reuse accounting and stream/Sankey payload foundation"], "inputs": "Named streams, flow, component composition, units, process nodes, stream roles and recycle definitions.", "outputs": "Closure, residual, lineage, recovery and water-disposition diagnostics.", "assumptions": "Specialist owners declare transformations; engine foundation alone does not establish customer availability.", "limitations": "Coming Soon. Closure does not validate specialist physics or solve chemistry; unsupported recycle behavior fails closed.", "integration": "Foundation for controlled context as applications mature; customer-facing direct adapters are deferred.", "time_range": "3–12 h plant-wide balance and reconciliation study", "sample_report": "Plant-wide stream closure sample state: planned publication.", "release": "Status Coming Soon · implemented engine foundation", "seo_title": "Total Water Balance | Plant-Wide Water and Component Balance Software", "seo_description": "Assemble stream topology, closure, lineage and recycle diagnostics while preserving specialist calculation ownership."},
    "economics": {"tagline": "Connect process design to the economic decision.", "what_it_designs": "Process-scope and project-level CAPEX/OPEX, lifecycle and preliminary finance comparisons with cost ownership and provenance.", "current": ["Validated development foundation for CAPEX hierarchy and multi-application summaries", "OPEX reconciliation, lifecycle NPV/LCOW screening and source/maturity context", "Construction spend, funding, reserves, taxes and tariff modelling as preliminary finance foundation"], "development": ["Shared FX service, automatic project linkage and jurisdiction-specific tax adapters", "Debt sculpting, cash sweep and hedging remain planned"], "configurations": ["Cost/lifecycle study", "Time-phased finance screen", "Process-to-project cost ownership and provenance"], "inputs": "Scenario, energy, consumables, labor, CAPEX/OPEX, dates, currency/source and user financial assumptions.", "outputs": "Transparent cost ownership, lifecycle summaries, preliminary finance metrics and reconciliation context.", "assumptions": "Costs, escalation and operating conditions are user-supplied or explicitly sourced and dated.", "limitations": "Coming Soon. Not financial, tax, investment or bankability advice; do not conflate LCOW, tariff, IRR or customer price.", "integration": "Designed to receive controlled specialist summaries; automatic project linkage is planned.", "time_range": "4–16 h cost/lifecycle study; 8–32 h time-phased finance case", "sample_report": "Lifecycle economics and project-finance screen sample state: planned publication.", "release": "Status Coming Soon · validated development foundation", "seo_title": "Total Water Economics | Water Project CAPEX, OPEX and Finance Software", "seo_description": "Compare process costs, lifecycle assumptions and preliminary finance context with transparent cost ownership."},
    "system_integration": {"tagline": "System integration and optimization, built progressively.", "what_it_designs": "Versioned specialist results, handoff readiness and whole-system alternatives on a consistent project basis.", "current": ["Shared project, stream, chemistry, unit, assumption and revision foundations", "Selected development handoffs and project/report snapshot concepts", "Readiness-gate design for versioned specialist results"], "development": ["Cross-application scenario matrix, whole-Suite reporting and visual flowsheets", "Automated whole-train assembly and system optimization remain planned/in development"], "configurations": ["Handoff readiness and lineage", "Whole-system alternative comparison", "Future optimization over validated specialist results"], "inputs": "Approved specialist outputs, full-precision stream state, assumptions, constraints, warnings, maturity and revision provenance.", "outputs": "Traceable integration context, readiness gaps and future system trade-off views.", "assumptions": "Each application retains its process physics; engineers select the cases, constraints and accepted maturity.", "limitations": "In Development. No universal automatic handoffs, whole-train assembly, optimization or automatic recommendation is promised.", "integration": "Integration coverage varies by application and release; deeper contracts are adopted progressively.", "time_range": "10–40 h multidisciplinary option study", "sample_report": "System comparison report state: planned publication.", "release": "Status In Development · platform foundation", "seo_title": "Water System Integration and Optimization | Total Water Design Suite", "seo_description": "Coordinate versioned specialist results, preserve lineage and compare whole-system alternatives with explicit maturity."},
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
