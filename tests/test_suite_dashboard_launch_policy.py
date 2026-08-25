from html import escape
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

from suite_catalog import PRODUCTS, PRODUCT_BY_ID, status_label

ROOT = Path(__file__).resolve().parents[1]


def _dashboard_products() -> list[dict]:
    products = []
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
        products.append(item)
    return products


def _render_dashboard(*, admin: bool) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)

    def fake_url_for(endpoint: str, **values) -> str:
        if endpoint == "static":
            return "/static/" + str(values["filename"])
        return "/" + endpoint.replace(".", "/")

    env.globals["url_for"] = fake_url_for
    env.globals["csrf_token"] = lambda: "test-csrf"
    user = SimpleNamespace(
        is_authenticated=True,
        is_admin=admin,
        full_name="Suite Administrator" if admin else "Alpha Tester",
        organization="TWDS Validation",
        role="admin" if admin else "user",
    )
    return env.get_template("suite_dashboard.html").render(
        products=_dashboard_products(),
        current_user=user,
        status_label=status_label,
    )


def _card(html: str, name: str) -> str:
    marker = html.index(escape(name))
    start = html.rfind("<article", 0, marker)
    end = html.index("</article>", marker) + len("</article>")
    return html[start:end]


def test_catalog_declares_exact_current_admin_preview_set():
    enabled = {p.product_id for p in PRODUCTS if p.admin_preview_enabled}
    assert enabled == {"bio", "zld", "academy"}

    assert PRODUCT_BY_ID["bio"].status == "in_development"
    assert PRODUCT_BY_ID["bio"].route == "/apps/bio/"
    assert PRODUCT_BY_ID["zld"].status == "in_development"
    assert PRODUCT_BY_ID["zld"].route == "/zld/"
    assert PRODUCT_BY_ID["academy"].status == "in_development"
    assert PRODUCT_BY_ID["academy"].route == "/academy"

    for product_id in ("pretreatment", "post_treatment", "balance", "economics", "system_integration", "ro"):
        assert PRODUCT_BY_ID[product_id].admin_preview_enabled is False


def test_dashboard_consumes_catalog_preview_metadata_not_product_id_list():
    source = (ROOT / "templates/suite_dashboard.html").read_text(encoding="utf-8")
    assert "product.admin_preview_enabled" in source
    assert "['bio', 'zld']" not in source
    assert "['bio', 'zld', 'academy']" not in source
    assert "product.product_id in" not in source


def test_administrator_preview_launches_bio_zld_and_academy():
    html = _render_dashboard(admin=True)
    for product_id in ("bio", "zld", "academy"):
        product = PRODUCT_BY_ID[product_id]
        card = _card(html, product.name)
        assert "In Development" in card
        assert "Administrator preview" in card
        assert "Open application" in card
        assert f'href="{product.route}"' in card


def test_administrator_does_not_get_false_launch_surfaces():
    html = _render_dashboard(admin=True)
    for product_id in ("pretreatment", "post_treatment", "balance", "economics", "system_integration"):
        product = PRODUCT_BY_ID[product_id]
        card = _card(html, product.name)
        assert "no active launch control" in card
        assert "Open application" not in card
        assert f'href="{product.route}"' not in card


def test_total_ro_available_subscription_behavior_is_unchanged():
    html = _render_dashboard(admin=True)
    card = _card(html, PRODUCT_BY_ID["ro"].name)
    assert "Available" in card
    assert "Subscription" in card
    assert "Entry" in card
    assert "Administrator preview" not in card
    assert "Open application" in card
    assert 'href="/ro"' in card


def test_non_admin_does_not_receive_administrator_preview_controls():
    html = _render_dashboard(admin=False)
    for product_id in ("bio", "zld", "academy"):
        product = PRODUCT_BY_ID[product_id]
        card = _card(html, product.name)
        assert "In Development" in card
        assert "Administrator preview" not in card
        assert "Open application" not in card
        assert "no active launch control" in card

    ro = _card(html, PRODUCT_BY_ID["ro"].name)
    assert "Open application" in ro
    assert 'href="/ro"' in ro
