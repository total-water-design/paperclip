"""Runtime hardening for the Suite Core feedback workflow.

This module implements the remediation demonstrated by the feedback conformance
matrix without moving specialist engineering logic into Suite Core. It adds
atomic action claims, immutable response-approval snapshots, and evidence-bound
implementation/release transitions. The existing feedback database remains the
authoritative customer-feedback record.
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user
from sqlalchemy import UniqueConstraint, select, update

from auth import User, admin_required, audit, db
import suite_feedback as feedback
from suite_communications import ReleaseRecord
from suite_mail import send_transactional_email


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FeedbackActionGuard(db.Model):
    """Atomic/idempotency and approval-snapshot state kept beside feedback."""

    __tablename__ = "suite_feedback_action_guards"

    id = db.Column(db.Integer, primary_key=True)
    feedback_id = db.Column(
        db.Integer,
        db.ForeignKey("suite_feedback_reports.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    approved_response_draft = db.Column(db.Text, nullable=False, default="")
    response_state = db.Column(db.String(24), nullable=False, default="not_approved", index=True)
    response_attempts = db.Column(db.Integer, nullable=False, default=0)
    github_state = db.Column(db.String(24), nullable=False, default="not_ready", index=True)
    github_attempts = db.Column(db.Integer, nullable=False, default=0)
    validation_evidence_id = db.Column(
        db.Integer,
        db.ForeignKey("suite_feedback_validation_evidence.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    release_record_id = db.Column(db.Integer, nullable=True, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class FeedbackValidationEvidence(db.Model):
    """Trusted specialist/reconciliation validation evidence.

    No customer-facing/admin form creates this record. Specialist/reconciliation
    integration calls ``record_specialist_validation_evidence`` after its own
    validation has completed.
    """

    __tablename__ = "suite_feedback_validation_evidence"
    __table_args__ = (
        UniqueConstraint(
            "feedback_id",
            "validated_sha",
            "validation_reference",
            name="uq_feedback_validation_evidence",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    feedback_id = db.Column(
        db.Integer,
        db.ForeignKey("suite_feedback_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_branch = db.Column(db.String(180), nullable=False)
    validated_sha = db.Column(db.String(80), nullable=False, index=True)
    validation_reference = db.Column(db.String(500), nullable=False)
    recorded_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)


def record_specialist_validation_evidence(
    *,
    feedback_id: int,
    source_branch: str,
    validated_sha: str,
    validation_reference: str,
    recorded_by_user_id: int | None = None,
) -> FeedbackValidationEvidence:
    """Record validation evidence from a trusted specialist/reconciliation path."""

    report = db.session.get(feedback.FeedbackReport, int(feedback_id))
    if not report:
        raise ValueError("Feedback record not found.")
    branch = str(source_branch or "").strip()[:180]
    sha = str(validated_sha or "").strip()[:80]
    reference = str(validation_reference or "").strip()[:500]
    if not branch or not sha or not reference:
        raise ValueError("source_branch, validated_sha and validation_reference are required.")
    row = FeedbackValidationEvidence(
        feedback_id=report.id,
        source_branch=branch,
        validated_sha=sha,
        validation_reference=reference,
        recorded_by_user_id=recorded_by_user_id,
    )
    db.session.add(row)
    db.session.flush()
    return row


def _validation_evidence(feedback_id: int) -> FeedbackValidationEvidence | None:
    return db.session.scalar(
        select(FeedbackValidationEvidence)
        .where(FeedbackValidationEvidence.feedback_id == int(feedback_id))
        .order_by(FeedbackValidationEvidence.recorded_at.desc(), FeedbackValidationEvidence.id.desc())
    )


def has_specialist_validation_evidence(feedback_id: int) -> bool:
    return _validation_evidence(feedback_id) is not None


def _github_eligible(report: feedback.FeedbackReport) -> bool:
    return bool(
        report.status == feedback.STATUS_PRODUCT_REVIEW
        and report.acceptance_state == "accepted"
        and report.product_review_authorized
        and not report.github_issue_id
        and report.final_disposition not in {"duplicate", "rejected", "closed"}
    )


def _guard(report: feedback.FeedbackReport, *, create: bool = True) -> FeedbackActionGuard | None:
    row = db.session.scalar(
        select(FeedbackActionGuard).where(FeedbackActionGuard.feedback_id == report.id)
    )
    if row or not create:
        return row
    row = FeedbackActionGuard(
        feedback_id=report.id,
        response_state="sent" if report.response_sent_at else "not_approved",
        github_state="created" if report.github_issue_id else ("ready" if _github_eligible(report) else "not_ready"),
    )
    db.session.add(row)
    db.session.flush()
    return row


def _clear_product_authorization(report: feedback.FeedbackReport, guard: FeedbackActionGuard) -> None:
    report.product_review_authorized = False
    report.ai_processing_authorized = False
    if guard.github_state != "created":
        guard.github_state = "blocked"


def _apply_admin_fields(report: feedback.FeedbackReport, guard: FeedbackActionGuard) -> None:
    report.admin_review = feedback._clean(request.form.get("admin_review"), 12000)

    category = feedback._clean(request.form.get("category") or report.category, 40).lower()
    if category in feedback.CATEGORIES:
        report.category = category

    priority = feedback._clean(request.form.get("priority") or report.priority, 24).lower()
    if priority in feedback.PRIORITIES:
        report.priority = priority

    report.technical_requirement = feedback._clean(
        request.form.get("technical_requirement"), 12000
    )
    report.reproduction_info = feedback._clean(request.form.get("reproduction_info"), 12000)
    report.product_owner_branch = feedback._clean(request.form.get("product_owner_branch"), 160)
    report.duplicate_of_ticket = feedback._clean(request.form.get("duplicate_of_ticket"), 64)

    if "response_draft" in request.form:
        candidate = feedback._clean(request.form.get("response_draft"), 12000)
        if (
            report.response_approval_state == "approved"
            and guard.approved_response_draft
            and candidate != guard.approved_response_draft
        ):
            report.response_approval_state = "pending" if candidate else "not_drafted"
            guard.response_state = "not_approved"
            if report.status not in {
                feedback.STATUS_IMPLEMENTED,
                feedback.STATUS_CLOSED,
                feedback.STATUS_REJECTED,
                feedback.STATUS_DUPLICATE,
            }:
                report.status = feedback.STATUS_RESPONSE_DRAFTED
        report.response_draft = candidate
        if candidate and report.response_approval_state == "not_drafted":
            report.response_approval_state = "pending"
            if report.status not in {
                feedback.STATUS_IMPLEMENTED,
                feedback.STATUS_CLOSED,
                feedback.STATUS_REJECTED,
                feedback.STATUS_DUPLICATE,
            }:
                report.status = feedback.STATUS_RESPONSE_DRAFTED


def _finish_admin_action(report: feedback.FeedbackReport, action: str):
    audit(
        "feedback_admin_action",
        user=db.session.get(User, report.user_id) if report.user_id else None,
        actor=current_user,
        detail=f"ticket={report.ticket}; action={action}; status={report.status}",
    )
    db.session.commit()
    flash(f"Feedback {report.ticket} updated: {report.status}.", "success")
    return redirect(url_for("suite_feedback.feedback_admin_page"))


def _deny(message: str):
    db.session.commit()
    flash(message, "error")
    return redirect(url_for("suite_feedback.feedback_admin_page"))


def _send_response(report: feedback.FeedbackReport, guard: FeedbackActionGuard):
    if (
        report.response_approval_state != "approved"
        or not guard.approved_response_draft
        or report.response_draft != guard.approved_response_draft
        or not report.user_email
    ):
        return _deny("An unchanged, approved response draft and user email are required before sending.")
    if report.response_sent_at or guard.response_state == "sent":
        return _deny("This feedback response has already been sent.")

    db.session.flush()
    claim = db.session.execute(
        update(FeedbackActionGuard)
        .where(
            FeedbackActionGuard.id == guard.id,
            FeedbackActionGuard.response_state.in_(("ready", "failed")),
        )
        .values(
            response_state="sending",
            response_attempts=FeedbackActionGuard.response_attempts + 1,
            updated_at=_utcnow(),
        )
    )
    db.session.commit()
    if claim.rowcount != 1:
        flash("This feedback response is already being sent or has already been sent.", "error")
        return redirect(url_for("suite_feedback.feedback_admin_page"))

    report = db.session.get(feedback.FeedbackReport, report.id)
    guard = db.session.scalar(
        select(FeedbackActionGuard).where(FeedbackActionGuard.feedback_id == report.id)
    )
    approved = guard.approved_response_draft
    result = send_transactional_email(
        user_id=report.user_id,
        recipient=report.user_email,
        event_type="feedback_response",
        subject=f"Total Water Design Suite feedback follow-up · {report.ticket}",
        body=(
            f"Hello {report.user_first_name or 'there'},\n\n"
            f"{approved}\n\n"
            "Thank you for helping us improve Total Water Design Suite.\n\n"
            "Total Water Design Suite\n"
            "admin@totalrodesign.com\n"
        ),
        template="feedback_response_v1",
    )
    if not result.sent:
        guard.response_state = "failed"
        db.session.commit()
        flash(f"Response was not sent: {result.detail}", "error")
        return redirect(url_for("suite_feedback.feedback_admin_page"))

    report.response_sent_at = _utcnow()
    report.status = feedback.STATUS_RESPONSE_SENT
    guard.response_state = "sent"
    return _finish_admin_action(report, "send_response")


def _promote_github(report: feedback.FeedbackReport, guard: FeedbackActionGuard):
    if not _github_eligible(report):
        return _deny(
            "GitHub promotion requires the explicit APPROVED_FOR_PRODUCT_REVIEW lifecycle state "
            "with active product-review authorization."
        )
    if report.github_issue_id or guard.github_state == "created":
        return _deny("This feedback already has a GitHub issue.")

    # The database guard is the cross-worker ownership record. An in-progress
    # claim must never be reset merely because the external issue id has not yet
    # been persisted. Likewise, blocked/not-ready states fail closed instead of
    # being silently made claimable. A failed attempt is retryable only through
    # another explicit administrator promote action; the durable attempt counter
    # and updated_at timestamp record that new claim.
    if guard.github_state == "creating":
        return _deny("GitHub promotion is already in progress.")
    if guard.github_state not in {"ready", "failed"}:
        return _deny("GitHub promotion is not ready for this feedback lifecycle state.")

    claim = db.session.execute(
        update(FeedbackActionGuard)
        .where(
            FeedbackActionGuard.id == guard.id,
            FeedbackActionGuard.github_state.in_(("ready", "failed")),
        )
        .values(
            github_state="creating",
            github_attempts=FeedbackActionGuard.github_attempts + 1,
            updated_at=_utcnow(),
        )
    )
    db.session.commit()
    if claim.rowcount != 1:
        flash("GitHub promotion is already in progress or has already completed.", "error")
        return redirect(url_for("suite_feedback.feedback_admin_page"))

    report = db.session.get(feedback.FeedbackReport, report.id)
    guard = db.session.scalar(
        select(FeedbackActionGuard).where(FeedbackActionGuard.feedback_id == report.id)
    )
    ok, issue_id, issue_url = feedback._create_github_issue(report)
    if not ok:
        guard.github_state = "failed"
        db.session.commit()
        flash(issue_id, "error")
        return redirect(url_for("suite_feedback.feedback_admin_page"))

    report.github_issue_id = issue_id
    report.github_issue_url = issue_url
    report.status = feedback.STATUS_GITHUB
    guard.github_state = "created"
    return _finish_admin_action(report, "promote_github")


@admin_required
def hardened_feedback_admin_action(report_id: int):
    report = db.get_or_404(feedback.FeedbackReport, report_id)
    action = str(request.form.get("action") or "save").strip().lower()
    guard = _guard(report)
    _apply_admin_fields(report, guard)

    report.reviewed_by_user_id = current_user.id
    report.reviewed_at = _utcnow()
    if report.status == feedback.STATUS_NEW:
        report.status = feedback.STATUS_ADMIN_REVIEW

    if action == "accept":
        report.acceptance_state = "accepted"
        report.status = feedback.STATUS_ACCEPTED
        if guard.github_state == "blocked":
            guard.github_state = "not_ready"

    elif action == "reject":
        report.acceptance_state = "rejected"
        _clear_product_authorization(report, guard)
        report.status = feedback.STATUS_REJECTED
        report.final_disposition = "rejected"

    elif action == "request_info":
        _clear_product_authorization(report, guard)
        report.status = feedback.STATUS_MORE_INFO

    elif action == "duplicate":
        _clear_product_authorization(report, guard)
        report.status = feedback.STATUS_DUPLICATE
        report.final_disposition = "duplicate"

    elif action == "authorize_product_review":
        if report.acceptance_state != "accepted" or report.status != feedback.STATUS_ACCEPTED:
            return _deny("Accept the feedback before authorizing product review.")
        report.product_review_authorized = True
        report.ai_processing_authorized = bool(request.form.get("ai_processing_authorized"))
        report.status = feedback.STATUS_PRODUCT_REVIEW
        if not report.github_issue_id:
            guard.github_state = "ready"

    elif action == "approve_response":
        if not report.response_draft:
            return _deny("Draft a response before approving it.")
        if report.response_sent_at:
            return _deny("The response has already been sent and cannot be re-approved.")
        guard.approved_response_draft = report.response_draft
        guard.response_state = "ready"
        report.response_approval_state = "approved"
        report.status = feedback.STATUS_RESPONSE_APPROVED

    elif action == "reject_response":
        report.response_approval_state = "rejected"
        guard.response_state = "not_approved"

    elif action == "send_response":
        return _send_response(report, guard)

    elif action == "promote_github":
        return _promote_github(report, guard)

    elif action == "implemented":
        if report.category == "calculation" and not has_specialist_validation_evidence(report.id):
            return _deny(
                "Calculation feedback requires specialist validation evidence before it can be marked implemented."
            )
        report.status = feedback.STATUS_IMPLEMENTED
        report.final_disposition = "implemented"

    elif action == "close":
        _clear_product_authorization(report, guard)
        report.status = feedback.STATUS_CLOSED
        report.final_disposition = feedback._clean(
            request.form.get("final_disposition")
            or report.final_disposition
            or "closed",
            80,
        )

    elif action != "save":
        abort(400)

    return _finish_admin_action(report, action)


@admin_required
def hardened_update_feedback_state(report_id: int):
    from suite_feedback_state import FeedbackImplementationState

    report = db.session.get(feedback.FeedbackReport, report_id)
    if not report:
        abort(404)

    allowed = {"not_started", "planned", "in_development", "validated", "deployed", "closed"}
    status = str(request.form.get("implementation_status") or "not_started").strip().lower()
    if status not in allowed:
        status = "not_started"

    release_version = str(request.form.get("release_version") or "").strip()[:100]
    evidence = _validation_evidence(report.id)
    guard = _guard(report)

    if status in {"validated", "deployed"} and not evidence:
        return _deny(
            "Specialist validation evidence is required before feedback can be marked validated or deployed."
        )

    release = None
    if status == "deployed":
        if not release_version:
            return _deny("A deployed release record is required before feedback can be marked deployed.")
        release = db.session.scalar(
            select(ReleaseRecord).where(ReleaseRecord.version == release_version)
        )
        if not release or not release.is_customer_ready():
            return _deny(
                "The selected release is not recorded as validated, deployed, and health-verified."
            )

    row = db.session.scalar(
        select(FeedbackImplementationState).where(
            FeedbackImplementationState.feedback_id == report.id
        )
    )
    if not row:
        row = FeedbackImplementationState(feedback_id=report.id)
        db.session.add(row)

    row.implementation_status = status
    row.release_version = release.version if release else release_version
    row.note = str(request.form.get("note") or "").strip()[:1000]
    row.updated_by_user_id = current_user.id

    if evidence and status in {"validated", "deployed"}:
        guard.validation_evidence_id = evidence.id
    if release:
        guard.release_record_id = release.id

    audit(
        "feedback_implementation_status_updated",
        actor=current_user,
        detail=(
            f"feedback_id={report.id}; status={status}; "
            f"validation_evidence_id={guard.validation_evidence_id or ''}; "
            f"release_record_id={guard.release_record_id or ''}"
        ),
    )
    db.session.commit()
    flash("Feedback implementation/release status updated.", "success")
    return redirect(url_for("suite_feedback.feedback_admin_page"))


def init_suite_feedback_hardening(app) -> None:
    """Install evidence-backed feedback actions after base feedback routes exist."""

    if app.extensions.get("twds_feedback_hardening"):
        return
    with app.app_context():
        db.create_all()

    required = {
        "suite_feedback.feedback_admin_action": hardened_feedback_admin_action,
        "suite_feedback_state.update_feedback_state": hardened_update_feedback_state,
    }
    missing = [endpoint for endpoint in required if endpoint not in app.view_functions]
    if missing:
        raise RuntimeError(
            "Feedback hardening must be initialized after base feedback routes: "
            + ", ".join(missing)
        )
    app.view_functions.update(required)
    app.extensions["twds_feedback_hardening"] = True
