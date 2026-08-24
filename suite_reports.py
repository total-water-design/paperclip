"""Suite Project Library and specialist report-provider interface.

Suite Core owns project identity, authorization, saved-state retrieval, and report
generation audit. Specialist applications own engineering report generation and
register a provider callable; their equations/report logic is not moved here.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from flask import Blueprint, abort, current_app, jsonify, render_template
from flask_login import current_user, login_required
from sqlalchemy import select

from auth import ProjectFamily, ProjectRevision, audit, db, record_telemetry

reports_bp = Blueprint("suite_reports", __name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ReportResult:
    """Customer-facing artifact reference returned by a specialist provider."""
    url: str = ""
    filename: str = ""
    media_type: str = "application/pdf"
    provider_reference: str = ""


@dataclass(frozen=True)
class ReportProvider:
    product_id: str
    provider_id: str
    label: str
    generate: Callable[[dict, dict], ReportResult]


_PROVIDERS: dict[str, ReportProvider] = {}


class ProjectReportHistory(db.Model):
    __tablename__ = "suite_project_report_history"
    id = db.Column(db.Integer, primary_key=True)
    revision_id = db.Column(db.Integer, db.ForeignKey("project_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id = db.Column(db.String(48), nullable=False, index=True)
    provider_id = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="generated", index=True)
    artifact_reference = db.Column(db.String(500), nullable=False, default="")
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)


def register_report_provider(product_id: str, *, provider_id: str, label: str,
                             generate: Callable[[dict, dict], ReportResult]) -> None:
    """Register one authoritative report provider for a Suite application.

    Registration belongs in the specialist application's integration layer.
    Re-registering with a different provider ID is rejected to avoid accidental
    report-engine replacement during reconciliation.
    """
    key = str(product_id or "").strip().lower()
    if not key or not callable(generate):
        raise ValueError("A product_id and callable report generator are required.")
    existing = _PROVIDERS.get(key)
    if existing and existing.provider_id != provider_id:
        raise RuntimeError(f"Report provider already registered for {key}: {existing.provider_id}")
    _PROVIDERS[key] = ReportProvider(key, str(provider_id)[:100], str(label)[:120], generate)


def report_provider_status(product_id: str) -> dict:
    provider = _PROVIDERS.get(str(product_id or "").strip().lower())
    return {
        "available": bool(provider),
        "provider_id": provider.provider_id if provider else "",
        "label": provider.label if provider else "Generate Full Report",
    }


def _row_and_family(revision_id: int):
    row = db.session.get(ProjectRevision, int(revision_id))
    family = db.session.get(ProjectFamily, row.family_id) if row else None
    return row, family


def _can_read(family: ProjectFamily | None) -> bool:
    return bool(family and current_user.is_authenticated and (family.owner_user_id == current_user.id or current_user.is_admin))


def _project_context(row: ProjectRevision, family: ProjectFamily) -> dict:
    return {
        "revision_id": row.id,
        "product_id": row.product_id,
        "visible_id": row.visible_id,
        "revision": row.revision,
        "name": row.name,
        "family_uuid": family.family_uuid,
        "country_code": family.project_country_code or "",
        "country": family.project_country_name or "",
        "owner_user_id": family.owner_user_id,
        "saved_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@reports_bp.get("/projects")
@login_required
def project_library():
    query = (
        select(ProjectRevision, ProjectFamily)
        .join(ProjectFamily, ProjectFamily.id == ProjectRevision.family_id)
        .where(ProjectFamily.owner_user_id == current_user.id)
        .order_by(ProjectRevision.updated_at.desc(), ProjectRevision.id.desc())
    )
    rows = db.session.execute(query).all()
    projects = [{
        "row": row,
        "family": family,
        "provider": report_provider_status(row.product_id),
    } for row, family in rows]
    return render_template("auth/project_library.html", projects=projects)


@reports_bp.get("/api/suite/report-providers")
@login_required
def provider_api():
    return jsonify({"providers": {key: report_provider_status(key) for key in sorted(_PROVIDERS)}})


@reports_bp.post("/api/suite/projects/<int:revision_id>/full-report")
@login_required
def generate_full_report(revision_id: int):
    row, family = _row_and_family(revision_id)
    if not row or not _can_read(family):
        abort(404)
    provider = _PROVIDERS.get(row.product_id)
    if not provider:
        return jsonify({
            "error": "The application has not registered its full-report provider yet.",
            "product_id": row.product_id,
            "provider_required": True,
        }), 409
    try:
        snapshot = json.loads(row.snapshot_json)
    except json.JSONDecodeError:
        return jsonify({"error": "The saved project state is not valid JSON and cannot be reported."}), 409
    context = _project_context(row, family)
    try:
        result = provider.generate(snapshot, context)
        if not isinstance(result, ReportResult):
            raise TypeError("Report provider must return ReportResult.")
    except Exception as exc:
        current_app.logger.exception("Full report provider failed for %s", row.visible_id)
        db.session.add(ProjectReportHistory(
            revision_id=row.id, user_id=current_user.id, product_id=row.product_id,
            provider_id=provider.provider_id, status="failed", artifact_reference="",
        ))
        audit("project_full_report_failed", user=current_user, actor=current_user,
              detail=f"project={row.visible_id}; provider={provider.provider_id}; error={type(exc).__name__}")
        db.session.commit()
        return jsonify({"error": "The application report provider could not generate this saved project report."}), 500
    artifact = result.url or result.filename or result.provider_reference
    db.session.add(ProjectReportHistory(
        revision_id=row.id,
        user_id=current_user.id,
        product_id=row.product_id,
        provider_id=provider.provider_id,
        status="generated",
        artifact_reference=str(artifact)[:500],
    ))
    audit("project_full_report_generated", user=current_user, actor=current_user,
          detail=f"project={row.visible_id}; provider={provider.provider_id}")
    record_telemetry("project_report_generated", application=row.product_id,
                     metadata={"product_id": row.product_id, "status": "generated"}, user=current_user)
    db.session.commit()
    return jsonify({
        "ok": True,
        "project_id": row.visible_id,
        "revision": row.revision,
        "provider_id": provider.provider_id,
        "report": {
            "url": result.url,
            "filename": result.filename,
            "media_type": result.media_type,
            "reference": result.provider_reference,
        },
    })


def init_suite_reports(app) -> None:
    if "suite_reports" in app.blueprints:
        return
    with app.app_context():
        db.create_all()
    app.register_blueprint(reports_bp)
