"""Presentation and entitlement wiring for the Total RO Design CAPEX & OPEX workspace."""
from __future__ import annotations

import re


def register_ro_economic_ui(app, require_feature=None):
    """Load the additive workspace and preserve the existing economics entitlement."""
    if getattr(app, "_ro_economic_ui_registered", False):
        return app
    app._ro_economic_ui_registered = True

    if require_feature is not None:
        from flask import request

        @app.before_request
        def guard_ro_economic_summary_api():
            if request.path.startswith("/api/ro/economic-summary"):
                require_feature("economics")

    @app.after_request
    def inject_ro_economic_workspace(response):
        if response.mimetype != "text/html":
            return response
        text = response.get_data(as_text=True)
        if "ro_capex_opex.js" in text:
            return response
        match = re.search(
            r'<script[^>]+src=["\'][^"\']*/static/app\.js[^"\']*["\'][^>]*></script>',
            text,
            flags=re.I,
        )
        if not match:
            return response
        loader = '<script src="/static/ro_capex_opex.js"></script>\n'
        response.set_data(text.replace(match.group(0), loader + match.group(0), 1))
        return response

    return app
