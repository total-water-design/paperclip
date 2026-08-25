"""Native Total RO Design adoption of Suite Core UI/UX Contract v1.0.

The mature RO template remains authoritative.  This module injects only the
small RO-owned behavior adapters plus a narrowly scoped mobile compatibility
stylesheet.  It does not create a second shell/project bar, replace specialist
markup, change engineering calculations, or load Suite Core CSS over the RO
application.
"""
from __future__ import annotations

from flask import request

_CALCULATE_HOTFIX = '<script src="/static/ro_calculate_hotfix.js"></script>'
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
    if '</body>' in text:
        scripts = []
        if _CALCULATE_HOTFIX not in text:
            scripts.append(_CALCULATE_HOTFIX)
        if _SCRIPT not in text:
            scripts.append(_SCRIPT)
        if scripts:
            text = text.replace('</body>', '\n'.join(scripts) + '\n</body>', 1)
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
        'calculate_hotfix_js': '/static/ro_calculate_hotfix.js',
    }
    return app
