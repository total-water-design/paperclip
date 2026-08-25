"""Suite registration for Total ZLD Design.

ZLD reuses Suite authentication, entitlement, CSRF, Project Library and the
Application UI/UX Contract while remaining administrator-gated during the
engineering-preview milestone.
"""
from __future__ import annotations

from functools import wraps

from flask import jsonify, redirect, request, url_for
from flask_login import current_user

from auth import user_can_access_product
from suite_catalog import PRODUCT_BY_ID
from total_zld_design.web import create_zld_blueprint


def register_total_zld_design(app):
    """Register Total ZLD Design on the Suite Flask application."""

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

    product = PRODUCT_BY_ID["zld"]
    app.register_blueprint(
        create_zld_blueprint(
            project_backend=None,
            access_guard=access_required,
            application_context={
                "app_id": product.product_id,
                "app_name": product.name,
                "app_accent": product.accent,
                "app_icon_asset": product.icon_asset,
            },
        )
    )
    return app
