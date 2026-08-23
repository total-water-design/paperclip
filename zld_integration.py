"""Suite registration for Total ZLD Design.

This module keeps the ZLD product integration separate from the mature RO engine.
It reuses the Suite session, authentication, entitlement, CSRF and Project Library
infrastructure and grants administrators preview access while the product remains
in development.
"""
from __future__ import annotations

from functools import wraps

from flask import jsonify, redirect, request, url_for
from flask_login import current_user

from auth import user_can_access_product
from total_zld_design.web import create_zld_blueprint


def register_total_zld_design(app):
    """Register the hosted Total ZLD Design Blueprint on the Suite Flask app."""

    def access_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not app.config.get("AUTH_ENABLED", False):
                return view(*args, **kwargs)

            if bool(getattr(current_user, "is_admin", False)):
                return view(*args, **kwargs)

            if user_can_access_product(current_user, "zld"):
                return view(*args, **kwargs)

            if request.path.startswith("/zld/api/"):
                return jsonify({
                    "error": "Total ZLD Design is not included in this account.",
                    "error_type": "ProductEntitlementError",
                    "product_id": "zld",
                    "guidance": "Total ZLD Design is currently available only as an administrator engineering preview.",
                }), 403

            return redirect(url_for("suite_dashboard"))

        return wrapped

    app.register_blueprint(
        create_zld_blueprint(
            project_backend=None,
            access_guard=access_required,
        )
    )
    return app
