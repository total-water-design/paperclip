"""Native Total RO Design adoption of Suite Core UI/UX Contract v1.0.

The mature RO template remains authoritative. This module injects only the
accessibility/UI contract adapter and the narrowly scoped mobile compatibility
stylesheet. Calculation execution and state are owned natively by static/app.js.
"""
from __future__ import annotations

from flask import request

_SCRIPT = '<script src="/static/ro_suite_contract.js"></script>'
_MOBILE_CSS = '<link rel="stylesheet" href="/static/ro_mobile_compat.css">'
_MARKER = '<meta name="twds-ui-contract" content="1.0" data-twds-ro-contract="native">'


def _augment_html(text: str) -> str:
    if 'id="calculatorApp"' not in text or 'data-twds-ro-contract="native"' in text:
        return text
    if '</head>' in text:
        additions = []
        if _MOBILE_CSS not in text:
            additions.append(_MOBILE_CSS)
        additions.append(_MARKER)
        text = text.replace('</head>', '\n'.join(additions) + '\n</head>', 1)
    if '</body>' in text and _SCRIPT not in text:
        text = text.replace('</body>', _SCRIPT + '\n</body>', 1)
    return text


def register_ro_suite_ui_contract(app):
    """Install the non-structural RO-owned Contract v1.0 adapter."""
    if app.extensions.get('ro_suite_ui_contract_v1'):
        return app

    @app.after_request
    def _ro_suite_ui_contract_response(response):
        if request.method != 'GET' or response.status_code != 200:
            return response
        if 'text/html' not in response.headers.get('Content-Type', ''):
            return response
        try:
            text = response.get_data(as_text=True)
        except (UnicodeDecodeError, RuntimeError):
            return response
        augmented = _augment_html(text)
        if augmented != text:
            response.set_data(augmented)
            response.headers.pop('Content-Length', None)
        return response

    app.extensions['ro_suite_ui_contract_v1'] = {
        'contract': 'Suite Core UI/UX Contract v1.0',
        'mode': 'native-ro-adapter',
        'structural_dom_changes': False,
        'engineering_changes': False,
        'mobile_compat_css': '/static/ro_mobile_compat.css',
        'calculation_state_owner': '/static/app.js',
        'accessibility_contract_js': '/static/ro_suite_contract.js',
    }
    return app
