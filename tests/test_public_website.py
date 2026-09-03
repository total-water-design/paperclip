from html import escape

from app import app
from suite_catalog import public_product_catalog


def test_public_routes_render_and_product_ctas_match_status():
    client = app.test_client()
    for path in ('/', '/platform', '/applications', '/sample-reports', '/privacy', '/applications/ro', '/applications/bio'):
        response = client.get(path)
        assert response.status_code == 200, path
    assert b'Start a design' in client.get('/applications/ro').data
    assert b'Join the waitlist' in client.get('/applications/bio').data


def test_every_product_has_controlled_status_and_disclosures():
    client = app.test_client()
    for product in public_product_catalog():
        response = client.get(f"/applications/{product['product_id']}")
        body = response.get_data(as_text=True)
        assert escape(product['name']) in body
        assert 'Part of the Total Water Design Suite' in body
        assert 'Current capability' in body
        assert 'Development / planned capability' in body
        assert 'What it designs and supported configurations' in body
        assert product['what_it_designs'] in body
        assert product['time_range'] in body
        assert product['sample_report'] in body
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


def test_home_platform_and_ro_have_substantive_controlled_content():
    client = app.test_client()
    home = client.get('/').get_data(as_text=True)
    for phrase in ('Integrated Does Not Mean One Oversimplified Solver', '01 — Define the basis',
                   'See the Engineering—Not Only the Interface.', '500 engineering hours/year',
                   'Built to Show Its Work.', 'More Engineering. Less Re-Engineering.'):
        assert phrase in home
    platform = client.get('/platform').get_data(as_text=True)
    for phrase in ('The Shared Project Foundation', 'Each Application Owns Its Physics',
                   'Preserve Meaning at Every Handoff', 'Progressive Integration, Clearly Disclosed',
                   'The Complete Engineering Workflow Being Built'):
        assert phrase in platform
    ro = client.get('/applications/ro').get_data(as_text=True)
    for phrase in ('No continuous fresh-feed mixing into the concentrating inventory',
                   'Fresh make-up enters while permeate is produced', 'Entitlement is not engineering eligibility',
                   'TDS-only mass balance does not certify chemistry feasibility'):
        assert phrase in ro


def test_route_seo_and_theme_contract_are_rendered():
    client = app.test_client()
    ro = client.get('/applications/ro').get_data(as_text=True)
    platform = client.get('/platform').get_data(as_text=True)
    assert 'Total RO Design | Conventional, Batch and Semi-Batch RO Software' in ro
    assert 'Connected Water Engineering Platform | Total Water Design Suite' in platform
    assert 'rel="canonical"' in ro and 'property="og:title"' in ro
    nav = client.get('/').get_data(as_text=True)
    assert 'class="theme-toggle"' in nav
    script = open('static/public_website.js', encoding='utf-8').read()
    assert "twds-public-theme" in script and "dataset.theme" in script
