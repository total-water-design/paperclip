from html import escape

from app import app
from suite_catalog import public_product_catalog


def _contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def test_public_routes_render_and_product_ctas_match_status():
    client = app.test_client()
    for path in ('/', '/platform', '/applications', '/sample-reports', '/privacy', '/applications/ro', '/applications/bio'):
        response = client.get(path)
        assert response.status_code == 200, path
    assert b'Start a design' in client.get('/applications/ro').data
    assert b'Follow development' in client.get('/applications/bio').data


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
                   'Sample reports are planned.', '500 engineering hours/year',
                   'Built to Show Its Work.', 'More Engineering. Less Re-Engineering.'):
        assert phrase in home
    platform = client.get('/platform').get_data(as_text=True)
    for phrase in ('The Shared Project Foundation',
                   'Preserve Meaning at Every Handoff', 'Progressive Integration, Clearly Disclosed',
                   'The Complete Engineering Workflow Being Built'):
        assert phrase in platform
    ro = client.get('/applications/ro').get_data(as_text=True)
    for phrase in ('No continuous fresh-feed mixing into the concentrating inventory',
                   'Fresh make-up enters while permeate is produced', 'Entitlement is not engineering eligibility',
                   'TDS-only mass balance does not certify chemistry feasibility'):
        assert phrase in ro


def test_public_maturity_and_evidence_disclosures_are_actual_http_content():
    client = app.test_client()
    ro = client.get('/applications/ro').get_data(as_text=True)
    for phrase in ('Conventional RO — current', 'True Batch RO — preview',
                   'Semi-Batch RO — under validation', 'Availability does not make every mode or ERD path current'):
        assert phrase in ro
    pretreatment = client.get('/applications/pretreatment').get_data(as_text=True)
    for phrase in ('3–9 h focused CEB/CIP study', '6–20 h conceptual train is planned-engine scope',
                   'coagulation, sludge thickening and filter press', 'No unpublished cleaner is auto-populated'):
        assert phrase in pretreatment
    bio = client.get('/applications/bio').get_data(as_text=True)
    assert 'BOD/COD/TSS cannot infer ions' in bio
    assert 'gross-to-net flux, cycles/downtime, membrane area, N+1 trains' in bio
    zld = client.get('/applications/zld').get_data(as_text=True)
    assert '280–305 K, 35,000–95,000 mg/L, Reynolds number 45–90 and Prandtl number 5–10' in zld
    balance = client.get('/applications/balance').get_data(as_text=True)
    assert 'does not average pH, infer partitioning, invent mass or hide a non-converged recycle' in balance
    economics = client.get('/applications/economics').get_data(as_text=True)
    assert 'No silent 1:1 conversion is used' in economics
    reports = client.get('/sample-reports').get_data(as_text=True)
    assert 'not currently available' in reports
    assert 'View sample reports' not in reports


def test_route_seo_and_theme_contract_are_rendered():
    client = app.test_client()
    ro = client.get('/applications/ro').get_data(as_text=True)
    platform = client.get('/platform').get_data(as_text=True)
    assert 'Total RO Design | Conventional, Batch and Semi-Batch RO Software' in ro
    assert 'Connected Water Engineering Platform | Total Water Design Suite' in platform
    assert 'rel="canonical"' in ro and 'property="og:title"' in ro
    nav = client.get('/').get_data(as_text=True)
    assert 'theme-toggle' not in nav
    script = open('static/public_website.js', encoding='utf-8').read()
    assert "twds-public-theme" not in script and "dataset.theme" not in script
    assert "localStorage" not in script and "prefers-color-scheme" not in script


def test_public_contrast_tokens_and_favicon_are_runtime_contracts():
    css = open('static/public_website.css', encoding='utf-8').read()
    assert '--suite-cyan:#004c60!important' in css
    assert '--suite-eyebrow:#005f73' in css
    assert 'html[data-theme="dark"]' not in css
    assert '--suite-eyebrow:#8ee9f2' not in css
    assert 'linear-gradient(135deg,#005b73,#004c60)' in css
    for foreground, background in (('#004c60', '#f5f9fc'), ('#005f73', '#f5f9fc'),
                                   ('#75e2ef', '#0c1722'), ('#75e2ef', '#142535'),
                                   ('#8ee9f2', '#0c1722'), ('#8ee9f2', '#142535')):
        assert _contrast_ratio(foreground, background) >= 4.5

    client = app.test_client()
    for path in ('/', '/platform', '/applications', '/applications/bio', '/applications/zld'):
        assert 'totalrodesign_icon.ico' in client.get(path).get_data(as_text=True)
    assert client.get('/static/totalrodesign_icon.ico').status_code == 200


def test_public_handoff_bio_and_zld_disclosures_are_actual_http_content():
    client = app.test_client()
    platform = client.get('/platform').get_data(as_text=True)
    for phrase in ('Source Water → Pretreatment', 'Pretreatment → Membranes/Bio',
                   'Membranes/Bio → Reuse', 'Concentrate/residual → ZLD',
                   'Development handoffs do not establish current customer connectivity'):
        assert phrase in platform
    system = client.get('/applications/system_integration').get_data(as_text=True)
    assert 'development handoffs do not establish current customer connectivity' in system
    balance = client.get('/applications/balance').get_data(as_text=True)
    assert 'Direct specialist adapters and customer connectivity are planned/deferred' in balance
    bio = client.get('/applications/bio').get_data(as_text=True)
    for phrase in ('MBBR, SBR, anaerobic treatment', 'active versus installed area',
                   'offline peak flux', '1–4 h basis/fractionation', '3–7 h MBR planning',
                   '6–18 h overall concept'):
        assert phrase in bio
    assert '10–28 h detailed MBR planning' not in bio
    zld = client.get('/applications/zld').get_data(as_text=True)
    for phrase in ('separately validated design U', 'never silently extrapolated',
                   'mother-liquor recycle/purge', 'forced-circulation duty',
                   'equipment/customer-release validation', 'Tube mechanical design is vendor scope',
                   'Explore the engineering preview', 'Follow development'):
        assert phrase in zld
