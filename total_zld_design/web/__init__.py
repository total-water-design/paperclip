"""Flask integration for the Total Water Design Suite."""

from __future__ import annotations

from typing import Any, Callable


def create_zld_blueprint(project_backend: Any = None, access_guard: Callable | None = None):
    """Create the `/zld` Blueprint.

    `access_guard` should be supplied by the Suite and enforce authenticated `zld`
    product entitlement / admin-preview rules. `project_backend` should implement a
    `save_snapshot(snapshot, request_payload)` method and use the Suite PostgreSQL
    ProjectFamily/ProjectRevision models. This package deliberately does not create a
    parallel auth or project database.
    """
    try:
        from flask import Blueprint, jsonify, render_template, request
    except ImportError as exc:  # pragma: no cover - exercised only on web hosts
        raise RuntimeError("Flask is required for Suite web integration. Install the package's [web] extra.") from exc

    from ..service import defaults_payload, handle_calculation_payload, handle_snapshot_payload

    bp = Blueprint(
        "total_zld_design",
        __name__,
        url_prefix="/zld",
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )

    def protect(fn):
        return access_guard(fn) if access_guard is not None else fn

    @bp.get("")
    @bp.get("/")
    @protect
    def index():
        return render_template("zld_index.html")

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
