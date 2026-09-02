"""Authentication, account approval, and suite-product entitlement integration.

The desktop build can continue to run without authentication. The AWS/server
entry point enables authentication by default and refuses to start without a
strong secret key. User passwords are stored only as Werkzeug scrypt hashes.
The existing Total RO Design licensed_tier column is preserved as a compatibility
mirror of the RO entitlement while the suite adds product-specific entitlements.
"""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit
import getpass
import hashlib
import json
import os
import re
import secrets
import smtplib
import threading
import time
import uuid

import click
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import UniqueConstraint, event, func, select, inspect, text
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

from entitlements import normalize_tier, TIER_ORDER
from suite_catalog import PRODUCTS, PRODUCT_BY_ID, SUITE_NAME, product_catalog
from countries import COUNTRIES, normalize_country_code, country_name


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _normalise_email(value: object) -> str:
    return str(value or "").strip().lower()


def _valid_email(value: str) -> bool:
    # Deliberately conservative without requiring a network/DNS lookup.
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value or ""))


def _safe_next(value: object) -> str | None:
    target = str(value or "").strip()
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


MOBILE_CONTRACT = "twds.mobile.auth/v1"
MOBILE_ROUTES = {"mfa", "device_sessions", "privacy", "project", "job", "report"}


def _mobile_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mobile_time(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _mobile_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _mobile_error(code: str, status: int, message: str = ""):
    response = jsonify({"contract": MOBILE_CONTRACT, "code": code, "retryable": False,
                        "request_id": uuid.uuid4().hex, **({"message": message} if message else {})})
    response.status_code = status
    response.headers["Cache-Control"] = "no-store"
    return response


def _mobile_contract_error():
    requested = request.headers.get("Accept-Contract", MOBILE_CONTRACT)
    if requested != MOBILE_CONTRACT:
        return _mobile_error("VERSION_UNSUPPORTED", 406)
    return None


def _mobile_bearer_session() -> MobileDeviceSession | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header[7:].strip()
    if not token:
        return None
    row = db.session.scalar(select(MobileDeviceSession).where(MobileDeviceSession.access_hash == _mobile_hash(token)))
    now = _utcnow()
    if not row or row.state != "active" or _mobile_utc(row.expires_at) <= now or _mobile_utc(row.access_expires_at) <= now:
        return None
    return row


def _mobile_session_payload(row: MobileDeviceSession, *, current: bool = False) -> dict:
    result = {"contract": MOBILE_CONTRACT, "session_id": row.id, "device_id": row.device_id,
              "owner": {"tenant_id": "twds", "user_id": str(row.user_id)},
              "created_at": _mobile_time(row.created_at), "last_seen_at": _mobile_time(row.last_seen_at),
              "expires_at": _mobile_time(row.expires_at), "state": row.state,
              "refresh_generation": row.refresh_generation,
              "display": {"device_name": row.device_name, "platform": row.platform, "is_current": current}}
    if row.revoked_at:
        result["revoked_at"] = _mobile_time(row.revoked_at)
    return result


def _issue_mobile_tokens(row: MobileDeviceSession) -> dict:
    access = secrets.token_urlsafe(32)
    refresh = secrets.token_urlsafe(48)
    now = _utcnow()
    row.access_hash = _mobile_hash(access)
    row.refresh_hash = _mobile_hash(refresh)
    row.access_expires_at = now + timedelta(minutes=int(current_app.config.get("MOBILE_ACCESS_MINUTES", 15)))
    row.expires_at = now + timedelta(days=int(current_app.config.get("MOBILE_REFRESH_DAYS", 30)))
    row.last_seen_at = now
    return {"token_type": "Bearer", "access_token": access, "refresh_token": refresh,
            "expires_in": int((row.access_expires_at - now).total_seconds()), "session_id": row.id,
            "refresh_generation": row.refresh_generation}


def validate_password(password: str, email: str = "") -> list[str]:
    errors: list[str] = []
    if len(password or "") < 12:
        errors.append("Use at least 12 characters.")
    if len(password or "") > 256:
        errors.append("Password is too long.")
    local = _normalise_email(email).split("@", 1)[0]
    if local and len(local) >= 4 and local in (password or "").lower():
        errors.append("Do not include your email name in the password.")
    if (password or "").lower() in {
        "password1234", "totalrodesign", "totalrodesign123", "changeme1234",
    }:
        errors.append("Choose a less predictable password.")
    return errors


class Base:
    """Marker used by Flask-SQLAlchemy's generated declarative base."""


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
auth_bp = Blueprint("auth", __name__)


# The authenticated Alpha uses one Gunicorn process.  This small in-process
# limiter protects login, registration and password-reset forms from simple
# automated abuse without introducing another service.  A shared limiter
# (Redis/proxy/WAF) should replace it before horizontal scaling.
_rate_lock = threading.RLock()
_rate_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def _request_ip() -> str:
    return str(request.remote_addr or "unknown")[:64]


def _rate_limited(bucket: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    now = time.monotonic()
    key = (str(bucket), _request_ip())
    cutoff = now - max(1, int(window_seconds))
    with _rate_lock:
        hits = _rate_hits[key]
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= max(1, int(limit)):
            retry_after = max(1, int(window_seconds - (now - hits[0])))
            return True, retry_after
        hits.append(now)
    return False, 0


def _form_rate_limit(bucket: str, limit: int, window_seconds: int):
    limited, retry_after = _rate_limited(bucket, limit, window_seconds)
    if limited:
        response = render_template(
            "auth/rate_limited.html",
            retry_after=retry_after,
        )
        return response, 429, {"Retry-After": str(retry_after)}
    return None


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(160), nullable=False)
    organization = db.Column(db.String(200), nullable=False, default="")
    country_code = db.Column(db.String(2), nullable=True, index=True)
    country_name = db.Column(db.String(100), nullable=False, default="")
    password_hash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user", index=True)
    licensed_tier = db.Column(db.String(20), nullable=False, default="entry", index=True)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    password_changed_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    password_version = db.Column(db.Integer, nullable=False, default=1)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    terms_accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    @property
    def is_active(self) -> bool:  # Flask-Login contract
        return self.status == "active"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def get_id(self) -> str:
        # Include the password version in Flask-Login's signed session identity.
        # Changing a password therefore invalidates existing sessions and
        # remember-me cookies without storing server-side session secrets.
        return f"{self.id}:{int(self.password_version or 0)}"

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="scrypt")
        self.password_changed_at = _utcnow()
        self.password_version = int(self.password_version or 0) + 1

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        locked = self.locked_until
        if not locked:
            return False
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        return locked > _utcnow()


class MobileDeviceSession(db.Model):
    """Opaque, server-side mobile credentials.  Raw tokens are never persisted."""

    __tablename__ = "mobile_device_sessions"
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    device_id = db.Column(db.String(128), nullable=False, index=True)
    device_name = db.Column(db.String(128), nullable=False, default="")
    platform = db.Column(db.String(16), nullable=False, default="unknown")
    access_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    access_expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    refresh_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    refresh_generation = db.Column(db.Integer, nullable=False, default=0)
    state = db.Column(db.String(16), nullable=False, default="active", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)


class MobilePushToken(db.Model):
    __tablename__ = "mobile_push_tokens"
    id = db.Column(db.String(64), primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey("mobile_device_sessions.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    provider = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    rotated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)


class ProductEntitlement(db.Model):
    """Per-user product access and tier assignment.

    The table is additive and backward compatible: the legacy users.licensed_tier
    column remains the RO tier mirror so existing deployments and project code
    continue to work during the suite migration.
    """

    __tablename__ = "product_entitlements"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_user_product_entitlement"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.String(48), nullable=False, index=True)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    tier = db.Column(db.String(20), nullable=False, default="entry")
    status = db.Column(db.String(24), nullable=False, default="active")
    starts_at = db.Column(db.DateTime(timezone=True), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    def is_current(self, at: datetime | None = None) -> bool:
        at = at or _utcnow()
        start = self.starts_at
        end = self.expires_at
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return self.status == "active" and (not start or start <= at) and (not end or end > at)


def ensure_default_entitlements(user: User, *, flush: bool = False) -> dict[str, ProductEntitlement]:
    """Create missing suite entitlements without changing existing assignments."""
    if user.id is None:
        if flush:
            db.session.flush()
        else:
            raise ValueError("User must be persisted before entitlements are created.")
    existing = {row.product_id: row for row in db.session.scalars(
        select(ProductEntitlement).where(ProductEntitlement.user_id == user.id)
    ).all()}
    for product in PRODUCTS:
        if product.product_id in existing:
            continue
        is_ro = product.product_id == "ro"
        row = ProductEntitlement(
            user_id=user.id,
            product_id=product.product_id,
            enabled=is_ro,
            tier=normalize_tier(user.licensed_tier, "entry") if is_ro else "entry",
            status="active",
        )
        db.session.add(row)
        existing[product.product_id] = row
    if flush:
        db.session.flush()
    return existing


def product_entitlements_for(user: User) -> dict[str, ProductEntitlement]:
    if not user or user.id is None:
        return {}
    rows = ensure_default_entitlements(user)
    return rows


def product_entitlement_for(user: User, product_id: str) -> ProductEntitlement | None:
    return product_entitlements_for(user).get(str(product_id or "").strip().lower())


def user_can_access_product(user: User, product_id: str) -> bool:
    product = PRODUCT_BY_ID.get(str(product_id or "").strip().lower())
    if not user or not product or user.status != "active":
        return False

    # Administrator-preview metadata is the catalog's single readiness gate.
    # It permits active administrators to test the application without
    # presenting it as generally released.
    if getattr(user, "is_admin", False) and product.admin_preview_enabled:
        return True

    # An active, current entitlement may launch a generally available product
    # or a product explicitly approved for controlled Alpha testing. Products
    # without either catalog gate remain unavailable even if a stale or
    # mistakenly assigned entitlement row exists.
    if product.status != "available" and not product.admin_preview_enabled:
        return False

    entitlement = product_entitlement_for(user, product.product_id)
    return bool(entitlement and entitlement.enabled and entitlement.is_current())


def serialized_product_entitlements(user: User) -> list[dict]:
    rows = product_entitlements_for(user)
    output: list[dict] = []
    for product in PRODUCTS:
        row = rows.get(product.product_id)
        accessible = bool(
            user.status == "active"
            and (
                (getattr(user, "is_admin", False) and product.admin_preview_enabled)
                or (
                    (product.status == "available" or product.admin_preview_enabled)
                    and row
                    and row.enabled
                    and row.is_current()
                )
            )
        )
        output.append({
            **product.as_dict(),
            "entitlement": {
                "enabled": bool(row.enabled) if row else False,
                "tier": normalize_tier(row.tier, "entry") if row else "entry",
                "status": row.status if row else "inactive",
                "starts_at": row.starts_at.isoformat() if row and row.starts_at else None,
                "expires_at": row.expires_at.isoformat() if row and row.expires_at else None,
                "current": bool(row and row.is_current()),
            },
            "accessible": accessible,
        })
    return output


class AccountAudit(db.Model):
    __tablename__ = "account_audit"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    detail = db.Column(db.Text, nullable=False, default="")
    ip_address = db.Column(db.String(64), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)


class LoginAddress(db.Model):
    """Successful-login IP history visible only to suite administrators."""

    __tablename__ = "login_addresses"
    __table_args__ = (UniqueConstraint("user_id", "ip_address", name="uq_login_address_user_ip"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=False, index=True)
    first_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    login_count = db.Column(db.Integer, nullable=False, default=1)
    last_user_agent = db.Column(db.String(500), nullable=False, default="")


class TelemetrySession(db.Model):
    """Privacy-minimized authenticated session history for administrator analytics."""
    __tablename__ = "telemetry_sessions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_key = db.Column(db.String(64), nullable=False, unique=True, index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    ended_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    request_count = db.Column(db.Integer, nullable=False, default=0)


class TelemetryEvent(db.Model):
    """Usage/resource metadata only; customer engineering inputs are deliberately excluded."""
    __tablename__ = "telemetry_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    application = db.Column(db.String(48), nullable=False, default="suite", index=True)
    module = db.Column(db.String(80), nullable=False, default="", index=True)
    success = db.Column(db.Boolean, nullable=False, default=True, index=True)
    duration_ms = db.Column(db.Float, nullable=True)
    cpu_seconds = db.Column(db.Float, nullable=True)
    metadata_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)


class ResourceSample(db.Model):
    __tablename__ = "resource_samples"
    id = db.Column(db.Integer, primary_key=True)
    cpu_percent = db.Column(db.Float, nullable=True)
    memory_percent = db.Column(db.Float, nullable=True)
    process_memory_mb = db.Column(db.Float, nullable=True)
    database_bytes = db.Column(db.BigInteger, nullable=True)
    project_bytes = db.Column(db.BigInteger, nullable=True)
    active_sessions = db.Column(db.Integer, nullable=True)
    sampled_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)


class EmailNotification(db.Model):
    __tablename__ = "email_notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    recipient = db.Column(db.String(254), nullable=False, index=True)
    template = db.Column(db.String(80), nullable=False)
    subject = db.Column(db.String(240), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(24), nullable=False, default="queued", index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    last_error = db.Column(db.Text, nullable=False, default="")
    queued_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class ProjectFamily(db.Model):
    """Suite-wide project family shared by product-specific revisions."""

    __tablename__ = "project_families"

    id = db.Column(db.Integer, primary_key=True)
    family_uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    base_number = db.Column(db.Integer, unique=True, nullable=False, index=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_country_code = db.Column(db.String(2), nullable=True, index=True)
    project_country_name = db.Column(db.String(100), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class ProjectRevision(db.Model):
    """One immutable identity/revision row containing the latest saved snapshot for that revision."""

    __tablename__ = "project_revisions"
    __table_args__ = (
        UniqueConstraint("family_id", "product_id", "revision", name="uq_project_family_product_revision"),
        UniqueConstraint("visible_id", name="uq_project_visible_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey("project_families.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.String(48), nullable=False, default="ro", index=True)
    revision = db.Column(db.Integer, nullable=False, default=0, index=True)
    visible_id = db.Column(db.String(80), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, default="Total RO Design Project", index=True)
    snapshot_json = db.Column(db.Text, nullable=False)
    snapshot_bytes = db.Column(db.Integer, nullable=False, default=0)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    source_revision_id = db.Column(db.Integer, db.ForeignKey("project_revisions.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, index=True)


PROJECT_PREFIXES = {"pretreatment":"TPRE", "bio":"TBIO", "ro":"TROD", "zld":"TZLD", "balance":"TWBAL", "economics":"TWECO", "system_integration":"TWSYS"}


def _project_visible_base(visible_id: object) -> int | None:
    parts = str(visible_id or "").strip().rsplit("-", 2)
    if len(parts) != 3:
        return None
    try:
        return int(parts[1])
    except (TypeError, ValueError):
        return None


def _next_product_project_number(product_id: str) -> int:
    product_id = str(product_id or "").strip().lower()
    prefix = PROJECT_PREFIXES.get(product_id)
    if not prefix:
        raise ValueError(f"Unsupported Suite application: {product_id}")
    ids = db.session.scalars(select(ProjectRevision.visible_id).where(ProjectRevision.product_id == product_id)).all()
    used = {n for n in (_project_visible_base(v) for v in ids) if n is not None and n > 0}
    candidate = max(used, default=0) + 1
    while db.session.scalar(select(ProjectRevision.id).where(ProjectRevision.visible_id == f"{prefix}-{candidate}-0")):
        candidate += 1
    return candidate


def _product_visible_id(product_id: str, product_number: int, revision: int = 0) -> str:
    prefix = PROJECT_PREFIXES.get(str(product_id or "").strip().lower())
    if not prefix:
        raise ValueError(f"Unsupported Suite application: {product_id}")
    return f"{prefix}-{int(product_number)}-{int(revision)}"


def record_telemetry(event_type: str, *, application: str = "suite", module: str = "", success: bool = True,
                     duration_ms: float | None = None, cpu_seconds: float | None = None, metadata: dict | None = None,
                     user: User | None = None) -> None:
    """Queue lightweight usage metadata in the current DB transaction."""
    try:
        uid = getattr(user or current_user, "id", None) if (user is not None or current_user.is_authenticated) else None
    except RuntimeError:
        uid = getattr(user, "id", None)
    safe_meta = dict(metadata or {})
    # Never accept arbitrary project/calculation payloads into telemetry.
    allowed = {k: safe_meta[k] for k in safe_meta if k in {"tier","product_id","status","http_status","solver","iterations","reason","count"}}
    db.session.add(TelemetryEvent(
        user_id=uid, event_type=str(event_type)[:64], application=str(application)[:48], module=str(module)[:80],
        success=bool(success), duration_ms=None if duration_ms is None else float(duration_ms),
        cpu_seconds=None if cpu_seconds is None else float(cpu_seconds),
        metadata_json=json.dumps(allowed, separators=(",",":"), default=str)[:4000],
    ))


def _current_telemetry_session(user: User | None = None) -> TelemetrySession | None:
    user = user or (current_user if current_user.is_authenticated else None)
    if not user:
        return None
    key = str(session.get("telemetry_session_key") or "")
    if not key:
        key = secrets.token_hex(24)
        session["telemetry_session_key"] = key
    row = db.session.scalar(select(TelemetrySession).where(TelemetrySession.session_key == key))
    now = _utcnow()
    if not row:
        row = TelemetrySession(user_id=user.id, session_key=key, started_at=now, last_seen_at=now, request_count=0)
        db.session.add(row)
    row.last_seen_at = now
    row.request_count = int(row.request_count or 0) + 1
    return row


def _queue_email_notification(user: User, event_type: str, subject: str, body: str, template: str) -> EmailNotification:
    row = EmailNotification(user_id=user.id, event_type=event_type, recipient=user.email, template=template,
                            subject=subject[:240], body=body, status="queued")
    db.session.add(row)
    return row


def _deliver_notification(notification_id: int) -> None:
    """Best-effort asynchronous delivery using a fresh app/DB context."""
    app = current_app._get_current_object()
    def worker():
        with app.app_context():
            row = db.session.get(EmailNotification, int(notification_id))
            if not row or row.status == "sent":
                return
            row.attempts = int(row.attempts or 0) + 1
            try:
                sent, detail = send_email(row.subject, [row.recipient], row.body)
                if sent:
                    row.status = "sent"; row.sent_at = _utcnow(); row.last_error = ""
                else:
                    row.status = "retry"; row.last_error = str(detail)[:2000]
            except Exception as exc:  # pragma: no cover - external delivery
                row.status = "retry"; row.last_error = str(exc)[:2000]
            db.session.commit()
    threading.Thread(target=worker, name=f"twds-mail-{notification_id}", daemon=True).start()


def _access_email_content(user: User, event_type: str, *, changes: list[str] | None = None) -> tuple[str,str,str]:
    founder_name = current_app.config.get("FOUNDER_NAME", "Jerry Ross-Sisniega")
    founder_title = current_app.config.get("FOUNDER_TITLE", "CEO and Founder")
    founder_email = current_app.config.get("FOUNDER_EMAIL", "admin@totalrodesign.com")
    rows = serialized_product_entitlements(user)
    active = [f"{x['name']} ({x['entitlement']['tier'].title()})" for x in rows if x['entitlement']['enabled']]
    first = (user.full_name or "there").strip().split()[0]
    if event_type == "account_activated":
        subject = "Welcome to Total Water Design Suite"
        intro = "Your access to Total Water Design Suite has now been activated."
        template = "account_activated_v1"
    else:
        subject = "Your Total Water Design Suite Access Has Been Expanded"
        intro = "Your Total Water Design Suite access has been updated."
        template = "access_expanded_v1"
    change_text = "\n".join(f"- {x}" for x in (changes or active)) or "- Your current Suite access is available from My Applications."
    body = f"""Dear {first},\n\n{intro}\n\nThank you for using our software and for placing your trust in the platform. We are committed to continuing to improve the Suite so it becomes an increasingly useful and practical engineering environment for your work.\n\nYou now have access to:\n{change_text}\n\nWe greatly value feedback from our users. If you have suggestions, identify areas that could be improved, or would simply like to discuss how you are using the software, please feel free to reach out directly to our founder.\n\nThank you again for being part of Total Water Design Suite.\n\nKind regards,\n\nTotal Water Design Suite Team\n\n{founder_name}\n{founder_title}\n{founder_email}\n"""
    return subject, body, template


def _ensure_schema_additions() -> None:
    """Small additive migration layer for installations that predate v0.25."""
    engine = db.engine
    inspector = inspect(engine)
    # db.create_all() creates new tables but cannot add columns to existing tables.
    additions = {
        "users": [("country_code", "VARCHAR(2)"), ("country_name", "VARCHAR(100) NOT NULL DEFAULT ''")],
        "project_families": [("project_country_code", "VARCHAR(2)"), ("project_country_name", "VARCHAR(100) NOT NULL DEFAULT ''")],
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            existing = {c["name"] for c in inspector.get_columns(table)} if inspector.has_table(table) else set()
            for name, ddl in columns:
                if name not in existing:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, _connection_record):  # pragma: no cover - backend-specific
    module = dbapi_connection.__class__.__module__
    if not module.startswith("sqlite3"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def audit(action: str, *, user: User | None = None, actor: User | None = None, detail: str = "") -> None:
    try:
        row = AccountAudit(
            user_id=getattr(user, "id", None),
            actor_user_id=getattr(actor, "id", None),
            action=str(action)[:80],
            detail=str(detail)[:4000],
            ip_address=str(request.remote_addr or "")[:64] if request else "",
        )
        db.session.add(row)
    except RuntimeError:
        # CLI/bootstrap paths can run without a request context.
        row = AccountAudit(
            user_id=getattr(user, "id", None),
            actor_user_id=getattr(actor, "id", None),
            action=str(action)[:80],
            detail=str(detail)[:4000],
            ip_address="",
        )
        db.session.add(row)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _record_login_address(user: User) -> None:
    ip = _request_ip()
    if not ip or ip == "unknown":
        return
    now = _utcnow()
    row = db.session.scalar(
        select(LoginAddress).where(LoginAddress.user_id == user.id, LoginAddress.ip_address == ip)
    )
    if row:
        row.last_seen_at = now
        row.login_count = int(row.login_count or 0) + 1
        row.last_user_agent = str(request.headers.get("User-Agent") or "")[:500]
    else:
        db.session.add(LoginAddress(
            user_id=user.id,
            ip_address=ip[:64],
            first_seen_at=now,
            last_seen_at=now,
            login_count=1,
            last_user_agent=str(request.headers.get("User-Agent") or "")[:500],
        ))


def _backfill_login_addresses() -> None:
    """Populate/refresh IP history from existing successful-login audit rows."""
    aggregates = db.session.execute(
        select(
            AccountAudit.user_id,
            AccountAudit.ip_address,
            func.count(AccountAudit.id),
            func.min(AccountAudit.created_at),
            func.max(AccountAudit.created_at),
        ).where(
            AccountAudit.action == "login_success",
            AccountAudit.user_id.is_not(None),
            AccountAudit.ip_address != "",
        ).group_by(AccountAudit.user_id, AccountAudit.ip_address)
    ).all()
    for user_id, ip, count, first_seen, last_seen in aggregates:
        row = db.session.scalar(
            select(LoginAddress).where(LoginAddress.user_id == user_id, LoginAddress.ip_address == ip)
        )
        if not row:
            row = LoginAddress(user_id=user_id, ip_address=str(ip)[:64])
            db.session.add(row)
        row.login_count = int(count or 0)
        row.first_seen_at = first_seen or row.first_seen_at or _utcnow()
        row.last_seen_at = last_seen or row.last_seen_at or _utcnow()


def _project_snapshot_payload(value: object) -> tuple[dict, str, int]:
    if not isinstance(value, dict):
        raise ValueError("A project snapshot object is required.")
    supported = {"Total RO Design Project", "CalcOsPower Project", "Total Bio Design Project", "Total ZLD Design Project"}
    if str(value.get("format") or "") not in supported:
        raise ValueError("Unsupported Total Water Design Suite project format.")
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    size = len(encoded.encode("utf-8"))
    max_bytes = int(os.getenv("TOTALRO_PROJECT_MAX_BYTES", str(8 * 1024 * 1024)) or (8 * 1024 * 1024))
    if size > max_bytes:
        raise ValueError(f"Project snapshot exceeds the {max_bytes // (1024 * 1024)} MB server limit.")
    project_meta = value.get("project") if isinstance(value.get("project"), dict) else {}
    name = str(project_meta.get("project_name") or "Total RO Design Project").strip()[:200] or "Total RO Design Project"
    return value, encoded, size


def _project_meta(row: ProjectRevision, family: ProjectFamily) -> dict:
    return {
        "id": row.id,
        "family_uuid": family.family_uuid,
        "base_number": family.base_number,
        "project_country_code": family.project_country_code or "",
        "project_country_name": family.project_country_name or "",
        "product_id": row.product_id,
        "revision": row.revision,
        "visible_id": row.visible_id,
        "name": row.name,
        "snapshot_bytes": row.snapshot_bytes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _project_owner_row(revision_id: int) -> tuple[ProjectRevision, ProjectFamily] | tuple[None, None]:
    row = db.session.get(ProjectRevision, revision_id)
    if not row:
        return None, None
    family = db.session.get(ProjectFamily, row.family_id)
    if not family:
        return None, None
    return row, family


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="totalro-password-reset-v1")


def make_password_reset_token(user: User) -> str:
    return _serializer().dumps({"uid": user.id, "ver": int(user.password_version or 0)})


def resolve_password_reset_token(token: str) -> User | None:
    try:
        payload = _serializer().loads(
            token,
            max_age=int(current_app.config.get("PASSWORD_RESET_MAX_AGE", 3600)),
        )
    except (BadSignature, SignatureExpired):
        return None
    user = db.session.get(User, int(payload.get("uid", 0) or 0))
    if not user or int(payload.get("ver", -1)) != int(user.password_version or 0):
        return None
    return user


def _mail_outbox() -> Path:
    configured = os.getenv("TOTALRO_AUTH_MAIL_OUTBOX")
    root = Path(configured).expanduser() if configured else Path(current_app.instance_path) / "mail_outbox"
    root.mkdir(parents=True, exist_ok=True)
    return root


def send_email(subject: str, recipients: list[str], body: str) -> tuple[bool, str]:
    recipients = [_normalise_email(x) for x in recipients if _valid_email(_normalise_email(x))]
    if not recipients:
        return False, "No valid recipient."
    sender = (
        os.getenv("TOTALRO_SMTP_FROM")
        or os.getenv("TOTALRO_SMTP_USER")
        or os.getenv("TOTALRO_ADMIN_EMAIL")
        or "admin@totalrodesign.com"
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(body)

    host = os.getenv("TOTALRO_SMTP_HOST", "").strip()
    if not host:
        filename = f"{_utcnow().strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(4)}.eml"
        path = _mail_outbox() / filename
        path.write_bytes(message.as_bytes())
        current_app.logger.warning("Authentication email saved to protected outbox because SMTP is not configured: %s", path)
        return False, "Email delivery is not configured. The message was saved to the protected server outbox for administrator retrieval."

    port = int(os.getenv("TOTALRO_SMTP_PORT", "587") or 587)
    username = os.getenv("TOTALRO_SMTP_USER", "")
    password = os.getenv("TOTALRO_SMTP_PASSWORD", "")
    use_ssl = _bool_env("TOTALRO_SMTP_SSL", port == 465)
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                if _bool_env("TOTALRO_SMTP_STARTTLS", True):
                    smtp.starttls()
                    smtp.ehlo()
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        return True, "sent"
    except Exception as exc:  # pragma: no cover - external SMTP
        filename = f"{_utcnow().strftime('%Y%m%dT%H%M%SZ')}_{secrets.token_hex(4)}.eml"
        path = _mail_outbox() / filename
        path.write_bytes(message.as_bytes())
        current_app.logger.exception("Authentication email delivery failed; message saved to protected outbox: %s", path)
        return False, "Email delivery failed. The message was saved to the protected server outbox for administrator retrieval."


def send_reset_email(user: User) -> tuple[bool, str]:
    token = make_password_reset_token(user)
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    body = f"""Hello {user.full_name},

A password reset was requested for your Total Water Design Suite account.

Use this link within {int(current_app.config.get('PASSWORD_RESET_MAX_AGE', 3600)) // 60} minutes:
{reset_url}

If you did not request this, no action is required. The link becomes invalid after a successful password change.

Total Water Design Suite
support@totalrodesign.com
"""
    return send_email("Reset your Total Water Design Suite password", [user.email], body)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    try:
        raw_id, raw_version = str(user_id).split(":", 1)
        user = db.session.get(User, int(raw_id))
        if not user or int(raw_version) != int(user.password_version or 0):
            return None
        return user
    except (TypeError, ValueError):
        return None


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({
            "error": "Authentication required.",
            "error_type": "AuthenticationRequired",
            "login_url": url_for("auth.login"),
        }), 401
    return redirect(url_for("auth.login", next=request.full_path if request.method == "GET" else None))


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return unauthorized()
        if getattr(current_user, "status", None) != "active":
            logout_user()
            session.clear()
            return unauthorized()
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return view(*args, **kwargs)
    return wrapped


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if not current_app.config.get("AUTH_ENABLED", False):
        return redirect(url_for("suite_dashboard"))
    if current_user.is_authenticated:
        return redirect(url_for("suite_dashboard"))

    next_url = _safe_next(request.args.get("next") or request.form.get("next"))
    if request.method == "POST":
        limited = _form_rate_limit(
            "login",
            int(current_app.config.get("LOGIN_IP_LIMIT", 20)),
            int(current_app.config.get("LOGIN_IP_WINDOW_SECONDS", 900)),
        )
        if limited:
            return limited
        email = _normalise_email(request.form.get("email"))
        password = str(request.form.get("password") or "")
        remember = bool(request.form.get("remember"))
        user = db.session.scalar(select(User).where(func.lower(User.email) == email))

        # Use a dummy scrypt hash for unknown users so timing is less revealing.
        dummy = current_app.config.get("_DUMMY_PASSWORD_HASH")
        if not dummy:
            dummy = generate_password_hash(secrets.token_urlsafe(24), method="scrypt")
            current_app.config["_DUMMY_PASSWORD_HASH"] = dummy
        valid_password = user.check_password(password) if user else check_password_hash(dummy, password)

        if user and user.is_locked():
            flash("Too many failed attempts. Try again later or reset your password.", "error")
        elif user and valid_password and user.status == "active":
            session.clear()
            login_user(user, remember=remember, fresh=True)
            session.permanent = True
            user.failed_login_count = 0
            user.locked_until = None
            user.last_login_at = _utcnow()
            audit("login_success", user=user, actor=user)
            _record_login_address(user)
            db.session.commit()
            if user.terms_accepted_at is None:
                return redirect(url_for("auth.accept_terms", next=next_url or url_for("suite_dashboard")))
            return redirect(next_url or url_for("suite_dashboard"))
        elif user and valid_password and user.status == "pending":
            flash("Your account request is awaiting administrator approval.", "warning")
        elif user and valid_password and user.status in {"disabled", "suspended", "canceled", "rejected"}:
            flash("This account is not currently enabled. Contact support@totalrodesign.com.", "error")
        else:
            if user:
                user.failed_login_count = int(user.failed_login_count or 0) + 1
                if user.failed_login_count >= int(current_app.config.get("LOGIN_FAILURE_LIMIT", 5)):
                    user.locked_until = _utcnow() + timedelta(
                        minutes=int(current_app.config.get("LOGIN_LOCK_MINUTES", 15))
                    )
                    user.failed_login_count = 0
                audit("login_failed", user=user, detail="Invalid password")
                db.session.commit()
            flash("Invalid email or password.", "error")
    return render_template("auth/login.html", next_url=next_url)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if not current_app.config.get("AUTH_ENABLED", False):
        return redirect(url_for("suite_dashboard"))
    if current_user.is_authenticated:
        return redirect(url_for("suite_dashboard"))
    if not current_app.config.get("REGISTRATION_ENABLED", True):
        return render_template("auth/registration_closed.html"), 403

    if request.method == "POST":
        limited = _form_rate_limit(
            "register",
            int(current_app.config.get("REGISTRATION_IP_LIMIT", 5)),
            int(current_app.config.get("REGISTRATION_IP_WINDOW_SECONDS", 3600)),
        )
        if limited:
            return limited
        email = _normalise_email(request.form.get("email"))
        full_name = str(request.form.get("full_name") or "").strip()
        organization = str(request.form.get("organization") or "").strip()
        country_code = normalize_country_code(request.form.get("country_code"))
        password = str(request.form.get("password") or "")
        confirm = str(request.form.get("confirm_password") or "")
        accepted = bool(request.form.get("accept_terms"))
        errors: list[str] = []
        if not _valid_email(email):
            errors.append("Enter a valid email address.")
        if len(full_name) < 2:
            errors.append("Enter your full name.")
        if not country_code:
            errors.append("Select your country.")
        errors.extend(validate_password(password, email))
        if password != confirm:
            errors.append("Passwords do not match.")
        if not accepted:
            errors.append("Acknowledge the preliminary-engineering terms before requesting access.")
        if db.session.scalar(select(User).where(func.lower(User.email) == email)):
            errors.append("An account request already exists for this email.")

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            user = User(
                email=email,
                full_name=full_name[:160],
                organization=organization[:200],
                country_code=country_code,
                country_name=country_name(country_code),
                role="user",
                licensed_tier="entry",
                status="pending",
                terms_accepted_at=_utcnow(),
                password_hash="",
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            ensure_default_entitlements(user, flush=True)
            audit("registration_requested", user=user, detail=f"organization={organization[:200]}")
            db.session.commit()
            admin_email = "admin@totalrodesign.com"
            admin_url = url_for("auth.admin_users", _external=True)
            send_email(
                "New Total Water Design Suite account awaiting approval",
                [admin_email],
                f"""A new Total Water Design Suite account is awaiting approval.

Name: {user.full_name}
Email: {user.email}
Organization: {user.organization or 'Not provided'}
Country: {user.country_name or 'Not provided'}
Requested tier: Entry
Request IP: {_request_ip()}

Review and approve or reject the request:
{admin_url}
""",
            )
            return render_template("auth/pending.html", email=user.email)

    return render_template("auth/register.html")


@auth_bp.post("/v1/auth/device-sessions")
def mobile_register_device():
    """Register the current authenticated device and return an opaque token envelope."""
    if (error := _mobile_contract_error()):
        return error
    if not current_user.is_authenticated or current_user.status != "active":
        return _mobile_error("UNAUTHENTICATED", 401)
    data = request.get_json(silent=True) or {}
    device_id = str(data.get("device_id") or "")
    platform = str(data.get("platform") or "unknown")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", device_id) or platform not in {"ios", "android", "unknown"}:
        return _mobile_error("VALIDATION_FAILED", 400)
    row = MobileDeviceSession(id=uuid.uuid4().hex, user_id=current_user.id, device_id=device_id,
                              device_name=str(data.get("device_name") or "")[:128], platform=platform,
                              access_hash="pending", refresh_hash="pending")
    envelope = _issue_mobile_tokens(row)
    db.session.add(row)
    audit("mobile_device_registered", user=current_user, actor=current_user, detail=f"device={device_id}")
    db.session.commit()
    response = jsonify(envelope); response.headers["Cache-Control"] = "no-store"
    return response, 201


@auth_bp.post("/v1/auth/refresh")
def mobile_refresh():
    if (error := _mobile_contract_error()):
        return error
    data = request.get_json(silent=True) or {}
    token, device_id = str(data.get("refresh_token") or ""), str(data.get("device_id") or "")
    if not token or not device_id:
        return _mobile_error("VALIDATION_FAILED", 400)
    row = db.session.scalar(select(MobileDeviceSession).where(MobileDeviceSession.device_id == device_id))
    now = _utcnow()
    if not row or row.refresh_hash != _mobile_hash(token):
        if row and row.state == "active":
            row.state, row.revoked_at = "compromised", now
            audit("mobile_refresh_reused", user=db.session.get(User, row.user_id), detail=f"session={row.id}")
            db.session.commit()
        return _mobile_error("TOKEN_REUSED", 401)
    if row.state != "active" or _mobile_utc(row.expires_at) <= now:
        return _mobile_error("SESSION_REVOKED", 401)
    # A conditional UPDATE makes the consumed refresh hash single-use across workers.
    old_hash, generation = row.refresh_hash, row.refresh_generation
    access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    access_expiry = now + timedelta(minutes=int(current_app.config.get("MOBILE_ACCESS_MINUTES", 15)))
    changed = db.session.query(MobileDeviceSession).filter_by(id=row.id, refresh_hash=old_hash,
        refresh_generation=generation, state="active").update({"refresh_hash": _mobile_hash(refresh),
        "access_hash": _mobile_hash(access), "access_expires_at": access_expiry,
        "refresh_generation": generation + 1, "last_seen_at": now}, synchronize_session=False)
    if changed != 1:
        db.session.rollback()
        return _mobile_error("TOKEN_REUSED", 401)
    db.session.commit()
    response = jsonify({"token_type": "Bearer", "access_token": access, "refresh_token": refresh,
                        "expires_in": int((access_expiry - now).total_seconds()), "session_id": row.id,
                        "refresh_generation": generation + 1})
    response.headers["Cache-Control"] = "no-store"
    return response


@auth_bp.get("/v1/auth/device-sessions")
def mobile_list_sessions():
    if (error := _mobile_contract_error()): return error
    current = _mobile_bearer_session()
    if not current: return _mobile_error("UNAUTHENTICATED", 401)
    rows = db.session.scalars(select(MobileDeviceSession).where(MobileDeviceSession.user_id == current.user_id).order_by(MobileDeviceSession.last_seen_at.desc())).all()
    response = jsonify([_mobile_session_payload(row, current=row.id == current.id) for row in rows]); response.headers["Cache-Control"] = "no-store"
    return response


@auth_bp.delete("/v1/auth/device-sessions/<session_id>")
def mobile_revoke_session(session_id: str):
    if (error := _mobile_contract_error()): return error
    current = _mobile_bearer_session()
    if not current: return _mobile_error("UNAUTHENTICATED", 401)
    row = db.session.get(MobileDeviceSession, session_id)
    if not row or row.user_id != current.user_id: return _mobile_error("NOT_FOUND", 404)
    if row.state == "active": row.state, row.revoked_at = "revoked", _utcnow()
    db.session.commit()
    return ("", 204, {"Cache-Control": "no-store"})


@auth_bp.post("/v1/auth/logout")
def mobile_logout():
    if (error := _mobile_contract_error()): return error
    current = _mobile_bearer_session()
    if not current: return ("", 204, {"Cache-Control": "no-store"})
    current.state, current.revoked_at = "revoked", _utcnow()
    db.session.commit()
    return ("", 204, {"Cache-Control": "no-store"})


@auth_bp.post("/v1/auth/logout-all")
def mobile_logout_all():
    if (error := _mobile_contract_error()): return error
    current = _mobile_bearer_session()
    if not current: return _mobile_error("UNAUTHENTICATED", 401)
    db.session.query(MobileDeviceSession).filter_by(user_id=current.user_id, state="active").update({"state": "revoked", "revoked_at": _utcnow()})
    db.session.commit()
    return ("", 204, {"Cache-Control": "no-store"})


@auth_bp.post("/v1/mobile/navigation")
def mobile_navigation():
    if (error := _mobile_contract_error()): return error
    current = _mobile_bearer_session()
    if not current: return _mobile_error("UNAUTHENTICATED", 401)
    data = request.get_json(silent=True) or {}
    route = data.get("route")
    if data.get("contract") != MOBILE_CONTRACT or route not in MOBILE_ROUTES or any(key in data for key in ("url", "href", "scheme", "host", "path", "fragment")):
        return _mobile_error("VALIDATION_FAILED", 400)
    response = jsonify({"contract": MOBILE_CONTRACT, "route": route,
                        **{key: data[key] for key in ("resource_id", "project_id", "revision_id", "reauthentication_required") if key in data}})
    response.headers["Cache-Control"] = "no-store"
    return response


@auth_bp.post("/v1/mobile/notification-permission")
def mobile_notification_permission():
    if (error := _mobile_contract_error()): return error
    current = _mobile_bearer_session()
    data = request.get_json(silent=True) or {}
    if not current: return _mobile_error("UNAUTHENTICATED", 401)
    if data.get("status") not in {"granted", "denied", "provisional"}: return _mobile_error("VALIDATION_FAILED", 400)
    return jsonify({"contract": MOBILE_CONTRACT, "status": data["status"]})


@auth_bp.post("/v1/mobile/push-tokens")
def mobile_push_token():
    if (error := _mobile_contract_error()): return error
    current = _mobile_bearer_session(); data = request.get_json(silent=True) or {}
    token, provider = str(data.get("token") or ""), str(data.get("provider") or "")
    if not current: return _mobile_error("UNAUTHENTICATED", 401)
    if not token or len(token) > 4096 or provider not in {"apns", "fcm"}: return _mobile_error("VALIDATION_FAILED", 400)
    digest = _mobile_hash(token); row = db.session.scalar(select(MobilePushToken).where(MobilePushToken.token_hash == digest))
    # At most one provider credential is active per device session.  Rotation
    # deletes the superseded credential before accepting the replacement.
    if row is None:
        db.session.query(MobilePushToken).filter_by(session_id=current.id).delete()
        db.session.add(MobilePushToken(id=uuid.uuid4().hex, session_id=current.id, token_hash=digest, provider=provider))
    else:
        db.session.query(MobilePushToken).filter(MobilePushToken.session_id == current.id,
            MobilePushToken.id != row.id).delete(synchronize_session=False)
        row.session_id, row.provider, row.rotated_at = current.id, provider, _utcnow()
    db.session.commit()
    return ("", 204, {"Cache-Control": "no-store"})


@auth_bp.delete("/v1/mobile/push-tokens")
def mobile_delete_push_token():
    if (error := _mobile_contract_error()): return error
    current = _mobile_bearer_session(); data = request.get_json(silent=True) or {}
    if not current: return _mobile_error("UNAUTHENTICATED", 401)
    token = str(data.get("token") or "")
    if token: db.session.query(MobilePushToken).filter_by(session_id=current.id, token_hash=_mobile_hash(token)).delete()
    db.session.commit()
    return ("", 204, {"Cache-Control": "no-store"})


@auth_bp.post("/v1/mobile/notification-payloads/validate")
def mobile_validate_notification_payload():
    if (error := _mobile_contract_error()): return error
    current = _mobile_bearer_session(); data = request.get_json(silent=True) or {}
    navigation = data.get("navigationInput")
    if not current: return _mobile_error("UNAUTHENTICATED", 401)
    if data.get("version") != 1 or not isinstance(navigation, dict) or navigation.get("contract") != MOBILE_CONTRACT or navigation.get("route") not in MOBILE_ROUTES or any(key in navigation for key in ("url", "href", "scheme", "host", "path", "fragment")):
        return _mobile_error("VALIDATION_FAILED", 400)
    return jsonify({"contract": MOBILE_CONTRACT, "valid": True})


@auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        audit("logout", user=current_user, actor=current_user)
        db.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        limited = _form_rate_limit(
            "forgot-password",
            int(current_app.config.get("PASSWORD_RESET_IP_LIMIT", 5)),
            int(current_app.config.get("PASSWORD_RESET_IP_WINDOW_SECONDS", 3600)),
        )
        if limited:
            return limited
        email = _normalise_email(request.form.get("email"))
        user = db.session.scalar(select(User).where(func.lower(User.email) == email)) if email else None
        if user and user.status == "active":
            send_reset_email(user)
            audit("password_reset_requested", user=user)
            db.session.commit()
        # Always use the same message to avoid account enumeration.
        flash("If an active account exists for that email, a reset link has been sent.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    user = resolve_password_reset_token(token)
    if not user or user.status != "active":
        return render_template("auth/reset_invalid.html"), 400
    if request.method == "POST":
        password = str(request.form.get("password") or "")
        confirm = str(request.form.get("confirm_password") or "")
        errors = validate_password(password, user.email)
        if password != confirm:
            errors.append("Passwords do not match.")
        if errors:
            for error in errors:
                flash(error, "error")
        else:
            user.set_password(password)
            user.failed_login_count = 0
            user.locked_until = None
            audit("password_reset_completed", user=user, actor=user)
            db.session.commit()
            logout_user()
            session.clear()
            flash("Password updated. Sign in with your new password.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", token=token, user=user)


@auth_bp.route("/accept-terms", methods=["GET", "POST"])
def accept_terms():
    if not current_user.is_authenticated:
        return unauthorized()
    next_url = _safe_next(request.args.get("next") or request.form.get("next")) or url_for("suite_dashboard")
    disclaimer_path = Path(current_app.root_path) / "LEGAL_AND_ENGINEERING_DISCLAIMER.txt"
    disclaimer_text = disclaimer_path.read_text(encoding="utf-8") if disclaimer_path.exists() else (
        "Total RO Design provides preliminary engineering estimates that must be independently verified."
    )
    if request.method == "POST":
        if not request.form.get("accept_terms"):
            flash("Acknowledge the preliminary-engineering terms to continue.", "error")
        else:
            current_user.terms_accepted_at = _utcnow()
            audit("terms_accepted", user=current_user, actor=current_user)
            db.session.commit()
            return redirect(next_url)
    return render_template(
        "auth/accept_terms.html",
        disclaimer_text=disclaimer_text,
        next_url=next_url,
    )


@auth_bp.get("/account")
def account():
    if not current_user.is_authenticated or current_user.status != "active":
        return unauthorized()
    return render_template("auth/account.html", product_entitlements=serialized_product_entitlements(current_user))


@auth_bp.get("/admin/users")
@admin_required
def admin_users():
    users = db.session.scalars(select(User).order_by(User.created_at.desc())).all()
    addresses = db.session.scalars(select(LoginAddress).order_by(LoginAddress.last_seen_at.desc())).all()
    by_user: dict[int, list[LoginAddress]] = defaultdict(list)
    for row in addresses:
        by_user[int(row.user_id)].append(row)
    login_stats = {
        user.id: {
            "count": len(by_user.get(user.id, [])),
            "last_ip": by_user.get(user.id, [None])[0].ip_address if by_user.get(user.id) else "",
            "last_seen_at": by_user.get(user.id, [None])[0].last_seen_at if by_user.get(user.id) else None,
            "all_ips": " ".join(row.ip_address for row in by_user.get(user.id, [])),
        }
        for user in users
    }
    now = _utcnow()
    pending_hours = {}
    for user in users:
        created = _aware(user.created_at)
        pending_hours[user.id] = max(0.0, (now - created).total_seconds() / 3600.0) if user.status == "pending" and created else 0.0
    return render_template(
        "auth/admin_users.html",
        users=users,
        products=product_catalog(),
        entitlement_map={u.id: serialized_product_entitlements(u) for u in users},
        login_stats=login_stats,
        pending_hours=pending_hours,
        countries=COUNTRIES,
        counts={
            "all": len(users),
            "pending": sum(1 for u in users if u.status == "pending"),
            "active": sum(1 for u in users if u.status == "active"),
            "restricted": sum(1 for u in users if u.status in {"disabled", "suspended", "canceled", "rejected"}),
        },
    )


@auth_bp.get("/admin/users/<int:user_id>/ips")
@admin_required
def admin_user_ips(user_id: int):
    user = db.get_or_404(User, user_id)
    rows = db.session.scalars(
        select(LoginAddress).where(LoginAddress.user_id == user.id).order_by(LoginAddress.last_seen_at.desc())
    ).all()
    return jsonify({
        "user": {"id": user.id, "name": user.full_name, "email": user.email},
        "addresses": [{
            "ip_address": row.ip_address,
            "login_count": int(row.login_count or 0),
            "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
            "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
            "last_user_agent": row.last_user_agent,
        } for row in rows],
    })


def _active_admin_count() -> int:
    return int(db.session.scalar(
        select(func.count(User.id)).where(User.role == "admin", User.status == "active")
    ) or 0)


def _send_account_status_email(user: User, status: str, feedback: str = "") -> tuple[bool, str]:
    feedback = str(feedback or "").strip()
    signin = url_for("auth.login", _external=True)
    if status == "active":
        subject = "Your Total Water Design Suite account is active"
        body = f"""Hello {user.full_name},

Your Total Water Design Suite account is active.

Licensed Total RO Design tier: {user.licensed_tier.title()}
Sign in: {signin}

Total Water Design Suite
support@totalrodesign.com
"""
    elif status == "rejected":
        subject = "Total Water Design Suite account request update"
        body = f"""Hello {user.full_name},

Your Total Water Design Suite account request was not approved.

Administrator feedback:
{feedback or 'No additional feedback was provided.'}

If you believe this requires review, contact support@totalrodesign.com.

Total Water Design Suite
"""
    elif status == "suspended":
        subject = "Your Total Water Design Suite account has been suspended"
        body = f"""Hello {user.full_name},

Access to your Total Water Design Suite account has been suspended.

Administrator feedback:
{feedback or 'No additional feedback was provided.'}

Contact support@totalrodesign.com if you need this reviewed.

Total Water Design Suite
"""
    elif status == "canceled":
        subject = "Your Total Water Design Suite account has been canceled"
        body = f"""Hello {user.full_name},

Your Total Water Design Suite account has been canceled.

Administrator feedback:
{feedback or 'No additional feedback was provided.'}

Contact support@totalrodesign.com if you need this reviewed.

Total Water Design Suite
"""
    else:
        return False, "No notification template exists for this account state."
    return send_email(subject, [user.email], body)


@auth_bp.post("/admin/users/<int:user_id>/decision")
@admin_required
def admin_user_decision(user_id: int):
    user = db.get_or_404(User, user_id)
    action = str(request.form.get("action") or "").strip().lower()
    feedback = str(request.form.get("feedback") or "").strip()[:2000]
    status_by_action = {
        "approve": "active",
        "reactivate": "active",
        "reject": "rejected",
        "suspend": "suspended",
        "cancel": "canceled",
    }
    if action not in status_by_action:
        abort(400)
    if action in {"reject", "suspend", "cancel"} and len(feedback) < 3:
        flash("Provide a short reason or feedback before applying that account action.", "error")
        return redirect(url_for("auth.admin_users"))

    new_status = status_by_action[action]
    if user.id == current_user.id and new_status != "active":
        flash("You cannot suspend, cancel, or reject your own administrator account.", "error")
        return redirect(url_for("auth.admin_users"))
    if user.role == "admin" and user.status == "active" and new_status != "active" and _active_admin_count() <= 1:
        flash("At least one active administrator must remain.", "error")
        return redirect(url_for("auth.admin_users"))

    old_status = user.status
    user.status = new_status
    if new_status == "active":
        user.approved_at = user.approved_at or _utcnow()
        user.approved_by_id = current_user.id
        user.failed_login_count = 0
        user.locked_until = None
    audit(
        f"account_{action}",
        user=user,
        actor=current_user,
        detail=f"status={old_status}->{new_status}; feedback={feedback}",
    )
    notification_id = None
    if new_status == "active" and old_status != "active":
        subject, body, template = _access_email_content(user, "account_activated")
        notification = _queue_email_notification(user,"account_activated",subject,body,template)
        db.session.flush(); notification_id = notification.id
    db.session.commit()
    if notification_id:
        _deliver_notification(notification_id)
        flash(f"{user.email} is now {new_status}. Welcome notification queued.", "success")
    else:
        sent, detail = _send_account_status_email(user, new_status, feedback)
        message = f"{user.email} is now {new_status}."
        if not sent: message += f" Email delivery: {detail}"
        flash(message, "success" if sent else "warning")
    return redirect(url_for("auth.admin_users"))


@auth_bp.post("/admin/users/<int:user_id>/update")
@admin_required
def admin_update_user(user_id: int):
    user = db.get_or_404(User, user_id)
    new_role = str(request.form.get("role") or user.role).lower()
    requested_country = request.form.get("country_code")
    new_country = normalize_country_code(requested_country) if requested_country is not None else (user.country_code or "")
    new_tier = normalize_tier(request.form.get("ro_tier") or request.form.get("licensed_tier"), user.licensed_tier)
    if new_role not in {"admin", "user"}:
        abort(400)
    if user.id == current_user.id and new_role != "admin":
        flash("You cannot demote your own administrator account.", "error")
        return redirect(url_for("auth.admin_users"))
    if user.role == "admin" and user.status == "active" and new_role != "admin" and _active_admin_count() <= 1:
        flash("At least one active administrator must remain.", "error")
        return redirect(url_for("auth.admin_users"))

    old = f"role={user.role}, tier={user.licensed_tier}"
    previous_access = {x.product_id:(bool(x.enabled),normalize_tier(x.tier,"entry")) for x in db.session.scalars(select(ProductEntitlement).where(ProductEntitlement.user_id==user.id)).all()}
    user.role = new_role
    user.licensed_tier = new_tier
    if new_country:
        user.country_code = new_country
        user.country_name = country_name(new_country)
    entitlements = ensure_default_entitlements(user)
    for product in PRODUCTS:
        row = entitlements[product.product_id]
        enabled_key = f"product_{product.product_id}_enabled"
        tier_key = f"product_{product.product_id}_tier"
        row.enabled = bool(request.form.get(enabled_key))
        row.tier = normalize_tier(request.form.get(tier_key), row.tier)
        if product.product_id == "ro":
            user.licensed_tier = row.tier
    audit(
        "account_access_updated",
        user=user,
        actor=current_user,
        detail=f"{old} -> role={new_role}, tier={user.licensed_tier}",
    )
    changes=[]
    for product in PRODUCTS:
        row=entitlements[product.product_id]; before=previous_access.get(product.product_id,(False,"entry"))
        if row.enabled and not before[0]: changes.append(f"{product.name} — {row.tier.title()}")
        elif row.enabled and TIER_ORDER.get(row.tier,0)>TIER_ORDER.get(before[1],0): changes.append(f"{product.name} upgraded to {row.tier.title()}")
    notification_id=None
    if changes:
        subject,body,template=_access_email_content(user,"access_expanded",changes=changes)
        note=_queue_email_notification(user,"access_expanded",subject,body,template); db.session.flush(); notification_id=note.id
    db.session.commit()
    if notification_id: _deliver_notification(notification_id)
    flash(f"Updated access for {user.email}." + (" Notification queued." if notification_id else ""), "success")
    return redirect(url_for("auth.admin_users"))


@auth_bp.post("/admin/users/<int:user_id>/send-reset")
@admin_required
def admin_send_reset(user_id: int):
    user = db.get_or_404(User, user_id)
    if user.status != "active":
        flash("Activate the account before sending a password-reset link.", "error")
    else:
        sent, detail = send_reset_email(user)
        audit("admin_password_reset_sent", user=user, actor=current_user, detail=detail)
        db.session.commit()
        flash("Password reset link sent." if sent else detail, "success" if sent else "warning")
    return redirect(url_for("auth.admin_users"))


@auth_bp.post("/admin/users/create")
@admin_required
def admin_create_user():
    email = _normalise_email(request.form.get("email"))
    full_name = str(request.form.get("full_name") or "").strip()
    organization = str(request.form.get("organization") or "").strip()
    country_code = normalize_country_code(request.form.get("country_code"))
    role = str(request.form.get("role") or "user").lower()
    tier = normalize_tier(
        request.form.get("new_product_ro_tier") or request.form.get("licensed_tier"),
        "entry",
    )
    if not _valid_email(email) or len(full_name) < 2 or role not in {"admin", "user"} or not country_code:
        flash("Provide a valid name, email, country, role and tier.", "error")
        return redirect(url_for("auth.admin_users"))
    if db.session.scalar(select(User).where(func.lower(User.email) == email)):
        flash("That email already has an account.", "error")
        return redirect(url_for("auth.admin_users"))
    user = User(
        email=email,
        full_name=full_name[:160],
        organization=organization[:200],
        country_code=country_code,
        country_name=country_name(country_code),
        role=role,
        licensed_tier=tier,
        status="active",
        approved_at=_utcnow(),
        approved_by_id=current_user.id,
        terms_accepted_at=None,
        password_hash="",
    )
    user.set_password(secrets.token_urlsafe(48))
    db.session.add(user)
    db.session.flush()
    entitlements = ensure_default_entitlements(user, flush=True)
    product_controls_present = any(
        f"new_product_{product.product_id}_enabled" in request.form
        or f"new_product_{product.product_id}_tier" in request.form
        for product in PRODUCTS
    )
    if product_controls_present:
        enabled_products: list[str] = []
        for product in PRODUCTS:
            row = entitlements[product.product_id]
            row.enabled = bool(request.form.get(f"new_product_{product.product_id}_enabled"))
            row.tier = normalize_tier(request.form.get(f"new_product_{product.product_id}_tier"), row.tier)
            if row.enabled:
                enabled_products.append(f"{product.product_id}:{row.tier}")
        user.licensed_tier = entitlements["ro"].tier
        entitlement_detail = ",".join(enabled_products) or "none"
    else:
        # Backward-compatible behavior for older forms/installers.
        entitlements["ro"].enabled = True
        entitlements["ro"].tier = tier
        user.licensed_tier = tier
        entitlement_detail = f"ro:{tier}"
    audit(
        "account_created_by_admin",
        user=user,
        actor=current_user,
        detail=f"role={role}; products={entitlement_detail}",
    )
    subject,body,template=_access_email_content(user,"account_activated")
    note=_queue_email_notification(user,"account_activated",subject,body,template); db.session.flush(); note_id=note.id
    db.session.commit()
    _deliver_notification(note_id)
    sent, detail = send_reset_email(user)
    flash(
        "Account created; welcome notification queued and password setup link sent." if sent else f"Account created; welcome notification queued. {detail}",
        "success" if sent else "warning",
    )
    return redirect(url_for("auth.admin_users"))


@auth_bp.get("/api/projects")
@login_required
def project_list_api():
    rows = db.session.execute(
        select(ProjectRevision, ProjectFamily)
        .join(ProjectFamily, ProjectFamily.id == ProjectRevision.family_id)
        .where(ProjectFamily.owner_user_id == current_user.id)
        .order_by(ProjectRevision.updated_at.desc(), ProjectRevision.id.desc())
    ).all()
    return jsonify({"projects": [_project_meta(row, family) for row, family in rows]})


@auth_bp.post("/api/projects")
@login_required
def project_create_api():
    body = request.get_json(force=True) or {}
    product_id = str(body.get("product_id") or "ro").strip().lower()
    if product_id not in PROJECT_PREFIXES or product_id not in PRODUCT_BY_ID:
        return jsonify({"error":"Unsupported Suite application for project creation."}), 400
    if not current_user.is_admin and not user_can_access_product(current_user, product_id):
        return jsonify({"error":"This application is not included in the current account.","product_id":product_id}), 403
    try:
        snapshot, encoded, size = _project_snapshot_payload(body.get("snapshot") if "snapshot" in body else body)
    except (TypeError, ValueError) as exc:
        return jsonify({"error":str(exc)}), 400
    next_family_base = int(db.session.scalar(select(func.max(ProjectFamily.base_number))) or 0) + 1
    project_country_code = normalize_country_code(body.get("project_country_code") or (snapshot.get("project") or {}).get("project_country_code"))
    family = ProjectFamily(
        family_uuid=str(uuid.uuid4()), base_number=next_family_base, owner_user_id=current_user.id,
        project_country_code=project_country_code or None, project_country_name=country_name(project_country_code),
    )
    db.session.add(family); db.session.flush()
    revision_number = 0
    product_number = _next_product_project_number(product_id)
    visible_id = _product_visible_id(product_id, product_number, revision_number)
    meta = snapshot.get("project") if isinstance(snapshot.get("project"), dict) else {}
    meta["revision"] = f"Rev {revision_number}"; meta["project_id"] = visible_id
    meta["project_country_code"] = family.project_country_code or ""; meta["project_country"] = family.project_country_name or ""
    snapshot["project"] = meta; snapshot["saved_at"] = _utcnow().isoformat()
    _, encoded, size = _project_snapshot_payload(snapshot)
    default_name = "Total Bio Design Project" if product_id=="bio" else "Total ZLD Design Project" if product_id=="zld" else "Total RO Design Project"
    row = ProjectRevision(family_id=family.id, product_id=product_id, revision=revision_number, visible_id=visible_id,
                          name=str(meta.get("project_name") or default_name)[:200], snapshot_json=encoded,
                          snapshot_bytes=size, created_by_user_id=current_user.id)
    db.session.add(row); db.session.flush()
    audit("project_created",user=current_user,actor=current_user,detail=f"project={row.visible_id}; name={row.name}")
    record_telemetry("project_created", application=product_id, metadata={"product_id":product_id}, user=current_user)
    db.session.commit()
    return jsonify({"project":_project_meta(row,family)}),201


@auth_bp.get("/api/projects/<int:revision_id>")
@login_required
def project_read_api(revision_id: int):
    row, family = _project_owner_row(revision_id)
    if not row or not family or family.owner_user_id != current_user.id:
        abort(404)
    return jsonify({"project": _project_meta(row, family), "snapshot": json.loads(row.snapshot_json)})


@auth_bp.put("/api/projects/<int:revision_id>")
@login_required
def project_update_api(revision_id: int):
    row, family = _project_owner_row(revision_id)
    if not row or not family or family.owner_user_id != current_user.id:
        abort(404)
    body = request.get_json(force=True) or {}
    try:
        snapshot, encoded, size = _project_snapshot_payload(body.get("snapshot") if "snapshot" in body else body)
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    meta = snapshot.get("project") if isinstance(snapshot.get("project"), dict) else {}
    requested_country = normalize_country_code(meta.get("project_country_code"))
    if requested_country:
        family.project_country_code = requested_country
        family.project_country_name = country_name(requested_country)
    meta["project_country_code"] = family.project_country_code or ""
    meta["project_country"] = family.project_country_name or ""
    meta["revision"] = f"Rev {row.revision}"
    meta["project_id"] = row.visible_id
    snapshot["project"] = meta
    snapshot["saved_at"] = _utcnow().isoformat()
    _, encoded, size = _project_snapshot_payload(snapshot)
    row.name = str(meta.get("project_name") or row.name or "Total RO Design Project")[:200]
    row.snapshot_json = encoded
    row.snapshot_bytes = size
    row.updated_at = _utcnow()
    family.updated_at = row.updated_at
    audit("project_saved", user=current_user, actor=current_user, detail=f"project={row.visible_id}; name={row.name}")
    db.session.commit()
    return jsonify({"project": _project_meta(row, family)})


@auth_bp.post("/api/projects/<int:revision_id>/copy")
@login_required
def project_copy_api(revision_id: int):
    source, family = _project_owner_row(revision_id)
    if not source or not family or family.owner_user_id != current_user.id:
        abort(404)
    body = request.get_json(silent=True) or {}
    raw_snapshot = body.get("snapshot")
    try:
        snapshot = raw_snapshot if isinstance(raw_snapshot, dict) else json.loads(source.snapshot_json)
        snapshot, _encoded, _size = _project_snapshot_payload(snapshot)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return jsonify({"error": str(exc)}), 400
    source_product_number = _project_visible_base(source.visible_id)
    if source_product_number is None:
        return jsonify({"error":"The source project identifier is invalid and cannot be revised."}),409
    prefix = PROJECT_PREFIXES.get(source.product_id, source.product_id.upper())
    next_revision = int(db.session.scalar(
        select(func.max(ProjectRevision.revision)).where(
            ProjectRevision.product_id == source.product_id,
            ProjectRevision.visible_id.like(f"{prefix}-{source_product_number}-%"),
        )
    ) or 0) + 1
    visible_id = _product_visible_id(source.product_id, source_product_number, next_revision)
    meta = snapshot.get("project") if isinstance(snapshot.get("project"), dict) else {}
    if body.get("name"):
        meta["project_name"] = str(body.get("name"))[:200]
    meta["revision"] = f"Rev {next_revision}"
    meta["project_id"] = visible_id
    meta["project_country_code"] = family.project_country_code or ""
    meta["project_country"] = family.project_country_name or ""
    snapshot["project"] = meta
    snapshot["saved_at"] = _utcnow().isoformat()
    _, encoded, size = _project_snapshot_payload(snapshot)
    row = ProjectRevision(
        family_id=family.id,
        product_id=source.product_id,
        revision=next_revision,
        visible_id=visible_id,
        name=str(meta.get("project_name") or source.name)[:200],
        snapshot_json=encoded,
        snapshot_bytes=size,
        created_by_user_id=current_user.id,
        source_revision_id=source.id,
    )
    db.session.add(row)
    family.updated_at = _utcnow()
    db.session.flush()
    audit("project_revision_created", user=current_user, actor=current_user, detail=f"source={source.visible_id}; project={row.visible_id}")
    db.session.commit()
    return jsonify({"project": _project_meta(row, family)}), 201


@auth_bp.post("/api/projects/<int:revision_id>/handoff/ro")
@login_required
def project_handoff_to_ro_api(revision_id: int):
    source, family = _project_owner_row(revision_id)
    if not source or not family or family.owner_user_id != current_user.id:
        abort(404)
    if source.product_id != "bio":
        return jsonify({"error":"Only Total Bio Design projects can currently be handed off to Total RO Design."}),409
    if not current_user.is_admin and not user_can_access_product(current_user,"ro"):
        return jsonify({"error":"Total RO Design is not included in the current account.","product_id":"ro"}),403
    body=request.get_json(silent=True) or {}; handoff=body.get("handoff") if isinstance(body.get("handoff"),dict) else {}
    try: source_snapshot=json.loads(source.snapshot_json)
    except Exception: source_snapshot={}
    product_number=_next_product_project_number("ro"); visible_id=_product_visible_id("ro",product_number,0)
    source_meta=source_snapshot.get("project") if isinstance(source_snapshot.get("project"),dict) else {}
    name=str(body.get("name") or source_meta.get("project_name") or source.name or "Total RO Design Project")[:200]
    snapshot={"format":"Total RO Design Project","schema_version":7,"app_version":"0.2","saved_at":_utcnow().isoformat(),
              "project":{"project_name":name,"project_id":visible_id,"revision":"Rev 0","project_country_code":family.project_country_code or "","project_country":family.project_country_name or ""},
              "suite_handoff":{"source_product_id":source.product_id,"source_revision_id":source.id,"source_visible_id":source.visible_id,"source_project_name":source.name,"source_family_id":family.id,"handoff_type":"bio_to_ro"},
              "bio_handoff":handoff}
    snapshot,encoded,size=_project_snapshot_payload(snapshot)
    row=ProjectRevision(family_id=family.id,product_id="ro",revision=0,visible_id=visible_id,name=name,snapshot_json=encoded,snapshot_bytes=size,created_by_user_id=current_user.id,source_revision_id=source.id)
    db.session.add(row); family.updated_at=_utcnow(); db.session.flush()
    audit("project_handoff_created",user=current_user,actor=current_user,detail=f"source={source.visible_id}; target={row.visible_id}; handoff=bio_to_ro")
    record_telemetry("project_handoff_created",application="ro",metadata={"product_id":"ro"},user=current_user)
    db.session.commit()
    return jsonify({"project":_project_meta(row,family),"source_project":_project_meta(source,family),"handoff":"bio_to_ro"}),201


@auth_bp.get("/admin/projects")
@admin_required
def admin_projects():
    rows = db.session.scalars(select(ProjectRevision).order_by(ProjectRevision.updated_at.desc(), ProjectRevision.id.desc())).all()
    family_ids = {row.family_id for row in rows}
    families = {row.id: row for row in db.session.scalars(select(ProjectFamily).where(ProjectFamily.id.in_(family_ids))).all()} if family_ids else {}
    owner_ids = {family.owner_user_id for family in families.values()}
    owners = {row.id: row for row in db.session.scalars(select(User).where(User.id.in_(owner_ids))).all()} if owner_ids else {}
    project_rows = []
    for row in rows:
        family = families.get(row.family_id)
        owner = owners.get(family.owner_user_id) if family else None
        project_rows.append({
            "row": row,
            "family": family,
            "owner": owner,
            "size_kb": round((row.snapshot_bytes or 0) / 1024.0, 1),
        })
    return render_template(
        "auth/admin_projects.html",
        project_rows=project_rows,
        project_count=len(project_rows),
        family_count=len({item["family"].id for item in project_rows if item["family"]}),
        owner_count=len({item["owner"].id for item in project_rows if item["owner"]}),
        products=product_catalog(),
        countries=COUNTRIES,
    )


@auth_bp.get("/admin/metrics")
@admin_required
def admin_metrics():
    now=_utcnow(); window=str(request.args.get("window") or "30d").lower()
    days={"24h":1,"7d":7,"30d":30,"90d":90,"1y":365,"all":36500}.get(window,30)
    start=now-timedelta(days=days)
    users=db.session.scalars(select(User)).all()
    sessions=db.session.scalars(select(TelemetrySession).where(TelemetrySession.started_at>=start)).all()
    events=db.session.scalars(select(TelemetryEvent).where(TelemetryEvent.created_at>=start)).all()
    projects=db.session.scalars(select(ProjectRevision)).all()
    families={f.id:f for f in db.session.scalars(select(ProjectFamily)).all()}
    active_ids={s.user_id for s in sessions}
    durations=[max(0.0,((_aware(s.ended_at) or _aware(s.last_seen_at) or now)-(_aware(s.started_at) or now)).total_seconds()) for s in sessions]
    calc=[e for e in events if e.event_type in {"calculation_completed","calculation_failed"}]
    runtimes=sorted(float(e.duration_ms or 0)/1000.0 for e in calc if e.duration_ms is not None)
    def percentile(vals,p):
        if not vals:return 0.0
        idx=min(len(vals)-1,max(0,int(round((len(vals)-1)*p))))
        return vals[idx]
    daily={}
    for e in events:
        day=(_aware(e.created_at) or now).date().isoformat(); row=daily.setdefault(day,{"events":0,"calculations":0,"failures":0,"cpu_seconds":0.0}); row["events"]+=1
        if e.event_type.startswith("calculation_"): row["calculations"]+=int(e.event_type in {"calculation_completed","calculation_failed"}); row["failures"]+=int(e.event_type=="calculation_failed")
        row["cpu_seconds"]+=float(e.cpu_seconds or 0)
    app_counts={}; tier_counts={}; country_counts={}
    for e in events: app_counts[e.application]=app_counts.get(e.application,0)+1
    for u in users:
        tier_counts[u.licensed_tier]=tier_counts.get(u.licensed_tier,0)+1
        if u.country_name: country_counts[u.country_name]=country_counts.get(u.country_name,0)+1
    project_bytes=sum(int(p.snapshot_bytes or 0) for p in projects)
    calc_count=len(calc); active=max(1,len(active_ids))
    capacity=[{"concurrent_users":n,"estimated_cpu_hours_day":(sum(float(e.cpu_seconds or 0) for e in calc)/3600.0/max(1,days))*n/active,
               "estimated_project_storage_mb":project_bytes/1048576.0*n/max(1,len(users))} for n in (10,25,50,100,250,500)]
    return render_template("auth/admin_metrics.html",window=window,users=len(users),active_users=len(active_ids),sessions=len(sessions),
        avg_session_s=(sum(durations)/len(durations) if durations else 0),median_session_s=(sorted(durations)[len(durations)//2] if durations else 0),
        calculations=calc_count,calc_failures=sum(1 for e in calc if not e.success),avg_runtime_s=(sum(runtimes)/len(runtimes) if runtimes else 0),p95_runtime_s=percentile(runtimes,.95),
        cpu_hours=sum(float(e.cpu_seconds or 0) for e in calc)/3600.0,project_bytes=project_bytes,project_count=len(projects),daily=sorted(daily.items()),app_counts=app_counts,tier_counts=tier_counts,country_counts=country_counts,capacity=capacity)


@auth_bp.get("/admin/projects/<int:revision_id>/json")
@admin_required
def admin_project_json(revision_id: int):
    row, family = _project_owner_row(revision_id)
    if not row or not family:
        abort(404)
    owner = db.session.get(User, family.owner_user_id)
    try:
        snapshot = json.loads(row.snapshot_json)
    except json.JSONDecodeError:
        snapshot = {"_raw": row.snapshot_json}
    audit(
        "admin_project_inspected",
        user=owner,
        actor=current_user,
        detail=f"project={row.visible_id}; revision_id={row.id}; read_only=true",
    )
    db.session.commit()
    return jsonify({
        "project": _project_meta(row, family),
        "owner": {"id": owner.id, "name": owner.full_name, "email": owner.email, "organization": owner.organization} if owner else None,
        "snapshot": snapshot,
    })


def _register_cli(app) -> None:
    @app.cli.command("init-db")
    def init_db_command():
        """Create/migrate authentication tables and seed suite entitlements."""
        db.create_all()
        _ensure_schema_additions()
        users = db.session.scalars(select(User)).all()
        for user in users:
            ensure_default_entitlements(user)
        _backfill_login_addresses()
        db.session.commit()
        click.echo(f"Total Water Design Suite authentication/project tables are ready; {len(users)} user entitlement set(s) verified.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt="Full name")
    @click.option("--tier", type=click.Choice(["entry", "silver", "gold", "platinum"]), default="platinum")
    def create_admin_command(email: str, name: str, tier: str):
        """Create or promote the first administrator account."""
        email = _normalise_email(email)
        if not _valid_email(email):
            raise click.ClickException("Invalid email address.")
        password = getpass.getpass("Password (minimum 12 characters): ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise click.ClickException("Passwords do not match.")
        errors = validate_password(password, email)
        if errors:
            raise click.ClickException(" ".join(errors))
        user = db.session.scalar(select(User).where(func.lower(User.email) == email))
        if not user:
            user = User(email=email, full_name=name.strip()[:160], organization="", password_hash="")
            db.session.add(user)
        user.full_name = name.strip()[:160]
        user.role = "admin"
        user.status = "active"
        user.licensed_tier = normalize_tier(tier, "platinum")
        user.approved_at = user.approved_at or _utcnow()
        user.set_password(password)
        db.session.flush()
        entitlements = ensure_default_entitlements(user, flush=True)
        entitlements["ro"].enabled = True
        entitlements["ro"].tier = user.licensed_tier
        db.session.commit()
        click.echo(f"Administrator ready: {user.email} ({user.licensed_tier.title()})")

    @app.cli.command("set-user-password")
    @click.argument("email")
    def set_user_password_command(email: str):
        """Set a password from the server console without exposing plaintext."""
        user = db.session.scalar(select(User).where(func.lower(User.email) == _normalise_email(email)))
        if not user:
            raise click.ClickException("User not found.")
        password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise click.ClickException("Passwords do not match.")
        errors = validate_password(password, user.email)
        if errors:
            raise click.ClickException(" ".join(errors))
        user.set_password(password)
        user.failed_login_count = 0
        user.locked_until = None
        db.session.commit()
        click.echo(f"Password updated for {user.email}.")

    @app.cli.command("list-users")
    def list_users_command():
        """List account status, role and licensed tier."""
        rows = db.session.scalars(select(User).order_by(User.id)).all()
        for user in rows:
            click.echo(f"{user.id:4d}  {user.email:40s}  {user.status:9s}  {user.role:5s}  {user.licensed_tier}")


def init_auth(app) -> None:
    deployment_mode = str(os.getenv("TOTALRO_DEPLOYMENT_MODE", "desktop") or "desktop").strip().lower()
    server_mode = deployment_mode in {"server", "aws", "production"}
    auth_enabled = _bool_env("TOTALRO_AUTH_ENABLED", server_mode)
    secret = os.getenv("TOTALRO_SECRET_KEY") or os.getenv("SECRET_KEY")
    if auth_enabled and server_mode and (not secret or len(secret) < 32):
        raise RuntimeError(
            "TOTALRO_SECRET_KEY must be set to at least 32 random characters before starting the authenticated server."
        )
    if not secret:
        # Desktop/local mode only. The random key prevents a reusable weak default.
        secret = secrets.token_urlsafe(48)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db_url = os.getenv("TOTALRO_DATABASE_URL") or os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]
    if not db_url:
        db_path = Path(app.instance_path) / "totalrodesign.db"
        db_url = f"sqlite:///{db_path.as_posix()}"

    app.config.update(
        SECRET_KEY=secret,
        AUTH_ENABLED=auth_enabled,
        DEPLOYMENT_MODE=deployment_mode,
        SQLALCHEMY_DATABASE_URI=db_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_NAME="totalro_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=_bool_env("TOTALRO_COOKIE_SECURE", server_mode),
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=_bool_env("TOTALRO_COOKIE_SECURE", server_mode),
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_DURATION=timedelta(days=int(os.getenv("TOTALRO_REMEMBER_DAYS", "14") or 14)),
        REMEMBER_COOKIE_REFRESH_EACH_REQUEST=False,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.getenv("TOTALRO_SESSION_HOURS", "8") or 8)),
        WTF_CSRF_ENABLED=_bool_env("TOTALRO_CSRF_ENABLED", auth_enabled),
        WTF_CSRF_TIME_LIMIT=int(os.getenv("TOTALRO_CSRF_SECONDS", "28800") or 28800),
        REGISTRATION_ENABLED=_bool_env("TOTALRO_REGISTRATION_ENABLED", True),
        LOGIN_IP_LIMIT=int(os.getenv("TOTALRO_LOGIN_IP_LIMIT", "20") or 20),
        LOGIN_IP_WINDOW_SECONDS=int(os.getenv("TOTALRO_LOGIN_IP_WINDOW_SECONDS", "900") or 900),
        REGISTRATION_IP_LIMIT=int(os.getenv("TOTALRO_REGISTRATION_IP_LIMIT", "5") or 5),
        REGISTRATION_IP_WINDOW_SECONDS=int(os.getenv("TOTALRO_REGISTRATION_IP_WINDOW_SECONDS", "3600") or 3600),
        PASSWORD_RESET_IP_LIMIT=int(os.getenv("TOTALRO_PASSWORD_RESET_IP_LIMIT", "5") or 5),
        PASSWORD_RESET_IP_WINDOW_SECONDS=int(os.getenv("TOTALRO_PASSWORD_RESET_IP_WINDOW_SECONDS", "3600") or 3600),
        PASSWORD_RESET_MAX_AGE=int(os.getenv("TOTALRO_PASSWORD_RESET_SECONDS", "3600") or 3600),
        LOGIN_FAILURE_LIMIT=int(os.getenv("TOTALRO_LOGIN_FAILURE_LIMIT", "5") or 5),
        LOGIN_LOCK_MINUTES=int(os.getenv("TOTALRO_LOGIN_LOCK_MINUTES", "15") or 15),
        MAX_CONTENT_LENGTH=int(os.getenv("TOTALRO_MAX_CONTENT_LENGTH", str(40 * 1024 * 1024))),
        FOUNDER_NAME=os.getenv("TWDS_FOUNDER_NAME","Jerry Ross-Sisniega"),
        FOUNDER_TITLE=os.getenv("TWDS_FOUNDER_TITLE","CEO and Founder"),
        FOUNDER_EMAIL=os.getenv("TWDS_FOUNDER_EMAIL","admin@totalrodesign.com"),
        PREFERRED_URL_SCHEME="https" if server_mode else "http",
    )
    trusted_hosts = [x.strip() for x in os.getenv("TOTALRO_TRUSTED_HOSTS", "").split(",") if x.strip()]
    if trusted_hosts:
        app.config["TRUSTED_HOSTS"] = trusted_hosts

    if server_mode:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Sign in to continue to the Total Water Design Suite."
    login_manager.session_protection = "strong"
    csrf.init_app(app)
    app.register_blueprint(auth_bp)
    _register_cli(app)

    @app.before_request
    def _protect_application():
        if not app.config.get("AUTH_ENABLED", False):
            return None
        endpoint = request.endpoint or ""
        if endpoint == "static" or endpoint.startswith("auth.") or endpoint in {"healthz", "index", "suite_catalog_api"}:
            return None
        if not current_user.is_authenticated:
            return unauthorized()
        if current_user.status != "active":
            logout_user()
            session.clear()
            return unauthorized()
        if current_user.terms_accepted_at is None:
            return redirect(url_for("auth.accept_terms", next=request.full_path if request.method == "GET" else url_for("suite_dashboard")))
        return None

    @app.context_processor
    def _auth_template_context():
        return {
            "auth_enabled": bool(app.config.get("AUTH_ENABLED", False)),
            "deployment_mode": app.config.get("DEPLOYMENT_MODE", "desktop"),
            "suite_name": SUITE_NAME,
            "suite_products": product_catalog(),
            "country_choices": COUNTRIES,
        }

    @app.errorhandler(CSRFError)
    def _csrf_error(exc):
        if request.path.startswith("/api/"):
            return jsonify({
                "error": "Security token missing or expired. Reload the page and try again.",
                "error_type": "CSRFError",
            }), 400
        return render_template("auth/csrf_error.html", reason=exc.description), 400

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'self'; "
            "form-action 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self';",
        )
        if _bool_env("TOTALRO_HSTS_ENABLED", False) and request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        if auth_enabled:
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    if _bool_env("TOTALRO_AUTO_CREATE_DB", True):
        with app.app_context():
            db.create_all()
            _ensure_schema_additions()
            users = db.session.scalars(select(User)).all()
            for user in users:
                ensure_default_entitlements(user)
            _backfill_login_addresses()
            db.session.commit()
