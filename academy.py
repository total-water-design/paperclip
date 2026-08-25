"""Total Water Academy Flask blueprint and learning-progress persistence.

Academy teaches engineering through the Suite but does not own specialist
engineering equations. Future numerical practicals must call narrow, validated
adapters exposed by the owning application/engine branch.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import secrets
from typing import Any
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy import UniqueConstraint, select

from auth import db, product_entitlement_for
from academy_content import (
    ACADEMY_VERSION,
    DEFAULT_CAPSTONE_PASS_PERCENT,
    DIPLOMA_DISCLAIMER,
    DIPLOMA_TITLE,
    LEVELS,
    PILOT_MODULE,
    curriculum,
    evaluate_activity,
    level_by_id,
    module_by_id,
    validate_curriculum,
)
from academy_i18n import (
    current_locale,
    language_options,
    locale_info,
    localize,
    localize_assessment_result,
    normalize_locale,
    tr,
)
from suite_commercial import precommercial_entitlement_allowed

academy_bp = Blueprint("academy", __name__, url_prefix="/academy")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_load(value: str | None, fallback):
    try:
        parsed = json.loads(value or "")
    except (TypeError, ValueError):
        return fallback
    return parsed


def _academy_access_allowed() -> bool:
    if not current_app.config.get("AUTH_ENABLED", False):
        return True
    if not current_user.is_authenticated or getattr(current_user, "status", "") != "active":
        return False
    if bool(getattr(current_user, "is_admin", False)):
        return True
    if precommercial_entitlement_allowed(current_user, "academy"):
        return True
    entitlement = product_entitlement_for(current_user, "academy")
    return bool(entitlement and entitlement.enabled and entitlement.is_current())


def _require_academy_access():
    if _academy_access_allowed():
        return None
    if current_app.config.get("AUTH_ENABLED", False) and not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.path))
    return render_template("academy/access_denied.html"), 403


def _user_id() -> int | None:
    return int(current_user.id) if current_user.is_authenticated else None


def _safe_academy_return(value: object) -> str:
    target = str(value or "").strip()
    if not target:
        return "/academy"
    parsed = urlsplit(target)
    academy_local = target == "/academy" or target.startswith("/academy/") or target.startswith("/academy?")
    if parsed.scheme or parsed.netloc or not academy_local or target.startswith("//"):
        return "/academy"
    return target


class AcademyModuleProgress(db.Model):
    __tablename__ = "academy_module_progress"
    __table_args__ = (UniqueConstraint("user_id", "module_id", name="uq_academy_user_module_progress"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    level_id = db.Column(db.String(16), nullable=False, index=True)
    module_id = db.Column(db.String(24), nullable=False, index=True)
    state = db.Column(db.String(24), nullable=False, default="not_started", index=True)
    completed_steps_json = db.Column(db.Text, nullable=False, default="[]")
    competencies_json = db.Column(db.Text, nullable=False, default="[]")
    best_score = db.Column(db.Float, nullable=False, default=0.0)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    engagement_seconds = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    @property
    def completed_steps(self) -> list[str]:
        value = _json_load(self.completed_steps_json, [])
        return [str(item) for item in value] if isinstance(value, list) else []

    @property
    def competencies(self) -> list[str]:
        value = _json_load(self.competencies_json, [])
        return [str(item) for item in value] if isinstance(value, list) else []

    def add_step(self, step_id: str) -> None:
        values = self.completed_steps
        key = str(step_id)
        if key not in values:
            values.append(key)
        self.completed_steps_json = json.dumps(values, separators=(",", ":"))
        if self.state == "not_started":
            self.state = "in_progress"
        if not self.started_at:
            self.started_at = _utcnow()

    def add_competencies(self, values: list[str]) -> None:
        current = self.competencies
        for value in values:
            key = str(value or "").strip()
            if key and key not in current:
                current.append(key)
        self.competencies_json = json.dumps(current, separators=(",", ":"))


class AcademyAttempt(db.Model):
    __tablename__ = "academy_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    level_id = db.Column(db.String(16), nullable=False, index=True)
    module_id = db.Column(db.String(24), nullable=False, index=True)
    activity_id = db.Column(db.String(48), nullable=False, index=True)
    activity_kind = db.Column(db.String(24), nullable=False)
    answer_json = db.Column(db.Text, nullable=False, default="null")
    correct = db.Column(db.Boolean, nullable=False, default=False)
    score = db.Column(db.Float, nullable=False, default=0.0)
    explanation = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)


class AcademyAward(db.Model):
    __tablename__ = "academy_awards"
    __table_args__ = (UniqueConstraint("user_id", "course_version", "award_type", name="uq_academy_user_course_award"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_version = db.Column(db.String(24), nullable=False, default=ACADEMY_VERSION)
    award_type = db.Column(db.String(32), nullable=False, default="course_diploma")
    title = db.Column(db.String(240), nullable=False, default=DIPLOMA_TITLE)
    verification_token = db.Column(db.String(80), nullable=False, unique=True, index=True)
    status = db.Column(db.String(24), nullable=False, default="issued", index=True)
    issued_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)


def _module_progress(module_id: str, create: bool = True) -> AcademyModuleProgress | None:
    user_id = _user_id()
    if user_id is None:
        return None
    module = module_by_id(module_id)
    if not module:
        return None
    level_id = module.get("level_id") or str(module_id).split("-M", 1)[0]
    row = db.session.scalar(select(AcademyModuleProgress).where(
        AcademyModuleProgress.user_id == user_id,
        AcademyModuleProgress.module_id == str(module_id),
    ))
    if not row and create:
        row = AcademyModuleProgress(user_id=user_id, level_id=level_id, module_id=str(module_id))
        db.session.add(row)
        db.session.flush()
    return row


def _pilot_required_steps() -> set[str]:
    return {str(step["id"]) for step in PILOT_MODULE["steps"]}


def _refresh_pilot_completion(row: AcademyModuleProgress) -> None:
    if row.module_id != PILOT_MODULE["id"]:
        return
    if _pilot_required_steps().issubset(set(row.completed_steps)) and row.best_score >= 75.0:
        row.state = "completed"
        row.completed_at = row.completed_at or _utcnow()


def _all_module_ids() -> list[str]:
    return [module["id"] for level in LEVELS for module in level["modules"]]


def diploma_status(user_id: int | None) -> dict[str, Any]:
    module_ids = _all_module_ids()
    if user_id is None:
        return {
            "eligible": False,
            "completed_modules": 0,
            "required_modules": len(module_ids),
            "capstone_required_percent": DEFAULT_CAPSTONE_PASS_PERCENT,
            "reason": "Sign in to track diploma progress.",
        }
    rows = db.session.scalars(select(AcademyModuleProgress).where(AcademyModuleProgress.user_id == user_id)).all()
    completed = {row.module_id for row in rows if row.state == "completed"}
    capstone = next((row for row in rows if row.module_id == "L10-M05"), None)
    eligible = set(module_ids).issubset(completed) and bool(capstone and capstone.best_score >= DEFAULT_CAPSTONE_PASS_PERCENT)
    return {
        "eligible": eligible,
        "completed_modules": len(completed.intersection(module_ids)),
        "required_modules": len(module_ids),
        "capstone_required_percent": DEFAULT_CAPSTONE_PASS_PERCENT,
        "reason": "All ten levels and the final capstone assessment must be completed." if not eligible else "All course completion requirements are satisfied.",
    }


def _overview_progress() -> dict[str, Any]:
    user_id = _user_id()
    total_modules = len(_all_module_ids())
    if user_id is None:
        return {"completed_modules": 0, "total_modules": total_modules, "percent": 0.0, "engagement_hours": 0.0, "attempts": 0}
    rows = db.session.scalars(select(AcademyModuleProgress).where(AcademyModuleProgress.user_id == user_id)).all()
    completed = sum(1 for row in rows if row.state == "completed")
    engagement = sum(int(row.engagement_seconds or 0) for row in rows)
    attempts = sum(int(row.attempts or 0) for row in rows)
    return {
        "completed_modules": completed,
        "total_modules": total_modules,
        "percent": round(100.0 * completed / max(1, total_modules), 1),
        "engagement_hours": round(engagement / 3600.0, 1),
        "attempts": attempts,
    }


@academy_bp.post("/language")
def set_language():
    locale = normalize_locale(request.form.get("locale"))
    if not locale:
        return jsonify({"error": "Unsupported Academy language."}), 400
    session["academy_locale"] = locale
    return redirect(_safe_academy_return(request.form.get("next")))


@academy_bp.get("")
def home():
    gate = _require_academy_access()
    if gate is not None:
        return gate
    loc = current_locale()
    return render_template(
        "academy/index.html",
        course=localize(curriculum(), loc),
        progress=_overview_progress(),
        diploma=localize(diploma_status(_user_id()), loc),
        app_name="Total Water Academy",
        app_id="academy",
        app_version=ACADEMY_VERSION,
        app_accent="#1A7F8E",
        app_icon_asset="branding/suite/total_water_academy_icon.svg",
    )


@academy_bp.get("/levels/<level_id>")
def level(level_id: str):
    gate = _require_academy_access()
    if gate is not None:
        return gate
    item = level_by_id(level_id)
    if not item:
        abort(404)
    loc = current_locale()
    return render_template(
        "academy/level.html", level=localize(item, loc), course=localize(curriculum(), loc), progress=_overview_progress(),
        app_name="Total Water Academy", app_id="academy", app_version=ACADEMY_VERSION,
        app_accent="#1A7F8E", app_icon_asset="branding/suite/total_water_academy_icon.svg",
    )


@academy_bp.get("/modules/<module_id>")
def module(module_id: str):
    gate = _require_academy_access()
    if gate is not None:
        return gate
    item = module_by_id(module_id)
    if not item:
        abort(404)
    progress = _module_progress(module_id, create=True)
    if progress:
        if progress.state == "not_started":
            progress.state = "in_progress"
            progress.started_at = _utcnow()
        db.session.commit()
    is_pilot = module_id.upper() == PILOT_MODULE["id"]
    loc = current_locale()
    return render_template(
        "academy/module.html", module=localize(item, loc), is_pilot=is_pilot,
        module_progress=progress, course=localize(curriculum(), loc), overall=_overview_progress(),
        app_name="Total Water Academy", app_id="academy", app_version=ACADEMY_VERSION,
        app_accent="#1A7F8E", app_icon_asset="branding/suite/total_water_academy_icon.svg",
    )


@academy_bp.get("/api/curriculum")
def curriculum_api():
    gate = _require_academy_access()
    if gate is not None:
        return jsonify({"error": tr("academy_access_required")}), 403
    return jsonify(localize(curriculum(), current_locale()))


@academy_bp.post("/api/modules/<module_id>/step")
def complete_step_api(module_id: str):
    gate = _require_academy_access()
    if gate is not None:
        return jsonify({"error": tr("academy_access_required")}), 403
    if module_id.upper() != PILOT_MODULE["id"]:
        return jsonify({"error": tr("module_not_authored_api")}), 409
    payload = request.get_json(force=True) or {}
    step_id = str(payload.get("step_id") or "").strip()
    valid_steps = {step["id"] for step in PILOT_MODULE["steps"]}
    if step_id not in valid_steps:
        return jsonify({"error": tr("unknown_step")}), 400
    step = next(step for step in PILOT_MODULE["steps"] if step["id"] == step_id)
    if step["kind"] != "concept":
        return jsonify({"error": tr("assessed_via_submission")}), 400
    row = _module_progress(module_id, create=True)
    if not row:
        return jsonify({"ok": True, "preview": True})
    row.add_step(step_id)
    _refresh_pilot_completion(row)
    db.session.commit()
    return jsonify({"ok": True, "state": row.state, "completed_steps": row.completed_steps})


@academy_bp.post("/api/modules/<module_id>/assess")
def assess_api(module_id: str):
    gate = _require_academy_access()
    if gate is not None:
        return jsonify({"error": tr("academy_access_required")}), 403
    if module_id.upper() != PILOT_MODULE["id"]:
        return jsonify({"error": tr("module_no_assessment")}), 409
    payload = request.get_json(force=True) or {}
    activity_id = str(payload.get("activity_id") or "").strip()
    try:
        result = evaluate_activity(activity_id, payload.get("answer"))
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    activity = next(step for step in PILOT_MODULE["steps"] if step["id"] == activity_id)
    row = _module_progress(module_id, create=True)
    if row:
        row.attempts = int(row.attempts or 0) + 1
        row.best_score = max(float(row.best_score or 0.0), float(result["score"]))
        row.add_competencies([value for value in result.get("competencies", []) if value])
        if result["correct"]:
            row.add_step(activity_id)
        db.session.add(AcademyAttempt(
            user_id=row.user_id,
            level_id=row.level_id,
            module_id=row.module_id,
            activity_id=activity_id,
            activity_kind=activity["kind"],
            answer_json=json.dumps(payload.get("answer"), separators=(",", ":"), ensure_ascii=False),
            correct=bool(result["correct"]),
            score=float(result["score"]),
            explanation=str(result.get("feedback") or "")[:5000],
        ))
        _refresh_pilot_completion(row)
        db.session.commit()
        result["module_state"] = row.state
        result["completed_steps"] = row.completed_steps
        result["attempts"] = row.attempts
    else:
        result["preview"] = True
    return jsonify(localize_assessment_result(activity, result, current_locale()))


@academy_bp.post("/api/modules/<module_id>/engagement")
def engagement_api(module_id: str):
    gate = _require_academy_access()
    if gate is not None:
        return jsonify({"error": tr("academy_access_required")}), 403
    payload = request.get_json(silent=True) or {}
    try:
        seconds = int(payload.get("seconds", 0))
    except (TypeError, ValueError):
        seconds = 0
    seconds = max(0, min(seconds, 120))
    row = _module_progress(module_id, create=True)
    if row and seconds:
        row.engagement_seconds = int(row.engagement_seconds or 0) + seconds
        db.session.commit()
    return jsonify({"ok": True, "credited_seconds": seconds})


@academy_bp.get("/diploma")
def diploma():
    gate = _require_academy_access()
    if gate is not None:
        return gate
    loc = current_locale()
    status = localize(diploma_status(_user_id()), loc)
    award = None
    user_id = _user_id()
    if user_id is not None:
        award = db.session.scalar(select(AcademyAward).where(
            AcademyAward.user_id == user_id,
            AcademyAward.course_version == ACADEMY_VERSION,
            AcademyAward.award_type == "course_diploma",
        ))
    return render_template(
        "academy/diploma.html", diploma=status, award=award,
        diploma_title=localize(DIPLOMA_TITLE, loc), diploma_disclaimer=localize(DIPLOMA_DISCLAIMER, loc),
        app_name="Total Water Academy", app_id="academy", app_version=ACADEMY_VERSION,
        app_accent="#1A7F8E", app_icon_asset="branding/suite/total_water_academy_icon.svg",
    )


@academy_bp.post("/api/diploma/issue")
def issue_diploma_api():
    gate = _require_academy_access()
    if gate is not None:
        return jsonify({"error": tr("academy_access_required")}), 403
    user_id = _user_id()
    status = diploma_status(user_id)
    if not status["eligible"]:
        localized_status = localize(status, current_locale())
        return jsonify({"error": localized_status["reason"], **localized_status}), 409
    award = db.session.scalar(select(AcademyAward).where(
        AcademyAward.user_id == user_id,
        AcademyAward.course_version == ACADEMY_VERSION,
        AcademyAward.award_type == "course_diploma",
    ))
    if not award:
        award = AcademyAward(
            user_id=user_id,
            course_version=ACADEMY_VERSION,
            award_type="course_diploma",
            title=DIPLOMA_TITLE,
            verification_token=secrets.token_urlsafe(24),
        )
        db.session.add(award)
        db.session.commit()
    loc = current_locale()
    return jsonify({
        "ok": True, "title": localize(award.title, loc), "issued_at": award.issued_at.isoformat(),
        "verification_token": award.verification_token, "disclaimer": localize(DIPLOMA_DISCLAIMER, loc),
    })


def init_total_water_academy(app) -> None:
    if "academy" in app.blueprints:
        return
    errors = validate_curriculum()
    if errors:
        raise RuntimeError("Invalid Total Water Academy curriculum: " + "; ".join(errors))
    app.jinja_env.globals.update(
        academy_tr=tr,
        academy_current_locale=current_locale,
        academy_locale_info=locale_info,
        academy_language_options=language_options,
    )
    app.register_blueprint(academy_bp)
    with app.app_context():
        db.create_all()
