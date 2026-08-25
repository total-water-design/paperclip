from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

from auth import user_can_access_product
from suite_catalog import (
    PRODUCT_BY_ID,
    PRODUCTS,
    SUITE_HEADLINE,
    SUITE_TAGLINE,
    SUITE_VERSION,
    product_catalog,
    status_label,
)

ROOT = Path(__file__).resolve().parents[1]

LEGACY_PRODUCTS = {
    "pretreatment": ("Total Pretreatment Design", "design", "coming_soon", "/pretreatment", "#8B5A00", "branding/suite/total_pretreatment_design_icon_512.png"),
    "bio": ("Total Bio Design", "design", "in_development", "/apps/bio/", "#0E7A55", "branding/suite/total_bio_design_icon_512.png"),
    "ro": ("Total RO Design", "design", "available", "/ro", "#1769D2", "branding/suite/total_ro_design_icon_512.png"),
    "zld": ("Total ZLD Design", "design", "in_development", "/zld/", "#6B4FD3", "branding/suite/total_zld_design_icon_512.png"),
    "balance": ("Total Water Balance", "analysis", "coming_soon", "/balance", "#007A86", "branding/suite/total_water_balance_icon_512.png"),
    "economics": ("Total Water Economics", "analysis", "coming_soon", "/economics-suite", "#985A00", "branding/suite/total_water_economics_icon_512.png"),
    "system_integration": ("Total Water Design — System Integration & Optimization", "analysis", "in_development", "/integrate", "#3651B5", "branding/suite/total_water_design_system_integration_icon_512.png"),
    "academy": ("Total Water Academy", "education", "in_development", "/academy", "#1A7F8E", "branding/suite/total_water_academy_icon.svg"),
}


def _render(template_name: str, products: list[dict], *, authenticated: bool = False) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)

    def fake_url_for(endpoint: str, **values) -> str:
        if endpoint == "static":
            return "/static/" + str(values["filename"])
        return "/" + endpoint.replace(".", "/")

    env.globals["url_for"] = fake_url_for
    env.globals["csrf_token"] = lambda: "test-csrf"
    user = SimpleNamespace(
        is_authenticated=authenticated,
        is_admin=False,
        full_name="Portfolio User",
        organization="TWDS Test",
        role="user",
    )
    return env.get_template(template_name).render(
        products=products,
        status_label=status_label,
        suite_headline=SUITE_HEADLINE,
        suite_tagline=SUITE_TAGLINE,
        auth_enabled=authenticated,
        current_user=user,
        config={"SUITE_VERSION": SUITE_VERSION},
        twds_whats_new={"recently_updated": [], "roadmap": [], "commercial_launch_window": ""},
    )


def _dashboard_products() -> list[dict]:
    output = []
    for product in PRODUCTS:
        item = product.as_dict()
        is_ro = product.product_id == "ro"
        item.update(
            accessible=is_ro,
            entitlement={
                "enabled": is_ro,
                "tier": "entry",
                "status": "active" if is_ro else "inactive",
                "starts_at": None,
                "expires_at": None,
                "current": is_ro,
            },
        )
        output.append(item)
    return output


def _card_containing(html: str, text: str) -> str:
    marker = html.index(text)
    start = html.rfind("<article", 0, marker)
    end = html.index("</article>", marker) + len("</article>")
    return html[start:end]


def test_post_treatment_catalog_definition_and_order():
    source = (ROOT / "suite_catalog.py").read_text(encoding="utf-8")
    compile(source, "suite_catalog.py", "exec")

    product = PRODUCT_BY_ID["post_treatment"]
    assert product.product_id == "post_treatment"
    assert product.name == "Total Post-Treatment Design"
    assert product.short_name == "Post-Treatment"
    assert product.category == "design"
    assert product.status == "in_development"
    assert product.route == "/post-treatment/"
    assert product.accent == "#455468"
    assert product.icon_asset == "branding/suite/total_water_design_suite_icon_512.png"
    assert product.logo_asset is None
    assert product.public_tiers == ()
    assert product.admin_preview_enabled is False
    assert product.launch_priority == 25
    assert [p.product_id for p in PRODUCTS] == [
        "pretreatment",
        "bio",
        "ro",
        "post_treatment",
        "zld",
        "balance",
        "economics",
        "system_integration",
        "academy",
    ]


def test_existing_catalog_products_are_preserved():
    for product_id, expected in LEGACY_PRODUCTS.items():
        product = PRODUCT_BY_ID[product_id]
        actual = (
            product.name,
            product.category,
            product.status,
            product.route,
            product.accent,
            product.icon_asset,
        )
        assert actual == expected


def test_post_treatment_brand_placeholder_exists_and_is_suite_owned():
    product = PRODUCT_BY_ID["post_treatment"]
    icon = ROOT / "static" / product.icon_asset
    assert icon.is_file()
    assert "total_water_design_suite" in product.icon_asset
    assert "pretreatment" not in product.icon_asset
    assert "bio" not in product.icon_asset
    assert "ro_design" not in product.icon_asset
    assert "zld" not in product.icon_asset


def test_public_landing_renders_in_development_without_launch_control():
    html = _render("suite_landing.html", product_catalog(), authenticated=False)
    card = _card_containing(html, "Total Post-Treatment Design")
    assert "In Development" in card
    assert "product-water stabilization" in card
    assert "calcite/CO2" in card
    assert "disinfection and corrosion-control capabilities will follow as validated" in card
    assert "/static/branding/suite/total_water_design_suite_icon_512.png" in card
    assert "suite-product-disabled" in card
    assert "Open application" not in card
    assert "Sign in to open" not in card
    assert "/post-treatment/" not in card


def test_suite_story_includes_post_treatment_without_overstating_handoffs():
    html = _render("suite_landing.html", product_catalog(), authenticated=False)
    assert "post-treatment and finished-water conditioning" in html
    assert "ZLD for concentrate and residuals where applicable" in html
    assert "The Suite is being built so validated stream data can move between designs" in html


def test_authenticated_dashboard_renders_disabled_post_treatment_card():
    html = _render("suite_dashboard.html", _dashboard_products(), authenticated=True)
    card = _card_containing(html, "Total Post-Treatment Design")
    assert "In Development" in card
    assert "In Development · no active launch control" in card
    assert "Open application" not in card
    assert "/post-treatment/" not in card


def test_post_treatment_access_fails_closed_for_users_and_admins():
    ordinary = SimpleNamespace(status="active", is_admin=False)
    admin = SimpleNamespace(status="active", is_admin=True)
    assert user_can_access_product(ordinary, "post_treatment") is False
    assert user_can_access_product(admin, "post_treatment") is False


def test_catalog_registration_does_not_import_specialist_runtime():
    source = (ROOT / "suite_catalog.py").read_text(encoding="utf-8")
    landing = (ROOT / "templates/suite_landing.html").read_text(encoding="utf-8")
    dashboard = (ROOT / "templates/suite_dashboard.html").read_text(encoding="utf-8")
    combined = "\n".join((source, landing, dashboard))
    for forbidden in (
        "from total_post_treatment",
        "import total_post_treatment",
        "app/total-post-treatment-design",
        "register_post_treatment",
    ):
        assert forbidden not in combined


def test_existing_responsive_catalog_layout_contract_is_unchanged():
    css = (ROOT / "static/suite.css").read_text(encoding="utf-8")
    assert ".suite-product-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))" in css
    assert "@media(max-width:1180px){.suite-product-grid{grid-template-columns:repeat(2,minmax(0,1fr))}" in css
    assert ".suite-product-grid,.suite-dashboard-grid,.suite-basis-grid{grid-template-columns:1fr}" in css
    assert ".status-in_development .suite-status-badge" in css
    assert "text-transform:uppercase" in css
