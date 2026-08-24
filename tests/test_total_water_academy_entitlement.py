from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_academy_is_registered_as_future_suite_product():
    catalog = read("suite_catalog.py")
    assert 'product_id="academy"' in catalog
    assert 'name="Total Water Academy"' in catalog
    assert 'status="in_development"' in catalog
    assert 'route="/academy"' in catalog


def test_academy_commercial_policy_is_configurable():
    text = read("suite_commercial.py")
    assert 'price_usd_cents=500' in text
    assert 'billing_cadence=""' in text
    assert 'precommercial_access_mode="approved_students"' in text
    assert 'student_free_access_enabled=True' in text
    assert 'commercial_active=False' in text


def test_academy_does_not_assume_billing_cadence():
    text = read("suite_commercial.py")
    template = read("templates/auth/admin_products.html")
    assert 'Billing cadence is intentionally undefined' in text
    assert 'Leave blank until explicitly approved' in template


def test_precommercial_access_requires_admin_entitlement():
    text = read("suite_commercial.py")
    assert 'ProductEntitlement' in text
    assert 'not entitlement.enabled' in text
    assert 'approved_students' in text
