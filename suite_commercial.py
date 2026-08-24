"""Configurable Suite product commercial/eligibility policy.

Billing cadence is deliberately nullable. Suite Core stores commercial intent and
pre-commercial eligibility policy but does not assume a payment processor or
subscription cadence before those decisions are approved.
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from auth import ProductEntitlement, User, admin_required, audit, db
from suite_catalog import PRODUCTS

commercial_bp = Blueprint("suite_commercial", __name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProductCommercialPolicy(db.Model):
    __tablename__ = "suite_product_commercial_policies"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(48), nullable=False, unique=True, index=True)
    commercial_active = db.Column(db.Boolean, nullable=False, default=False)
    price_usd_cents = db.Column(db.Integer, nullable=True)
    billing_cadence = db.Column(db.String(40), nullable=False, default="")
    precommercial_access_mode = db.Column(db.String(80), nullable=False, default="admin_approved")
    student_free_access_enabled = db.Column(db.Boolean, nullable=False, default=False)
    eligibility_notes = db.Column(db.Text, nullable=False, default="")
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


def ensure_commercial_policies() -> None:
    existing = {row.product_id: row for row in db.session.scalars(select(ProductCommercialPolicy)).all()}
    for product in PRODUCTS:
        if product.product_id in existing:
            continue
        if product.product_id == "academy":
            row = ProductCommercialPolicy(
                product_id="academy",
                commercial_active=False,
                price_usd_cents=500,
                billing_cadence="",
                precommercial_access_mode="approved_students",
                student_free_access_enabled=True,
                eligibility_notes="Pre-commercial: free access may be granted to administrator-approved eligible students. Billing cadence is intentionally undefined until approved.",
            )
        else:
            row = ProductCommercialPolicy(product_id=product.product_id)
        db.session.add(row)


def commercial_policy(product_id: str) -> ProductCommercialPolicy | None:
    return db.session.scalar(select(ProductCommercialPolicy).where(ProductCommercialPolicy.product_id == str(product_id).strip().lower()))


def precommercial_entitlement_allowed(user: User, product_id: str) -> bool:
    """Policy helper for future specialist apps such as Total Water Academy.

    A product branch must still enforce its release/readiness state. This helper
    only answers whether Suite administration granted a user entitlement under
    the configured pre-commercial policy.
    """
    policy = commercial_policy(product_id)
    if not policy or policy.commercial_active:
        return False
    entitlement = db.session.scalar(select(ProductEntitlement).where(
        ProductEntitlement.user_id == user.id,
        ProductEntitlement.product_id == str(product_id).strip().lower(),
    ))
    if not entitlement or not entitlement.enabled or not entitlement.is_current():
        return False
    if policy.precommercial_access_mode == "approved_students":
        return bool(policy.student_free_access_enabled)
    return policy.precommercial_access_mode == "admin_approved"


@commercial_bp.get("/admin/products")
@admin_required
def admin_products():
    ensure_commercial_policies()
    db.session.commit()
    policies = {row.product_id: row for row in db.session.scalars(select(ProductCommercialPolicy)).all()}
    return render_template("auth/admin_products.html", products=PRODUCTS, policies=policies)


@commercial_bp.post("/admin/products/<product_id>/commercial-policy")
@admin_required
def update_commercial_policy(product_id: str):
    ensure_commercial_policies()
    row = commercial_policy(product_id)
    if not row:
        flash("Unknown Suite product.", "error")
        return redirect(url_for("suite_commercial.admin_products"))
    raw_price = str(request.form.get("price_usd") or "").strip()
    if raw_price:
        try:
            cents = int(round(float(raw_price) * 100))
            if cents < 0:
                raise ValueError
            row.price_usd_cents = cents
        except ValueError:
            flash("Price must be a non-negative USD value or blank.", "error")
            return redirect(url_for("suite_commercial.admin_products"))
    else:
        row.price_usd_cents = None
    row.billing_cadence = str(request.form.get("billing_cadence") or "").strip()[:40]
    row.commercial_active = bool(request.form.get("commercial_active"))
    row.student_free_access_enabled = bool(request.form.get("student_free_access_enabled"))
    row.precommercial_access_mode = str(request.form.get("precommercial_access_mode") or "admin_approved").strip()[:80]
    row.eligibility_notes = str(request.form.get("eligibility_notes") or "").strip()[:5000]
    row.updated_by_user_id = current_user.id
    audit("product_commercial_policy_updated", actor=current_user,
          detail=f"product={row.product_id}; commercial={row.commercial_active}; price_cents={row.price_usd_cents}; cadence={row.billing_cadence or 'undefined'}")
    db.session.commit()
    flash(f"Commercial policy updated for {row.product_id}.", "success")
    return redirect(url_for("suite_commercial.admin_products"))


def init_suite_commercial(app) -> None:
    if "suite_commercial" in app.blueprints:
        return
    with app.app_context():
        db.create_all()
        ensure_commercial_policies()
        db.session.commit()
    app.register_blueprint(commercial_bp)
