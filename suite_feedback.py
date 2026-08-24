"""Authoritative Total Water Design Suite feedback workflow.

Raw customer feedback remains in the Suite database. Administrators are the
product gate: no feedback is promoted to product review, external tooling, or a
GitHub issue until explicitly accepted and authorized. GitHub mirrors contain
only administrator-sanitized technical summaries.
"""
from __future__ import annotations

import base64
import json
import os
import re
import smtplib
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, inspect, select, text

from auth import User, admin_required, audit, db, record_telemetry
from suite_mail import first_name, send_transactional_email

feedback_bp = Blueprint("suite_feedback", __name__)

STATUS_NEW = "NEW"
STATUS_ADMIN_REVIEW = "ADMIN_REVIEW"
STATUS_ACCEPTED = "ACCEPTED"
STATUS_REJECTED = "REJECTED"
STATUS_PRODUCT_REVIEW = "APPROVED_FOR_PRODUCT_REVIEW"
STATUS_GITHUB = "GITHUB_ISSUE_CREATED"
STATUS_RESPONSE_DRAFTED = "RESPONSE_DRAFTED"
STATUS_RESPONSE_APPROVED = "RESPONSE_APPROVED"
STATUS_RESPONSE_SENT = "RESPONSE_SENT"
STATUS_MORE_INFO = "MORE_INFORMATION_REQUESTED"
STATUS_DUPLICATE = "DUPLICATE"
STATUS_IMPLEMENTED = "IMPLEMENTED"
STATUS_CLOSED = "CLOSED"

FEEDBACK_STATUSES = (
    STATUS_NEW, STATUS_ADMIN_REVIEW, STATUS_ACCEPTED, STATUS_REJECTED,
    STATUS_PRODUCT_REVIEW, STATUS_GITHUB, STATUS_RESPONSE_DRAFTED,
    STATUS_RESPONSE_APPROVED, STATUS_RESPONSE_SENT, STATUS_MORE_INFO,
    STATUS_DUPLICATE, STATUS_IMPLEMENTED, STATUS_CLOSED,
)
PRIORITIES = ("unassigned", "low", "normal", "high", "critical")
CATEGORIES = ("general", "bug", "enhancement", "documentation", "calculation", "usability", "other")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _clean(value: object, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def _safe_token(value: object, fallback: str = "item") -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", _clean(value, 80)).strip("._")
    return value or fallback


class FeedbackReport(db.Model):
    __tablename__ = "suite_feedback_reports"

    id = db.Column(db.Integer, primary_key=True)
    ticket = db.Column(db.String(64), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_first_name = db.Column(db.String(100), nullable=False, default="")
    user_email = db.Column(db.String(254), nullable=False, default="", index=True)
    application = db.Column(db.String(64), nullable=False, default="suite", index=True)
    application_version = db.Column(db.String(40), nullable=False, default="")
    category = db.Column(db.String(40), nullable=False, default="general", index=True)
    message = db.Column(db.Text, nullable=False)
    context_json = db.Column(db.Text, nullable=False, default="{}")
    project_id = db.Column(db.String(100), nullable=False, default="", index=True)
    project_revision = db.Column(db.String(80), nullable=False, default="")
    workspace = db.Column(db.String(120), nullable=False, default="")
    status = db.Column(db.String(48), nullable=False, default=STATUS_NEW, index=True)
    admin_review = db.Column(db.Text, nullable=False, default="")
    acceptance_state = db.Column(db.String(24), nullable=False, default="unreviewed", index=True)
    priority = db.Column(db.String(24), nullable=False, default="unassigned", index=True)
    product_review_authorized = db.Column(db.Boolean, nullable=False, default=False)
    ai_processing_authorized = db.Column(db.Boolean, nullable=False, default=False)
    technical_requirement = db.Column(db.Text, nullable=False, default="")
    reproduction_info = db.Column(db.Text, nullable=False, default="")
    product_owner_branch = db.Column(db.String(160), nullable=False, default="")
    duplicate_of_ticket = db.Column(db.String(64), nullable=False, default="")
    response_draft = db.Column(db.Text, nullable=False, default="")
    response_approval_state = db.Column(db.String(24), nullable=False, default="not_drafted", index=True)
    response_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    github_issue_id = db.Column(db.String(40), nullable=False, default="")
    github_issue_url = db.Column(db.String(500), nullable=False, default="")
    final_disposition = db.Column(db.String(80), nullable=False, default="")
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    recipient = db.Column(db.String(254), nullable=False, default="support@totalrodesign.com")
    delivery_status = db.Column(db.String(24), nullable=False, default="pending", index=True)
    receipt_email_status = db.Column(db.String(24), nullable=False, default="pending", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.Text, nullable=False, default="")
    screenshots_count = db.Column(db.Integer, nullable=False, default=0)
    bundle_name = db.Column(db.String(180), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "ticket": self.ticket,
            "user_first_name": self.user_first_name,
            "user_email": self.user_email,
            "application": self.application,
            "application_version": self.application_version,
            "category": self.category,
            "message": self.message,
            "context": json.loads(self.context_json or "{}"),
            "project_id": self.project_id,
            "project_revision": self.project_revision,
            "workspace": self.workspace,
            "status": self.status,
            "admin_review": self.admin_review,
            "acceptance_state": self.acceptance_state,
            "priority": self.priority,
            "product_review_authorized": bool(self.product_review_authorized),
            "ai_processing_authorized": bool(self.ai_processing_authorized),
            "technical_requirement": self.technical_requirement,
            "reproduction_info": self.reproduction_info,
            "product_owner_branch": self.product_owner_branch,
            "response_draft": self.response_draft,
            "response_approval_state": self.response_approval_state,
            "response_sent_at": self.response_sent_at.isoformat() if self.response_sent_at else None,
            "github_issue_id": self.github_issue_id,
            "github_issue_url": self.github_issue_url,
            "final_disposition": self.final_disposition,
            "recipient": self.recipient,
            "delivery_status": self.delivery_status,
            "receipt_email_status": self.receipt_email_status,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "screenshots_count": self.screenshots_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


def _ensure_feedback_schema() -> None:
    """Add workflow columns to installations that already have v1 feedback."""
    inspector = inspect(db.engine)
    if not inspector.has_table("suite_feedback_reports"):
        return
    additions = [
        ("user_first_name", "VARCHAR(100) NOT NULL DEFAULT ''"),
        ("user_email", "VARCHAR(254) NOT NULL DEFAULT ''"),
        ("context_json", "TEXT NOT NULL DEFAULT '{}'"),
        ("status", "VARCHAR(48) NOT NULL DEFAULT 'NEW'"),
        ("admin_review", "TEXT NOT NULL DEFAULT ''"),
        ("acceptance_state", "VARCHAR(24) NOT NULL DEFAULT 'unreviewed'"),
        ("priority", "VARCHAR(24) NOT NULL DEFAULT 'unassigned'"),
        ("product_review_authorized", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("ai_processing_authorized", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("technical_requirement", "TEXT NOT NULL DEFAULT ''"),
        ("reproduction_info", "TEXT NOT NULL DEFAULT ''"),
        ("product_owner_branch", "VARCHAR(160) NOT NULL DEFAULT ''"),
        ("duplicate_of_ticket", "VARCHAR(64) NOT NULL DEFAULT ''"),
        ("response_draft", "TEXT NOT NULL DEFAULT ''"),
        ("response_approval_state", "VARCHAR(24) NOT NULL DEFAULT 'not_drafted'"),
        ("response_sent_at", "TIMESTAMP NULL"),
        ("github_issue_id", "VARCHAR(40) NOT NULL DEFAULT ''"),
        ("github_issue_url", "VARCHAR(500) NOT NULL DEFAULT ''"),
        ("final_disposition", "VARCHAR(80) NOT NULL DEFAULT ''"),
        ("reviewed_by_user_id", "INTEGER NULL"),
        ("reviewed_at", "TIMESTAMP NULL"),
        ("receipt_email_status", "VARCHAR(24) NOT NULL DEFAULT 'pending'"),
    ]
    existing = {column["name"] for column in inspector.get_columns("suite_feedback_reports")}
    with db.engine.begin() as connection:
        for name, ddl in additions:
            if name not in existing:
                connection.execute(text(f'ALTER TABLE suite_feedback_reports ADD COLUMN {name} {ddl}'))


def _feedback_outbox() -> Path:
    configured = os.getenv("TWDS_FEEDBACK_OUTBOX") or os.getenv("TOTALRO_FEEDBACK_OUTBOX")
    root = Path(configured).expanduser() if configured else Path(current_app.instance_path) / "feedback_outbox"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _recipient() -> str:
    return _clean(os.getenv("TWDS_FEEDBACK_TO") or os.getenv("TOTALRO_FEEDBACK_TO") or "support@totalrodesign.com", 254)


def _smtp_value(canonical: str, legacy: str, default: str = "") -> str:
    return str(os.getenv(canonical) or os.getenv(legacy) or default).strip()


def _user_required() -> None:
    if current_app.config.get("AUTH_ENABLED", False) and not current_user.is_authenticated:
        abort(401)


def _write_bundle(ticket: str, payload: dict, screenshots: list[dict]) -> tuple[Path, int, str]:
    root = _feedback_outbox()
    work = root / ticket
    work.mkdir(parents=True, exist_ok=True)
    safe_context = payload.get("diagnostic_context") if isinstance(payload.get("diagnostic_context"), dict) else {}
    encoded_context = json.dumps(safe_context, ensure_ascii=False, default=str)[:2_000_000]
    metadata = {
        "ticket": ticket,
        "created_utc": _utcnow().isoformat(),
        "application": _clean(payload.get("application") or "suite", 64),
        "application_version": _clean(payload.get("application_version"), 40),
        "category": _clean(payload.get("category") or "general", 40),
        "message": _clean(payload.get("message"), 12000),
        "project_id": _clean(payload.get("project_id"), 100),
        "project_revision": _clean(payload.get("project_revision"), 80),
        "project_name": _clean(payload.get("project_name"), 200),
        "workspace": _clean(payload.get("workspace"), 120),
        "page": _clean(payload.get("page"), 500),
        "recipient": _recipient(),
    }
    (work / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (work / "diagnostic_context.json").write_text(encoded_context, encoding="utf-8")
    saved = 0
    for index, item in enumerate(screenshots[:12], 1):
        if not isinstance(item, dict):
            continue
        data_url = str(item.get("data_url") or "")
        if "," not in data_url:
            continue
        try:
            raw = base64.b64decode(data_url.split(",", 1)[1], validate=False)
        except Exception:
            continue
        if len(raw) > 5 * 1024 * 1024:
            continue
        filename = f"{index:02d}_{_safe_token(item.get('label'), 'screenshot')}.png"
        (work / filename).write_bytes(raw)
        saved += 1
    bundle = root / f"{ticket}.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(work.iterdir()):
            archive.write(path, arcname=path.name)
    return bundle, saved, encoded_context


def _support_message(report: FeedbackReport, bundle: Path) -> EmailMessage:
    sender = _smtp_value("TWDS_SMTP_FROM", "TOTALRO_SMTP_FROM") or _smtp_value("TWDS_SMTP_USER", "TOTALRO_SMTP_USER") or "admin@totalrodesign.com"
    subject = f"[TWDS Feedback] {report.application} · {report.ticket}"
    body = f"""Total Water Design Suite feedback report

Ticket: {report.ticket}
Application: {report.application}{' ' + report.application_version if report.application_version else ''}
Category: {report.category}
Project: {report.project_id or 'Not supplied'} {report.project_revision or ''}
Workspace: {report.workspace or 'Not supplied'}
Submitted by: {report.user_first_name or 'User'}{f' <{report.user_email}>' if report.user_email else ''}

Feedback:
{report.message}

The authoritative workflow record is stored in the Suite feedback database.
This email is a notification only.
"""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = report.recipient
    if report.user_email:
        message["Reply-To"] = report.user_email
    message.set_content(body)
    message.add_attachment(bundle.read_bytes(), maintype="application", subtype="zip", filename=bundle.name)
    return message


def _deliver_support(report: FeedbackReport, bundle: Path) -> tuple[bool, str]:
    report.attempts = int(report.attempts or 0) + 1
    host = _smtp_value("TWDS_SMTP_HOST", "TOTALRO_SMTP_HOST")
    port = int(_smtp_value("TWDS_SMTP_PORT", "TOTALRO_SMTP_PORT", "587") or 587)
    username = _smtp_value("TWDS_SMTP_USER", "TOTALRO_SMTP_USER")
    password = _smtp_value("TWDS_SMTP_PASSWORD", "TOTALRO_SMTP_PASSWORD")
    use_ssl = _bool_env("TWDS_SMTP_SSL", _bool_env("TOTALRO_SMTP_SSL", port == 465))
    use_starttls = _bool_env("TWDS_SMTP_STARTTLS", _bool_env("TOTALRO_SMTP_STARTTLS", not use_ssl))
    message = _support_message(report, bundle)
    if not host:
        (_feedback_outbox() / f"{report.ticket}.eml").write_bytes(message.as_bytes())
        return False, "SMTP is not configured. The report remains in the protected feedback outbox."
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                if use_starttls:
                    smtp.starttls()
                    smtp.ehlo()
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        return True, "sent"
    except Exception as exc:  # pragma: no cover - external SMTP
        (_feedback_outbox() / f"{report.ticket}.eml").write_bytes(message.as_bytes())
        current_app.logger.exception("Suite feedback notification failed for %s", report.ticket)
        return False, f"{type(exc).__name__}: email delivery failed; protected outbox copy retained."


def _send_receipt(report: FeedbackReport) -> tuple[bool, str]:
    if not report.user_email:
        return False, "No user email was available for a receipt."
    name = report.user_first_name or "there"
    body = f"""Hello {name},

Thank you for taking the time to send feedback about Total Water Design Suite.

We received your feedback successfully. Your reference is {report.ticket}.

We take user feedback seriously and it will be reviewed by the team. Where appropriate, we will follow up with a response or request for additional information.

Thank you for helping us improve Total Water Design Suite.

Total Water Design Suite
admin@totalrodesign.com
"""
    result = send_transactional_email(
        user_id=report.user_id,
        recipient=report.user_email,
        event_type="feedback_receipt",
        subject=f"We received your Total Water Design Suite feedback · {report.ticket}",
        body=body,
        template="feedback_receipt_v1",
    )
    return result.sent, result.detail


def _github_labels(report: FeedbackReport) -> list[str]:
    app_map = {
        "ro": "app:ro", "total ro design": "app:ro",
        "bio": "app:bio", "total bio design": "app:bio",
        "pretreatment": "app:pretreatment", "total pretreatment design": "app:pretreatment",
        "balance": "app:water-balance", "total water balance": "app:water-balance",
        "economics": "app:economics", "total water economics": "app:economics",
        "zld": "app:zld", "total zld design": "app:zld",
    }
    category = report.category if report.category in {"bug", "enhancement", "documentation"} else "feedback"
    labels = ["feedback", "admin-accepted", category]
    app_label = app_map.get(report.application.strip().lower())
    if app_label:
        labels.append(app_label)
    elif report.application.strip().lower() in {"suite", "platform"}:
        labels.append("platform")
    return labels


def _create_github_issue(report: FeedbackReport) -> tuple[bool, str, str]:
    if report.acceptance_state != "accepted" or not report.product_review_authorized:
        return False, "Feedback must be accepted and approved for product review first.", ""
    if not report.technical_requirement.strip():
        return False, "A sanitized technical requirement is required before GitHub promotion.", ""
    token = str(os.getenv("TWDS_GITHUB_TOKEN") or "").strip()
    repository = str(os.getenv("TWDS_GITHUB_REPOSITORY") or "total-water-design/total-water-design-suite").strip()
    if not token or "/" not in repository:
        return False, "GitHub issue integration is not configured on the server.", ""
    body = f"""## Administrator-accepted Suite feedback

Internal feedback ID: `{report.ticket}`
Affected application: {report.application}
Category: {report.category}
Priority: {report.priority}
Product-owner branch: `{report.product_owner_branch or 'Not assigned'}`

### Technical requirement
{report.technical_requirement}

### Reproduction / verification information
{report.reproduction_info or 'No sanitized reproduction information supplied.'}

Acceptance status: accepted by Suite administrator.

Customer name, email, account details, and raw project content are intentionally omitted from this GitHub mirror.
"""
    payload = json.dumps({
        "title": f"[{report.application}] {report.technical_requirement.strip()[:120]}",
        "body": body,
        "labels": _github_labels(report),
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/issues",
        data=payload,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Total-Water-Design-Suite",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
        return True, str(result.get("number") or ""), str(result.get("html_url") or "")
    except urllib.error.HTTPError as exc:  # pragma: no cover - external GitHub
        current_app.logger.exception("GitHub feedback promotion failed for %s", report.ticket)
        return False, f"GitHub returned HTTP {exc.code}.", ""
    except Exception as exc:  # pragma: no cover
        current_app.logger.exception("GitHub feedback promotion failed for %s", report.ticket)
        return False, f"{type(exc).__name__}: GitHub issue creation failed.", ""


@feedback_bp.post("/api/suite/feedback/report")
def submit_feedback():
    _user_required()
    payload = request.get_json(silent=True) or {}
    message = _clean(payload.get("message"), 12000)
    if len(message) < 3:
        return jsonify({"error": "Please describe the feedback or issue before submitting."}), 400
    now = _utcnow()
    ticket = f"TWDS-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    application = _clean(payload.get("application") or "suite", 64)
    category = _clean(payload.get("category") or "general", 40).lower()
    if category not in CATEGORIES:
        category = "other"
    screenshots = payload.get("screenshots") if isinstance(payload.get("screenshots"), list) else []
    bundle, saved, context_json = _write_bundle(ticket, payload, screenshots)
    user = current_user if current_user.is_authenticated else None
    report = FeedbackReport(
        ticket=ticket,
        user_id=getattr(user, "id", None),
        user_first_name=first_name(getattr(user, "full_name", "")) if user else "",
        user_email=_clean(getattr(user, "email", ""), 254) if user else "",
        application=application,
        application_version=_clean(payload.get("application_version"), 40),
        category=category,
        message=message,
        context_json=context_json,
        project_id=_clean(payload.get("project_id"), 100),
        project_revision=_clean(payload.get("project_revision"), 80),
        workspace=_clean(payload.get("workspace"), 120),
        status=STATUS_NEW,
        recipient=_recipient(),
        delivery_status="pending",
        receipt_email_status="pending",
        screenshots_count=saved,
        bundle_name=bundle.name,
    )
    db.session.add(report)
    db.session.flush()
    support_sent, detail = _deliver_support(report, bundle)
    report.delivery_status = "sent" if support_sent else "failed"
    report.last_error = "" if support_sent else detail[:2000]
    report.sent_at = _utcnow() if support_sent else None
    receipt_sent, receipt_detail = _send_receipt(report)
    report.receipt_email_status = "sent" if receipt_sent else "failed"
    if not receipt_sent and receipt_detail:
        report.last_error = (report.last_error + " | Receipt: " + receipt_detail).strip(" |")[:2000]
    audit("feedback_submitted", user=user, actor=user, detail=f"ticket={ticket}; application={application}; category={category}")
    record_telemetry("feedback_submitted", application=application, success=True,
                     metadata={"status": STATUS_NEW, "count": saved}, user=user)
    db.session.commit()
    return jsonify({
        "ok": True,
        "feedback_id": report.id,
        "ticket": ticket,
        "status": report.status,
        "receipt_email_status": report.receipt_email_status,
        "message": f"Thank you. Your feedback was received successfully. Reference: {ticket}.",
    })


def _filtered_feedback():
    query = select(FeedbackReport)
    application = str(request.args.get("application") or "").strip()
    status = str(request.args.get("status") or "").strip()
    user = str(request.args.get("user") or "").strip().lower()
    if application:
        query = query.where(FeedbackReport.application == application)
    if status:
        query = query.where(FeedbackReport.status == status)
    if user:
        query = query.where(func.lower(FeedbackReport.user_email).contains(user))
    return db.session.scalars(query.order_by(FeedbackReport.created_at.desc()).limit(1000)).all()


@feedback_bp.get("/api/suite/admin/feedback")
@admin_required
def feedback_admin_api():
    return jsonify({"feedback": [row.as_dict() for row in _filtered_feedback()]})


@feedback_bp.get("/admin/feedback")
@admin_required
def feedback_admin_page():
    rows = _filtered_feedback()
    applications = db.session.scalars(select(FeedbackReport.application).distinct().order_by(FeedbackReport.application)).all()
    return render_template(
        "auth/admin_feedback.html",
        feedback_rows=rows,
        applications=applications,
        statuses=FEEDBACK_STATUSES,
        categories=CATEGORIES,
        priorities=PRIORITIES,
    )


def _apply_admin_fields(report: FeedbackReport) -> None:
    report.admin_review = _clean(request.form.get("admin_review"), 12000)
    category = _clean(request.form.get("category") or report.category, 40).lower()
    report.category = category if category in CATEGORIES else report.category
    priority = _clean(request.form.get("priority") or report.priority, 24).lower()
    report.priority = priority if priority in PRIORITIES else report.priority
    report.technical_requirement = _clean(request.form.get("technical_requirement"), 12000)
    report.reproduction_info = _clean(request.form.get("reproduction_info"), 12000)
    report.product_owner_branch = _clean(request.form.get("product_owner_branch"), 160)
    report.response_draft = _clean(request.form.get("response_draft"), 12000)
    if report.response_draft and report.response_approval_state == "not_drafted":
        report.response_approval_state = "pending"
        if report.status not in {STATUS_IMPLEMENTED, STATUS_CLOSED}:
            report.status = STATUS_RESPONSE_DRAFTED
    report.duplicate_of_ticket = _clean(request.form.get("duplicate_of_ticket"), 64)


@feedback_bp.post("/admin/feedback/<int:report_id>/action")
@admin_required
def feedback_admin_action(report_id: int):
    report = db.get_or_404(FeedbackReport, report_id)
    action = str(request.form.get("action") or "save").strip().lower()
    _apply_admin_fields(report)
    report.reviewed_by_user_id = current_user.id
    report.reviewed_at = _utcnow()
    if report.status == STATUS_NEW:
        report.status = STATUS_ADMIN_REVIEW

    if action == "accept":
        report.acceptance_state = "accepted"
        report.status = STATUS_ACCEPTED
    elif action == "reject":
        report.acceptance_state = "rejected"
        report.product_review_authorized = False
        report.ai_processing_authorized = False
        report.status = STATUS_REJECTED
        report.final_disposition = "rejected"
    elif action == "request_info":
        report.status = STATUS_MORE_INFO
    elif action == "duplicate":
        report.status = STATUS_DUPLICATE
        report.final_disposition = "duplicate"
    elif action == "authorize_product_review":
        if report.acceptance_state != "accepted":
            flash("Accept the feedback before authorizing product review.", "error")
            return redirect(url_for("suite_feedback.feedback_admin_page"))
        report.product_review_authorized = True
        report.ai_processing_authorized = bool(request.form.get("ai_processing_authorized"))
        report.status = STATUS_PRODUCT_REVIEW
    elif action == "approve_response":
        if not report.response_draft:
            flash("Draft a response before approving it.", "error")
            return redirect(url_for("suite_feedback.feedback_admin_page"))
        report.response_approval_state = "approved"
        report.status = STATUS_RESPONSE_APPROVED
    elif action == "reject_response":
        report.response_approval_state = "rejected"
    elif action == "send_response":
        if report.response_approval_state != "approved" or not report.response_draft or not report.user_email:
            flash("An approved response draft and user email are required before sending.", "error")
            return redirect(url_for("suite_feedback.feedback_admin_page"))
        result = send_transactional_email(
            user_id=report.user_id,
            recipient=report.user_email,
            event_type="feedback_response",
            subject=f"Total Water Design Suite feedback follow-up · {report.ticket}",
            body=f"Hello {report.user_first_name or 'there'},\n\n{report.response_draft}\n\nThank you for helping us improve Total Water Design Suite.\n\nTotal Water Design Suite\nadmin@totalrodesign.com\n",
            template="feedback_response_v1",
        )
        if not result.sent:
            flash(f"Response was not sent: {result.detail}", "error")
            db.session.commit()
            return redirect(url_for("suite_feedback.feedback_admin_page"))
        report.response_sent_at = _utcnow()
        report.status = STATUS_RESPONSE_SENT
    elif action == "promote_github":
        ok, issue_id, issue_url = _create_github_issue(report)
        if not ok:
            flash(issue_id, "error")
            db.session.commit()
            return redirect(url_for("suite_feedback.feedback_admin_page"))
        report.github_issue_id = issue_id
        report.github_issue_url = issue_url
        report.status = STATUS_GITHUB
    elif action == "implemented":
        report.status = STATUS_IMPLEMENTED
        report.final_disposition = "implemented"
    elif action == "close":
        report.status = STATUS_CLOSED
        report.final_disposition = _clean(request.form.get("final_disposition") or report.final_disposition or "closed", 80)
    elif action != "save":
        abort(400)

    audit("feedback_admin_action", user=db.session.get(User, report.user_id) if report.user_id else None,
          actor=current_user, detail=f"ticket={report.ticket}; action={action}; status={report.status}")
    db.session.commit()
    flash(f"Feedback {report.ticket} updated: {report.status}.", "success")
    return redirect(url_for("suite_feedback.feedback_admin_page"))


@feedback_bp.post("/api/suite/admin/feedback/<int:report_id>/retry")
@admin_required
def retry_feedback(report_id: int):
    report = db.get_or_404(FeedbackReport, report_id)
    bundle = _feedback_outbox() / report.bundle_name
    if not bundle.exists():
        report.delivery_status = "failed"
        report.last_error = "Diagnostic bundle is missing from the protected outbox."
        db.session.commit()
        return jsonify({"ok": False, "error": report.last_error}), 409
    sent, detail = _deliver_support(report, bundle)
    report.delivery_status = "sent" if sent else "failed"
    report.last_error = "" if sent else detail[:2000]
    report.sent_at = _utcnow() if sent else None
    db.session.commit()
    return jsonify({"ok": sent, "feedback": report.as_dict(), "detail": detail})


def init_suite_feedback(app) -> None:
    if "suite_feedback" in app.blueprints:
        return
    with app.app_context():
        db.create_all()
        _ensure_feedback_schema()
        db.session.commit()
    app.register_blueprint(feedback_bp)
