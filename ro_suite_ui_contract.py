"""Progressive Total RO Design adoption of Suite Core UI/UX Contract v1.0.

This module augments the mature RO customer interface at response time. It does
not replace the RO template or touch engineering calculations, APIs, reports,
entitlements, project storage or specialist workspaces.
"""
from __future__ import annotations

from flask import request

_STYLE_LINKS = (
    '<link rel="stylesheet" href="/static/suite_ui_tokens.css">',
    '<link rel="stylesheet" href="/static/ro_suite_contract.css">',
)
_SCRIPT_LINKS = (
    '<script src="/static/suite_application_shell.js"></script>',
    # CCRO is an additive RO workspace.  It must load after the host app.js
    # (already present in the template) and before the Suite-contract adapter.
    '<script src="/static/addons/ccro/ccro_addon.js"></script>',
    '<script src="/static/ro_suite_contract.js"></script>',
)


def _augment_html(text: str) -> str:
    if 'id="calculatorApp"' not in text or 'data-twds-ro-contract="1"' in text:
        return text
    styles = "\n".join(link for link in _STYLE_LINKS if link not in text)
    scripts = "\n".join(link for link in _SCRIPT_LINKS if link not in text)
    marker = '<meta name="twds-ui-contract" content="1.0" data-twds-ro-contract="1">'
    if '</head>' in text:
        text = text.replace('</head>', f'{marker}\n{styles}\n</head>', 1)
    if '</body>' in text:
        text = text.replace('</body>', f'{scripts}\n</body>', 1)
    return text


def register_ro_suite_ui_contract(app):
    """Install non-invasive shell augmentation for the Total RO calculator page."""
    if app.extensions.get('ro_suite_ui_contract_v1'):
        return app

    @app.after_request
    def _ro_suite_ui_contract_response(response):
        if request.method != 'GET' or response.status_code != 200:
            return response
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' not in content_type:
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
        'mode': 'progressive-adoption',
        'engineering_changes': False,
    }
    return app
