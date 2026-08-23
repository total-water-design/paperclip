from flask import Flask

from ro_suite_ui_contract import _augment_html, register_ro_suite_ui_contract


def test_augments_ro_calculator_once():
    html = '<html><head></head><body><main id="calculatorApp"></main></body></html>'
    out = _augment_html(html)
    assert 'data-twds-ro-contract="1"' in out
    assert '/static/suite_ui_tokens.css' in out
    assert '/static/ro_suite_contract.css' in out
    assert '/static/suite_application_shell.js' in out
    assert '/static/addons/ccro/ccro_addon.js' in out
    assert '/static/ro_suite_contract.js' in out
    assert out.index('/static/addons/ccro/ccro_addon.js') < out.index('/static/ro_suite_contract.js')
    assert _augment_html(out) == out


def test_does_not_touch_non_ro_pages():
    html = '<html><head></head><body><main id="suiteDashboard"></main></body></html>'
    assert _augment_html(html) == html


def test_contract_is_presentation_only():
    html = '<html><head></head><body><main id="calculatorApp"><form id="calcForm"><button id="calculateBtn">Calculate</button></form></main></body></html>'
    out = _augment_html(html)
    assert '<form id="calcForm">' in out
    assert '<button id="calculateBtn">Calculate</button>' in out
    assert out.count('id="calculatorApp"') == 1


def test_assets_are_injected_after_existing_app_markup():
    html = '<html><head><link rel="stylesheet" href="/static/style.css"></head><body><main id="calculatorApp"></main><script src="/static/app.js"></script></body></html>'
    out = _augment_html(html)
    assert out.index('/static/style.css') < out.index('/static/ro_suite_contract.css')
    assert out.index('/static/app.js') < out.index('/static/addons/ccro/ccro_addon.js')
    assert out.index('/static/addons/ccro/ccro_addon.js') < out.index('/static/ro_suite_contract.js')


def test_registered_flask_response_gets_contract_assets():
    app = Flask(__name__)

    @app.get('/ro')
    def ro():
        return '<html><head></head><body><main id="calculatorApp"></main><script src="/static/app.js"></script></body></html>'

    register_ro_suite_ui_contract(app)
    with app.test_client() as client:
        response = client.get('/ro')
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'data-twds-ro-contract="1"' in text
    assert '/static/addons/ccro/ccro_addon.js' in text
    assert '/static/ro_suite_contract.js' in text
