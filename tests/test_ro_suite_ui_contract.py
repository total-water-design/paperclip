from flask import Flask

from ro_suite_ui_contract import _augment_html, register_ro_suite_ui_contract


def test_augments_ro_calculator_once_without_structural_shell_assets():
    html = '<html><head></head><body><main id="calculatorApp"></main><script src="/static/app.js"></script></body></html>'
    out = _augment_html(html)
    assert 'data-twds-ro-contract="native"' in out
    assert '/static/ro_suite_contract.js' in out
    assert '/static/ro_mobile_compat.css' in out
    assert '/static/suite_ui_tokens.css' not in out
    assert '/static/suite_application_shell.js' not in out
    assert '/static/ro_suite_contract.css' not in out
    assert out.index('/static/ro_mobile_compat.css') < out.index('</head>')
    assert out.index('/static/app.js') < out.index('/static/ro_suite_contract.js')
    assert _augment_html(out) == out


def test_does_not_touch_non_ro_pages():
    html = '<html><head></head><body><main id="suiteDashboard"></main></body></html>'
    assert _augment_html(html) == html


def test_contract_preserves_existing_ro_markup_and_single_calculate_button():
    html = '<html><head></head><body><main id="calculatorApp"><form id="calcForm"><button class="primary" id="calculateBtn">Calculate</button></form><div id="fields"></div></main></body></html>'
    out = _augment_html(html)
    assert '<form id="calcForm">' in out
    assert 'id="calculateBtn"' in out
    assert 'id="fields"' in out
    assert out.count('id="calculateBtn"') == 1
    assert out.count('id="calculatorApp"') == 1


def test_registered_flask_response_gets_native_adapter_and_mobile_compat_css():
    app = Flask(__name__)

    @app.get('/ro')
    def ro():
        return '<html><head></head><body><main id="calculatorApp"></main><script src="/static/app.js"></script></body></html>'

    register_ro_suite_ui_contract(app)
    with app.test_client() as client:
        response = client.get('/ro')
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'data-twds-ro-contract="native"' in text
    assert '/static/ro_mobile_compat.css' in text
    assert '/static/ro_suite_contract.js' in text
    assert '/static/suite_application_shell.js' not in text
    assert '/static/ro_suite_contract.css' not in text


def test_registration_declares_no_structural_or_engineering_changes():
    app = Flask(__name__)
    register_ro_suite_ui_contract(app)
    state = app.extensions['ro_suite_ui_contract_v1']
    assert state['mode'] == 'native-ro-adapter'
    assert state['structural_dom_changes'] is False
    assert state['engineering_changes'] is False
    assert state['mobile_compat_css'] == '/static/ro_mobile_compat.css'



def test_augmented_ro_response_is_complete_idempotent_and_has_correct_content_length():
    app = Flask(__name__)

    @app.get('/ro')
    def ro():
        return '<html><head></head><body><main id="calculatorApp"></main><script src="/static/app.js"></script></body></html>'

    @app.after_request
    def _feedback_bridge(response):
        if 'text/html' in response.headers.get('Content-Type', ''):
            text = response.get_data(as_text=True)
            if 'data-test-feedback-bridge' not in text:
                text = text.replace(
                    '</body>',
                    '<script data-test-feedback-bridge="1"></script></body>',
                    1,
                )
                response.set_data(text)
                response.headers['Content-Length'] = str(len(response.get_data()))
        return response

    register_ro_suite_ui_contract(app)
    with app.test_client() as client:
        response = client.get('/ro')
    body = response.get_data()
    text = body.decode('utf-8')
    assert response.status_code == 200
    assert text.endswith('</html>')
    assert text.count('data-twds-ro-contract="native"') == 1
    assert text.count('/static/ro_suite_contract.js') == 1
    assert text.count('data-test-feedback-bridge') == 1
    assert int(response.headers['Content-Length']) == len(body)
    assert _augment_html(text) == text
