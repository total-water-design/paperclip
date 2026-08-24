"""Implementation/release state linked to authoritative Suite feedback records."""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_login import current_user
from sqlalchemy import select

from auth import admin_required, audit, db
from suite_feedback import FeedbackReport

feedback_state_bp = Blueprint("suite_feedback_state", __name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FeedbackImplementationState(db.Model):
    __tablename__ = "suite_feedback_implementation_state"
    id = db.Column(db.Integer, primary_key=True)
    feedback_id = db.Column(db.Integer, db.ForeignKey("suite_feedback_reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    implementation_status = db.Column(db.String(32), nullable=False, default="not_started", index=True)
    release_version = db.Column(db.String(100), nullable=False, default="", index=True)
    note = db.Column(db.String(1000), nullable=False, default="")
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class _EmptyState:
    implementation_status = "not_started"
    release_version = ""
    note = ""


def get_feedback_state(feedback_id: int):
    return db.session.scalar(
        select(FeedbackImplementationState).where(FeedbackImplementationState.feedback_id == int(feedback_id))
    ) or _EmptyState()


@feedback_state_bp.post("/admin/feedback/<int:report_id>/implementation")
@admin_required
def update_feedback_state(report_id: int):
    if not db.session.get(FeedbackReport, report_id):
        abort(404)
    allowed = {"not_started", "planned", "in_development", "validated", "deployed", "closed"}
    status = str(request.form.get("implementation_status") or "not_started").strip().lower()
    if status not in allowed:
        status = "not_started"
    row = db.session.scalar(
        select(FeedbackImplementationState).where(FeedbackImplementationState.feedback_id == report_id)
    )
    if not row:
        row = FeedbackImplementationState(feedback_id=report_id)
        db.session.add(row)
    row.implementation_status = status
    row.release_version = str(request.form.get("release_version") or "").strip()[:100]
    row.note = str(request.form.get("note") or "").strip()[:1000]
    row.updated_by_user_id = current_user.id
    audit(
        "feedback_implementation_status_updated",
        actor=current_user,
        detail=f"feedback_id={report_id}; status={status}; release={row.release_version}",
    )
    db.session.commit()
    flash("Feedback implementation/release status updated.", "success")
    return redirect(url_for("suite_feedback.feedback_admin_page"))


def init_suite_feedback_state(app) -> None:
    if "suite_feedback_state" in app.blueprints:
        return
    with app.app_context():
        db.create_all()
    app.register_blueprint(feedback_state_bp)

    @app.context_processor
    def _feedback_state_context():
        return {"feedback_state": get_feedback_state}

    # Install the evidence-derived remediation only after both base feedback
    # blueprints have registered their original endpoints. This keeps the
    # validation harness and production WSGI path on the same hardened routes.
    from suite_feedback_hardening import init_suite_feedback_hardening
    init_suite_feedback_hardening(app)
