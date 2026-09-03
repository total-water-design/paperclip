from html import escape

from app import app
from suite_catalog import public_product_catalog


def test_public_routes_render_and_product_ctas_match_status():
    client = app.test_client()
    for path in ('/', '/platform', '/applications', '/sample-reports', '/privacy', '/applications/ro', '/applications/bio'):
        response = client.get(path)
        assert response.status_code == 200, path
    assert b'Open Total RO Design' in client.get('/applications/ro').data
    assert b'Notify me when available' in client.get('/applications/bio').data


def test_every_product_has_controlled_status_and_disclosures():
    client = app.test_client()
    for product in public_product_catalog():
        response = client.get(f"/applications/{product['product_id']}")
        body = response.get_data(as_text=True)
        assert escape(product['name']) in body
        assert 'Part of the Total Water Design Suite' in body
        assert 'Current capabilities' in body
        assert 'Development / planned' in body
        assert 'Assumptions and defaults' in body
        assert 'Known limitations' in body
        assert 'INTEGRATION ROLE AND MATURITY' in body


def test_public_copy_uses_safe_terminology_and_no_private_founder_details():
    body = app.test_client().get('/').get_data(as_text=True)
    assert 'Semi-Batch RO' in body
    assert 'Jerry Ross' not in body
    assert 'only platform' not in body.lower()
    assert 'support@totalrodesign.com' not in body


def test_mobile_navigation_is_a_real_button_and_reduced_motion_is_supported():
    body = app.test_client().get('/').get_data(as_text=True)
    assert 'class="nav-toggle" aria-expanded="false" aria-controls="public-nav"' in body
    css = open('static/public_website.css', encoding='utf-8').read()
    assert '@media (prefers-reduced-motion:reduce)' in css
