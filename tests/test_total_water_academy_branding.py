from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_academy_has_dedicated_suite_brand_assets():
    icon = ROOT / "static/branding/suite/total_water_academy_icon.svg"
    logo = ROOT / "static/branding/suite/total_water_academy_logo.svg"
    assert icon.is_file() and icon.stat().st_size > 1000
    assert logo.is_file() and logo.stat().st_size > 1000
    assert "Total Water Academy icon" in icon.read_text(encoding="utf-8")
    assert "Total Water Academy logo" in logo.read_text(encoding="utf-8")


def test_catalog_uses_academy_assets_and_authoritative_accent():
    catalog = read("suite_catalog.py")
    assert 'product_id="academy"' in catalog
    assert 'accent="#1A7F8E"' in catalog
    assert 'icon_asset="branding/suite/total_water_academy_icon.svg"' in catalog
    assert 'logo_asset="branding/suite/total_water_academy_logo.svg"' in catalog


def test_academy_runtime_does_not_reuse_suite_master_icon_as_product_icon():
    academy = read("academy.py")
    placement = read("academy_placement.py")
    expected = 'branding/suite/total_water_academy_icon.svg'
    assert expected in academy
    assert expected in placement
    assert 'app_icon_asset="branding/suite/total_water_design_suite_icon_128.png"' not in academy
    assert 'app_icon_asset="branding/suite/total_water_design_suite_icon_128.png"' not in placement


def test_brand_standard_preserves_suite_ownership_boundaries():
    text = read("docs/TOTAL_WATER_ACADEMY_BRAND_v1.0.md")
    assert "Suite master identity" in text
    assert "does **not** define a separate application font family" in text
    assert "professional engineering seal" in text
    assert "Suite Core responsibilities" in text
