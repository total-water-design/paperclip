from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_academy_catalog_uses_validated_identity():
    catalog = read("suite_catalog.py")
    assert 'product_id="academy"' in catalog
    assert 'name="Total Water Academy"' in catalog
    assert 'category="education"' in catalog
    assert 'status="in_development"' in catalog
    assert 'route="/academy"' in catalog
    assert 'accent="#1A7F8E"' in catalog
    assert 'icon_asset="branding/suite/total_water_academy_icon.svg"' in catalog
    assert 'logo_asset="branding/suite/total_water_academy_logo.svg"' in catalog


def test_academy_brand_assets_are_present():
    icon = ROOT / "static/branding/suite/total_water_academy_icon.svg"
    logo = ROOT / "static/branding/suite/total_water_academy_logo.svg"
    assert icon.is_file()
    assert logo.is_file()
    assert "Total Water Academy icon" in icon.read_text(encoding="utf-8")
    assert "Total Water Academy logo" in logo.read_text(encoding="utf-8")


def test_public_portfolio_renders_education_group():
    landing = read("templates/suite_landing.html")
    assert "('education','Learning & Development','Applied water-treatment engineering education')" in landing
    assert "including Total Water Academy" in landing


def test_authenticated_portfolio_renders_education_group():
    dashboard = read("templates/suite_dashboard.html")
    assert "('education','Learning & Development','Applied water-treatment engineering education')" in dashboard
    assert "product.category == category" in dashboard


def test_in_development_academy_is_not_presented_as_publicly_available():
    landing = read("templates/suite_landing.html")
    catalog = read("suite_catalog.py")
    assert 'status="in_development"' in catalog
    assert "suite-product-disabled" in landing
    assert "product.product_id == 'ro'" in landing
