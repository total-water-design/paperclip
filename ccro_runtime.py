"""Register the isolated Total RO Design CCRO engine and UI."""
from __future__ import annotations

UI_SCRIPT = "/static/addons/ccro/ccro_addon.js"

def register_ccro_runtime(app, calculations):
    from addons.ccro import register_ccro
    register_ccro(app, calculations)
    if getattr(app, "_totalro_ccro_ui_runtime_registered", False):
        return
    from flask import request

    @app.after_request
    def _inject_ccro_workspace_loader(response):
        if request.path != "/ro" or response.status_code != 200:
            return response
        if "text/html" not in str(response.headers.get("Content-Type", "")).lower():
            return response
        html=response.get_data(as_text=True)
        if UI_SCRIPT in html or "</body>" not in html:
            return response
        response.set_data(html.replace("</body>", f'<script src="{UI_SCRIPT}"></script>\n</body>', 1))
        response.headers["Content-Length"] = str(len(response.get_data()))
        return response

    app._totalro_ccro_ui_runtime_registered = True
