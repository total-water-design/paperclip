"""Flask integration for Total ZLD Design within the Total Water Design Suite."""
from __future__ import annotations

from typing import Any, Callable, Mapping


def create_zld_blueprint(
    project_backend: Any = None,
    access_guard: Callable | None = None,
    application_context: Mapping[str, Any] | None = None,
):
    """Create the `/zld` Blueprint using the Suite application-shell contract.

    ``access_guard`` is supplied by the Suite and enforces authenticated ZLD
    entitlement/admin-preview rules. ``project_backend`` may provide a direct
    snapshot adapter, although hosted mode normally uses the Suite-wide project
    API from the browser. ``application_context`` carries catalog-controlled
    product identity into the shared Suite shell.
    """
    try:
        from flask import Blueprint, current_app, jsonify, render_template, request
    except ImportError as exc:  # pragma: no cover - web-host dependency
        raise RuntimeError("Flask is required for Suite web integration.") from exc

    from ..service import defaults_payload, handle_calculation_payload, handle_snapshot_payload

    bp = Blueprint(
        "total_zld_design",
        __name__,
        url_prefix="/zld",
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )

    shell_defaults = {
        "app_id": "zld",
        "app_name": "Total ZLD Design",
        "app_version": "0.2.0",
        "app_accent": "#6B4FD3",
        "app_icon_asset": "branding/suite/total_zld_design_icon_512.png",
        "project_name": "Total ZLD Design Project",
        "project_id": "Unsaved",
        "project_revision": "",
    }
    if application_context:
        shell_defaults.update(dict(application_context))

    def protect(fn):
        return access_guard(fn) if access_guard is not None else fn

    @bp.get("")
    @bp.get("/")
    @protect
    def index():
        context = dict(shell_defaults)
        context["auth_enabled"] = bool(current_app.config.get("AUTH_ENABLED", False))
        return render_template("zld_contract.html", **context)

    @bp.get("/api/health")
    def health():
        return jsonify({"ok": True, "service": "Total ZLD Design", "version": "0.2.0", "state": "engineering_preview"})

    @bp.get("/api/defaults")
    @protect
    def defaults():
        return jsonify(defaults_payload())

    @bp.post("/api/calculate")
    @protect
    def calculate_api():
        try:
            return jsonify(handle_calculation_payload(request.get_json(silent=True) or {}))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @bp.post("/api/project/snapshot")
    @protect
    def snapshot_api():
        try:
            return jsonify(handle_snapshot_payload(request.get_json(silent=True) or {}))
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @bp.post("/api/project/save")
    @protect
    def save_project_api():
        if project_backend is None:
            return jsonify({
                "ok": False,
                "error": "Suite Project Library adapter is not attached. Hosted mode must not fall back to localStorage.",
            }), 501
        try:
            payload = request.get_json(silent=True) or {}
            snapshot_response = handle_snapshot_payload(payload)
            saved = project_backend.save_snapshot(snapshot_response["snapshot"], payload)
            return jsonify({"ok": True, "project": saved})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    return bp


__all__ = ["create_zld_blueprint"]
