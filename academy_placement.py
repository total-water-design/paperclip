"""Total Water Academy entry diagnostic and learning-profile service.

The diagnostic personalizes learning emphasis; it does not grant engineering
credit, waive diploma requirements, or replace module assessments. Authentication
and product access remain owned by Suite Core.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from urllib.parse import urlsplit

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_login import current_user
from sqlalchemy import select

from auth import db, product_entitlement_for
from academy_content import ACADEMY_VERSION
from academy_i18n import current_locale, localize
from suite_commercial import precommercial_entitlement_allowed

academy_placement_bp = Blueprint("academy_placement", __name__, url_prefix="/academy")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_next(value: object) -> str:
    target = str(value or "").strip()
    if not target:
        return "/academy"
    parsed = urlsplit(target)
    academy_local = target == "/academy" or target.startswith("/academy/") or target.startswith("/academy?")
    if parsed.scheme or parsed.netloc or not academy_local or target.startswith("//"):
        return "/academy"
    return target


def _is_academy_path(path: object) -> bool:
    value = str(path or "")
    return value == "/academy" or value.startswith("/academy/")


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


SELF_RATING_DOMAINS = (
    ("process_math", "Engineering units, algebra and process variables"),
    ("mass_energy", "Mass, component and energy balances"),
    ("transport", "Heat transfer, fluid flow and mass transfer"),
    ("chemistry", "Water chemistry and chemical-equilibrium concepts"),
    ("water_treatment", "Pretreatment, biological and membrane treatment"),
    ("electrical_controls", "Pumps, electrical systems, instrumentation and controls"),
)

RATING_LABELS = {
    0: "New to this",
    1: "Basic awareness",
    2: "Can follow worked examples",
    3: "Can solve routine problems",
    4: "Comfortable applying it in design",
}

DIAGNOSTIC_QUESTIONS = (
    {"id": "q1", "domain": "units", "prompt": "A flow of 1 m³/h is equal to:", "choices": ["1 L/h", "100 L/h", "1,000 L/h", "10,000 L/h"], "answer": 2},
    {"id": "q2", "domain": "mass_balance", "prompt": "A process receives 100 m³/h and produces 75 m³/h of product. With no accumulation, the remaining outlet flow is:", "choices": ["15 m³/h", "25 m³/h", "75 m³/h", "175 m³/h"], "answer": 1},
    {"id": "q3", "domain": "mass_balance", "prompt": "Two liquid streams of 20 and 30 m³/h mix with no loss. The mixed flow is:", "choices": ["10 m³/h", "25 m³/h", "50 m³/h", "600 m³/h"], "answer": 2},
    {"id": "q4", "domain": "energy_heat", "prompt": "In an ideal steady heat exchanger with negligible heat loss, heat removed from the hot stream is approximately:", "choices": ["Destroyed", "Equal to heat gained by the cold stream", "Independent of flow", "Always zero"], "answer": 1},
    {"id": "q5", "domain": "energy_heat", "prompt": "When water is evaporated, which energy term becomes especially important?", "choices": ["Latent heat of vaporization", "Only static pressure", "Electrical frequency", "Turbidity"], "answer": 0},
    {"id": "q6", "domain": "fluids", "prompt": "A pump in a liquid system primarily adds:", "choices": ["Hydraulic head/energy", "Salt rejection", "Biomass", "Alkalinity"], "answer": 0},
    {"id": "q7", "domain": "fluids", "prompt": "Closing a throttling valve in a flowing line generally causes the valve pressure drop to:", "choices": ["Disappear", "Increase", "Become negative by definition", "Equal osmotic pressure"], "answer": 1},
    {"id": "q8", "domain": "mass_transfer", "prompt": "Molecular diffusion is driven primarily by:", "choices": ["A concentration/chemical-potential gradient", "Motor RPM alone", "Pipe color", "PLC scan time"], "answer": 0},
    {"id": "q9", "domain": "chemistry", "prompt": "Compared with pH 8 water, pH 6 water is generally:", "choices": ["More acidic", "More alkaline", "Always more saline", "Always harder"], "answer": 0},
    {"id": "q10", "domain": "water_process", "prompt": "Why is pretreatment commonly placed before a sensitive membrane process?", "choices": ["To protect the membrane from upstream water-quality risks", "To make all plants identical", "Only to raise voltage", "To eliminate all reject streams"], "answer": 0},
    {"id": "q11", "domain": "electrical_controls", "prompt": "A VFD is commonly used on an AC motor to:", "choices": ["Vary motor speed by controlling electrical frequency/voltage", "Measure pH", "Remove dissolved salt", "Replace every contactor in all circuits"], "answer": 0},
    {"id": "q12", "domain": "electrical_controls", "prompt": "A process interlock is primarily intended to:", "choices": ["Prevent or stop an unsafe/invalid operating sequence", "Increase membrane pore size", "Calculate CAPEX automatically", "Replace all operator training"], "answer": 0},
)

DOMAIN_LABELS = {
    "units": "engineering units",
    "mass_balance": "mass and component balances",
    "energy_heat": "energy balance and heat transfer",
    "fluids": "fluid flow and hydraulics",
    "mass_transfer": "mass transfer and diffusion",
    "chemistry": "water chemistry",
    "water_process": "water-treatment process reasoning",
    "electrical_controls": "electrical and process control fundamentals",
}


class AcademyLearningProfile(db.Model):
    __tablename__ = "academy_learning_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    background = db.Column(db.String(80), nullable=False, default="")
    years_experience = db.Column(db.Integer, nullable=False, default=0)
    learning_goal = db.Column(db.String(80), nullable=False, default="full_diploma")
    self_rating_json = db.Column(db.Text, nullable=False, default="{}")
    diagnostic_answers_json = db.Column(db.Text, nullable=False, default="{}")
    domain_scores_json = db.Column(db.Text, nullable=False, default="{}")
    knowledge_gaps_json = db.Column(db.Text, nullable=False, default="[]")
    diagnostic_score = db.Column(db.Float, nullable=False, default=0.0)
    recommended_track = db.Column(db.String(80), nullable=False, default="Foundation Builder")
    completed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    @property
    def domain_scores(self) -> dict:
        try:
            value = json.loads(self.domain_scores_json or "{}")
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}

    @property
    def knowledge_gaps(self) -> list[str]:
        try:
            value = json.loads(self.knowledge_gaps_json or "[]")
        except (TypeError, ValueError):
            return []
        return [str(x) for x in value] if isinstance(value, list) else []


def _profile_for_user() -> AcademyLearningProfile | None:
    if not current_user.is_authenticated:
        return None
    return db.session.scalar(select(AcademyLearningProfile).where(AcademyLearningProfile.user_id == current_user.id))


def score_diagnostic(answers: dict[str, int]) -> tuple[float, dict[str, float]]:
    per_domain: dict[str, list[bool]] = {}
    correct = 0
    for question in DIAGNOSTIC_QUESTIONS:
        chosen = answers.get(question["id"], -1)
        is_correct = int(chosen) == int(question["answer"])
        correct += int(is_correct)
        per_domain.setdefault(question["domain"], []).append(is_correct)
    overall = 100.0 * correct / len(DIAGNOSTIC_QUESTIONS)
    domain_scores = {domain: round(100.0 * sum(1 for item in values if item) / len(values), 1) for domain, values in per_domain.items()}
    return round(overall, 1), domain_scores


def recommend_track(score: float) -> str:
    if score < 55.0:
        return "Foundation Builder"
    if score < 80.0:
        return "Engineering Refresher"
    return "Accelerated Review"


def _knowledge_gaps(domain_scores: dict[str, float], self_ratings: dict[str, int]) -> list[str]:
    gaps = [DOMAIN_LABELS[key] for key, value in domain_scores.items() if float(value) < 60.0]
    self_to_domain = {
        "process_math": "engineering units",
        "mass_energy": "mass/energy balances",
        "transport": "transport phenomena",
        "chemistry": "water chemistry",
        "water_treatment": "water-treatment process reasoning",
        "electrical_controls": "electrical and process controls",
    }
    for key, label in self_to_domain.items():
        if int(self_ratings.get(key, 0)) <= 1 and label not in gaps:
            gaps.append(label)
    return gaps


@academy_placement_bp.route("/placement", methods=["GET", "POST"])
def placement():
    if current_app.config.get("AUTH_ENABLED", False) and not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.full_path))
    if not _academy_access_allowed():
        return render_template("academy/access_denied.html"), 403

    profile = _profile_for_user()
    destination = _safe_next(request.values.get("next"))
    if request.method == "POST":
        background = str(request.form.get("background") or "").strip()[:80]
        learning_goal = str(request.form.get("learning_goal") or "full_diploma").strip()[:80]
        try:
            years = max(0, min(60, int(request.form.get("years_experience") or 0)))
        except (TypeError, ValueError):
            years = 0

        self_ratings: dict[str, int] = {}
        for key, _ in SELF_RATING_DOMAINS:
            try:
                self_ratings[key] = max(0, min(4, int(request.form.get(f"rating_{key}") or 0)))
            except (TypeError, ValueError):
                self_ratings[key] = 0

        answers: dict[str, int] = {}
        for question in DIAGNOSTIC_QUESTIONS:
            try:
                answers[question["id"]] = int(request.form.get(question["id"], -1))
            except (TypeError, ValueError):
                answers[question["id"]] = -1

        score, domain_scores = score_diagnostic(answers)
        track = recommend_track(score)
        gaps = _knowledge_gaps(domain_scores, self_ratings)
        if profile is None and current_user.is_authenticated:
            profile = AcademyLearningProfile(user_id=current_user.id)
            db.session.add(profile)
        if profile is not None:
            profile.background = background
            profile.years_experience = years
            profile.learning_goal = learning_goal
            profile.self_rating_json = json.dumps(self_ratings, separators=(",", ":"))
            profile.diagnostic_answers_json = json.dumps(answers, separators=(",", ":"))
            profile.domain_scores_json = json.dumps(domain_scores, separators=(",", ":"))
            profile.knowledge_gaps_json = json.dumps(gaps, separators=(",", ":"))
            profile.diagnostic_score = score
            profile.recommended_track = track
            profile.completed_at = _utcnow()
            db.session.commit()
        session.pop("academy_placement_skipped", None)
        return redirect(url_for("academy_placement.placement", saved=1, next=destination))

    loc = current_locale()
    return render_template(
        "academy/placement.html",
        profile=profile,
        localized_track=localize(profile.recommended_track, loc) if profile else None,
        localized_gaps=localize(profile.knowledge_gaps, loc) if profile else [],
        self_rating_domains=localize(SELF_RATING_DOMAINS, loc),
        rating_labels=localize(RATING_LABELS, loc),
        questions=localize(DIAGNOSTIC_QUESTIONS, loc),
        destination=destination,
        app_name="Total Water Academy",
        app_id="academy",
        app_version=ACADEMY_VERSION,
        app_accent="#1A7F8E",
        app_icon_asset="branding/suite/total_water_academy_icon.svg",
    )


def init_academy_placement(app) -> None:
    if "academy_placement" in app.blueprints:
        return
    app.register_blueprint(academy_placement_bp)

    @app.before_request
    def _prompt_academy_placement_on_first_entry():
        path = request.path or ""
        if not _is_academy_path(path) or path.startswith("/academy/placement") or path.startswith("/academy/api/") or path.startswith("/academy/language"):
            return None
        if request.args.get("skip_placement") == "1":
            session["academy_placement_skipped"] = True
            return None
        if session.get("academy_placement_skipped"):
            return None
        if not current_app.config.get("AUTH_ENABLED", False) or not current_user.is_authenticated:
            return None
        if not _academy_access_allowed() or _profile_for_user() is not None:
            return None
        return redirect(url_for("academy_placement.placement", next=request.full_path))

    with app.app_context():
        db.create_all()
