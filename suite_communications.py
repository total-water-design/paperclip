"""Suite release records, What's New content, and product-update communications.

Customer-visible updates are derived from administrator-approved release and
roadmap records, never from raw Git branches. Product-update email is gated on a
release having been validated, deployed, and health-verified.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, render_template, request, url_for, flash
from flask_login import current_user, login_required
from sqlalchemy import select

from auth import User, admin_required, audit, db
from suite_mail import first_name, send_transactional_email

communications_bp = Blueprint("suite_communications", __name__)

WHATS_NEW_CARD_DEFAULTS = {
    "recently_updated": ("Recently Updated", "Changes already deployed"),
    "roadmap": ("What We're Working On", "Administrator-approved roadmap"),
    "commercial_launch": ("Commercial Launch", "Current estimated timing"),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CommunicationPreference(db.Model):
    __tablename__ = "suite_communication_preferences"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    product_updates_enabled = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class ReleaseRecord(db.Model):
    __tablename__ = "suite_release_records"
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(80), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False, default="")
    highlights_json = db.Column(db.Text, nullable=False, default="[]")
    applications_json = db.Column(db.Text, nullable=False, default="[]")
    deployment_sha = db.Column(db.String(80), nullable=False, default="")
    status = db.Column(db.String(24), nullable=False, default="draft", index=True)
    public = db.Column(db.Boolean, nullable=False, default=False, index=True)
    update_email_approved = db.Column(db.Boolean, nullable=False, default=False)
    validated_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    deployed_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    health_verified_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    announcement_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    @property
    def highlights(self) -> list[str]:
        try:
            values = json.loads(self.highlights_json or "[]")
            return [str(x) for x in values if str(x).strip()][:6]
        except Exception:
            return []

    def is_customer_ready(self) -> bool:
        return bool(
            self.status == "deployed"
            and self.validated_at
            and self.deployed_at
            and self.health_verified_at
        )


class RoadmapItem(db.Model):
    __tablename__ = "suite_roadmap_items"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False, default="")
    application = db.Column(db.String(64), nullable=False, default="suite", index=True)
    status = db.Column(db.String(24), nullable=False, default="approved", index=True)
    public = db.Column(db.Boolean, nullable=False, default=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=100)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class SuiteSetting(db.Model):
    __tablename__ = "suite_settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True, index=True)
    value = db.Column(db.Text, nullable=False, default="")
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class WhatsNewCard(db.Model):
    """Administrator-reviewed public copy for one fixed What's New section."""

    __tablename__ = "suite_whats_new_cards"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), nullable=False, unique=True, index=True)
    title = db.Column(db.String(200), nullable=False, default="")
    summary = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(24), nullable=False, default="draft", index=True)
    release_label = db.Column(db.String(80), nullable=False, default="")
    public = db.Column(db.Boolean, nullable=False, default=False, index=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    def is_public_ready(self) -> bool:
        return bool(
            self.slug in WHATS_NEW_CARD_DEFAULTS
            and self.public
            and self.status == "approved"
            and self.reviewed_at
            and self.title.strip()
            and self.summary.strip()
            and self.release_label.strip()
        )


def _card_view(slug: str, row: WhatsNewCard | None) -> dict:
    default_title, default_summary = WHATS_NEW_CARD_DEFAULTS[slug]
    ready = bool(row and row.is_public_ready())
    return {
        "slug": slug,
        "title": row.title if ready else default_title,
        "summary": row.summary if ready else default_summary,
        "status": row.status if ready else "not_published",
        "release_label": row.release_label if ready else "No approved update",
        "updated_at": row.updated_at if ready else None,
        "public_ready": ready,
    }


def _preference(user_id: int, create: bool = True) -> CommunicationPreference | None:
    row = db.session.scalar(select(CommunicationPreference).where(CommunicationPreference.user_id == int(user_id)))
    if not row and create:
        row = CommunicationPreference(user_id=int(user_id), product_updates_enabled=False)
        db.session.add(row)
        db.session.flush()
    return row


def _setting(key: str) -> str:
    row = db.session.scalar(select(SuiteSetting).where(SuiteSetting.key == key))
    return str(row.value) if row else ""


def whats_new_context() -> dict:
    releases = db.session.scalars(
        select(ReleaseRecord)
        .where(ReleaseRecord.status == "deployed", ReleaseRecord.public.is_(True))
        .order_by(ReleaseRecord.deployed_at.desc(), ReleaseRecord.id.desc())
        .limit(6)
    ).all()
    ready = [row for row in releases if row.is_customer_ready()]
    roadmap = db.session.scalars(
        select(RoadmapItem)
        .where(RoadmapItem.public.is_(True), RoadmapItem.status == "approved")
        .order_by(RoadmapItem.sort_order, RoadmapItem.id)
        .limit(8)
    ).all()
    card_rows = db.session.scalars(
        select(WhatsNewCard).where(WhatsNewCard.slug.in_(WHATS_NEW_CARD_DEFAULTS))
    ).all()
    by_slug = {row.slug: row for row in card_rows}
    return {
        "recently_updated": ready,
        "roadmap": roadmap,
        "commercial_launch_window": _setting("commercial_launch_window"),
        "cards": {slug: _card_view(slug, by_slug.get(slug)) for slug in WHATS_NEW_CARD_DEFAULTS},
    }


@communications_bp.get("/api/suite/whats-new")
def whats_new_api():
    data = whats_new_context()
    return jsonify({
        "recently_updated": [{
            "version": row.version,
            "title": row.title,
            "summary": row.summary,
            "highlights": row.highlights,
            "deployed_at": row.deployed_at.isoformat() if row.deployed_at else None,
        } for row in data["recently_updated"]],
        "roadmap": [{"title": row.title, "summary": row.summary, "application": row.application} for row in data["roadmap"]],
        "commercial_launch_window": data["commercial_launch_window"],
        "cards": {
            slug: {
                "title": card["title"],
                "summary": card["summary"],
                "status": card["status"],
                "release_label": card["release_label"],
                "updated_at": card["updated_at"].isoformat() if card["updated_at"] else None,
                "public_ready": card["public_ready"],
            }
            for slug, card in data["cards"].items()
        },
    })


@communications_bp.route("/account/communications", methods=["GET", "POST"])
@login_required
def account_communications():
    pref = _preference(current_user.id, create=True)
    if request.method == "POST":
        pref.product_updates_enabled = bool(request.form.get("product_updates_enabled"))
        audit("communication_preferences_updated", user=current_user, actor=current_user,
              detail=f"product_updates_enabled={pref.product_updates_enabled}")
        db.session.commit()
        flash("Email preferences updated.", "success")
        return redirect(url_for("suite_communications.account_communications"))
    db.session.commit()
    return render_template("auth/communication_preferences.html", preference=pref)


@communications_bp.get("/admin/communications")
@admin_required
def admin_communications():
    releases = db.session.scalars(select(ReleaseRecord).order_by(ReleaseRecord.created_at.desc())).all()
    roadmap = db.session.scalars(select(RoadmapItem).order_by(RoadmapItem.sort_order, RoadmapItem.id)).all()
    stored_cards = db.session.scalars(select(WhatsNewCard)).all()
    cards_by_slug = {row.slug: row for row in stored_cards}
    cards = [{
        "slug": slug,
        "default_title": defaults[0],
        "row": cards_by_slug.get(slug),
    } for slug, defaults in WHATS_NEW_CARD_DEFAULTS.items()]
    return render_template(
        "auth/admin_communications.html",
        releases=releases,
        roadmap=roadmap,
        launch_window=_setting("commercial_launch_window"),
        cards=cards,
    )


@communications_bp.post("/admin/communications/whats-new/<slug>")
@admin_required
def save_whats_new_card(slug: str):
    if slug not in WHATS_NEW_CARD_DEFAULTS:
        return jsonify({"error": "Unknown What's New card."}), 404
    title = str(request.form.get("title") or "").strip()[:200]
    summary = str(request.form.get("summary") or "").strip()[:3000]
    release_label = str(request.form.get("release_label") or "").strip()[:80]
    requested_public = bool(request.form.get("public"))
    reviewed = bool(request.form.get("reviewed"))
    if requested_public and (not title or not summary or not release_label or not reviewed):
        flash("Public What's New cards require a title, summary, release label, and explicit content review.", "error")
        return redirect(url_for("suite_communications.admin_communications"))
    row = db.session.scalar(select(WhatsNewCard).where(WhatsNewCard.slug == slug))
    if not row:
        row = WhatsNewCard(slug=slug)
        db.session.add(row)
    row.title = title
    row.summary = summary
    row.release_label = release_label
    row.public = requested_public
    row.reviewed_at = (row.reviewed_at or _utcnow()) if reviewed else None
    row.status = "approved" if reviewed else "draft"
    row.updated_by_user_id = current_user.id
    audit("whats_new_card_updated", actor=current_user,
          detail=f"slug={slug}; status={row.status}; public={row.public}")
    db.session.commit()
    flash(f"What's New card '{title or WHATS_NEW_CARD_DEFAULTS[slug][0]}' saved.", "success")
    return redirect(url_for("suite_communications.admin_communications"))


@communications_bp.post("/admin/communications/releases")
@admin_required
def save_release():
    release_id = int(request.form.get("release_id") or 0)
    row = db.session.get(ReleaseRecord, release_id) if release_id else None
    if not row:
        version = str(request.form.get("version") or "").strip()[:80]
        if not version:
            flash("Release version is required.", "error")
            return redirect(url_for("suite_communications.admin_communications"))
        row = ReleaseRecord(version=version, title="Release", created_by_user_id=current_user.id)
        db.session.add(row)
    row.title = str(request.form.get("title") or row.title or "Release").strip()[:200]
    row.summary = str(request.form.get("summary") or "").strip()[:5000]
    highlights = [line.strip(" -•\t") for line in str(request.form.get("highlights") or "").splitlines() if line.strip()]
    email_approved = bool(request.form.get("update_email_approved"))
    if highlights and not (3 <= len(highlights) <= 6):
        flash("Release highlights must contain 3–6 plain-language improvements when provided.", "error")
        return redirect(url_for("suite_communications.admin_communications"))
    if email_approved and not (3 <= len(highlights) <= 6):
        flash("Product-update email approval requires 3–6 plain-language improvements.", "error")
        return redirect(url_for("suite_communications.admin_communications"))
    row.highlights_json = json.dumps(highlights[:6], ensure_ascii=False)
    row.applications_json = json.dumps([x.strip() for x in str(request.form.get("applications") or "").split(",") if x.strip()])
    row.deployment_sha = str(request.form.get("deployment_sha") or "").strip()[:80]
    row.public = bool(request.form.get("public"))
    row.update_email_approved = email_approved
    now = _utcnow()
    row.validated_at = (row.validated_at or now) if request.form.get("validated") else None
    row.deployed_at = (row.deployed_at or now) if request.form.get("deployed") else None
    row.health_verified_at = (row.health_verified_at or now) if request.form.get("healthy") else None
    row.status = "deployed" if row.deployed_at else "approved" if row.validated_at else "draft"
    audit("release_record_updated", actor=current_user, detail=f"version={row.version}; status={row.status}; public={row.public}")
    db.session.commit()
    flash(f"Release {row.version} saved.", "success")
    return redirect(url_for("suite_communications.admin_communications"))


@communications_bp.post("/admin/communications/roadmap")
@admin_required
def save_roadmap_item():
    title = str(request.form.get("title") or "").strip()[:200]
    summary = str(request.form.get("summary") or "").strip()[:3000]
    if not title or not summary:
        flash("Roadmap title and customer-facing summary are required.", "error")
        return redirect(url_for("suite_communications.admin_communications"))
    row = RoadmapItem(
        title=title,
        summary=summary,
        application=str(request.form.get("application") or "suite")[:64],
        status="approved",
        public=bool(request.form.get("public")),
        sort_order=int(request.form.get("sort_order") or 100),
        created_by_user_id=current_user.id,
    )
    db.session.add(row)
    audit("roadmap_item_created", actor=current_user, detail=f"title={title}; public={row.public}")
    db.session.commit()
    return redirect(url_for("suite_communications.admin_communications"))


@communications_bp.post("/admin/communications/launch-window")
@admin_required
def save_launch_window():
    value = str(request.form.get("commercial_launch_window") or "").strip()[:200]
    row = db.session.scalar(select(SuiteSetting).where(SuiteSetting.key == "commercial_launch_window"))
    if not row:
        row = SuiteSetting(key="commercial_launch_window")
        db.session.add(row)
    row.value = value
    row.updated_by_user_id = current_user.id
    audit("commercial_launch_window_updated", actor=current_user, detail=f"value={value}")
    db.session.commit()
    flash("Commercial launch window updated.", "success")
    return redirect(url_for("suite_communications.admin_communications"))


def _release_email(user: User, release: ReleaseRecord) -> tuple[str, str]:
    greeting = first_name(user.full_name)
    bullets = "\n".join(f"- {item}" for item in release.highlights)
    body = f"""Hello {greeting},

Thank you for using Total Water Design Suite and for being part of the community helping us improve it.

What's new in {release.version}:
{bullets}

{release.summary}

We appreciate the feedback and practical experience users share with us. It helps us prioritize improvements that make the Suite more useful for engineering work.

You can manage product-update email preferences from My Account.

Total Water Design Suite
admin@totalrodesign.com
"""
    return f"What's new in Total Water Design Suite {release.version}", body


@communications_bp.post("/admin/communications/releases/<int:release_id>/send-update")
@admin_required
def send_release_update(release_id: int):
    release = db.get_or_404(ReleaseRecord, release_id)
    if not release.is_customer_ready() or not release.update_email_approved:
        flash("Release email is blocked until the release is validated, deployed, health-verified, and explicitly approved for email.", "error")
        return redirect(url_for("suite_communications.admin_communications"))
    if not (3 <= len(release.highlights) <= 6):
        flash("Release email is blocked until 3–6 approved plain-language improvements are recorded.", "error")
        return redirect(url_for("suite_communications.admin_communications"))
    if release.announcement_sent_at:
        flash("This release already has an announcement-sent timestamp. Create a corrected release record rather than sending it again blindly.", "warning")
        return redirect(url_for("suite_communications.admin_communications"))
    prefs = db.session.execute(
        select(User, CommunicationPreference)
        .join(CommunicationPreference, CommunicationPreference.user_id == User.id)
        .where(User.status == "active", CommunicationPreference.product_updates_enabled.is_(True))
    ).all()
    sent = 0
    failed = 0
    for user, _pref in prefs:
        subject, body = _release_email(user, release)
        result = send_transactional_email(
            user_id=user.id,
            recipient=user.email,
            event_type="product_update",
            subject=subject,
            body=body,
            template="product_update_v1",
        )
        sent += int(result.sent)
        failed += int(not result.sent)
    if sent and failed == 0:
        release.announcement_sent_at = _utcnow()
    audit("release_update_email_attempted", actor=current_user,
          detail=f"version={release.version}; recipients={len(prefs)}; sent={sent}; failed={failed}")
    db.session.commit()
    flash(f"Product update processed: {sent} sent, {failed} failed, {len(prefs)} opted-in recipients.", "success" if failed == 0 else "warning")
    return redirect(url_for("suite_communications.admin_communications"))


def init_suite_communications(app) -> None:
    if "suite_communications" in app.blueprints:
        return
    with app.app_context():
        db.create_all()
    app.register_blueprint(communications_bp)

    @app.context_processor
    def _communications_context():
        try:
            return {"twds_whats_new": whats_new_context()}
        except Exception:
            return {"twds_whats_new": {
                "recently_updated": [], "roadmap": [], "commercial_launch_window": "",
                "cards": {slug: _card_view(slug, None) for slug in WHATS_NEW_CARD_DEFAULTS},
            }}
