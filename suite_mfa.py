"""Mandatory Suite-wide multi-factor authentication.

The first implemented factor is RFC 6238 TOTP. The persistence model separates
an MFA profile from factor credentials so WebAuthn/passkey credentials can be
added later without redesigning account state. TOTP secrets are encrypted at
rest with Fernet; recovery codes are stored only as scrypt hashes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone
from functools import wraps

import click
import pyotp
from cryptography.fernet import Fernet, InvalidToken
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy import UniqueConstraint, select
from werkzeug.security import check_password_hash, generate_password_hash

from auth import User, admin_required, audit, db, _rate_limited
from suite_mfa_qr import qr_svg_data_uri

mfa_bp = Blueprint("suite_mfa", __name__)

MFA_SESSION_USER = "twds_mfa_verified_user_id"
MFA_SESSION_AT = "twds_mfa_verified_at"
MFA_PASSWORD_AUTH_USER = "twds_password_authenticated_user_id"
MFA_PASSWORD_AUTH_AT = "twds_password_authenticated_at"
MFA_PENDING_USER = "twds_mfa_pending_user_id"
MFA_PENDING_NEXT = "twds_mfa_pending_next"
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MfaProfile(db.Model):
    __tablename__ = "suite_mfa_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    enabled = db.Column(db.Boolean, nullable=False, default=False, index=True)
    primary_method = db.Column(db.String(24), nullable=False, default="totp")
    recovery_hashes_json = db.Column(db.Text, nullable=False, default="[]")
    last_totp_counter = db.Column(db.BigInteger, nullable=True)
    enrolled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    recovery_codes_generated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reset_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reset_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class MfaCredential(db.Model):
    """Extensible second-factor credential record.

    TOTP uses encrypted_secret. Future WebAuthn credentials can use credential_id
    and public_data_json while keeping private key material outside the server.
    """
    __tablename__ = "suite_mfa_credentials"
    __table_args__ = (UniqueConstraint("profile_id", "method", "credential_id", name="uq_mfa_profile_method_credential"),)
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("suite_mfa_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    method = db.Column(db.String(24), nullable=False, index=True)
    label = db.Column(db.String(120), nullable=False, default="Authenticator")
    encrypted_secret = db.Column(db.Text, nullable=False, default="")
    credential_id = db.Column(db.String(500), nullable=False, default="")
    public_data_json = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    last_used_at = db.Column(db.DateTime(timezone=True), nullable=True)


def _mfa_required() -> bool:
    raw = os.getenv("TWDS_MFA_REQUIRED")
    if raw is None:
        return bool(current_app.config.get("AUTH_ENABLED", False))
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _derived_fernet_key() -> bytes:
    secret = str(current_app.config.get("SECRET_KEY") or "")
    digest = hashlib.sha256(("twds:mfa:fernet:v1:" + secret).encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet_candidates() -> list[Fernet]:
    configured = str(os.getenv("TWDS_MFA_ENCRYPTION_KEY") or "").strip()
    keys: list[bytes] = []
    if configured:
        keys.append(configured.encode("ascii"))
    derived = _derived_fernet_key()
    if derived not in keys:
        keys.append(derived)
    return [Fernet(key) for key in keys]


def _encrypt_secret(secret: str) -> str:
    return _fernet_candidates()[0].encrypt(secret.encode("utf-8")).decode("ascii")


def _decrypt_secret(ciphertext: str) -> str:
    encoded = str(ciphertext).encode("ascii")
    for fernet in _fernet_candidates():
        try:
            return fernet.decrypt(encoded).decode("utf-8")
        except InvalidToken:
            continue
    raise RuntimeError("MFA credential cannot be decrypted with the configured Suite keys.")


def _profile(user_id: int, create: bool = False) -> MfaProfile | None:
    row = db.session.scalar(select(MfaProfile).where(MfaProfile.user_id == int(user_id)))
    if not row and create:
        row = MfaProfile(user_id=int(user_id), enabled=False, primary_method="totp")
        db.session.add(row)
        db.session.flush()
    return row


def _totp_credential(profile: MfaProfile, create: bool = False) -> MfaCredential | None:
    row = db.session.scalar(select(MfaCredential).where(
        MfaCredential.profile_id == profile.id,
        MfaCredential.method == "totp",
    ))
    if not row and create:
        row = MfaCredential(
            profile_id=profile.id,
            method="totp",
            label="Authenticator app",
            encrypted_secret=_encrypt_secret(pyotp.random_base32()),
            credential_id="primary",
        )
        db.session.add(row)
        db.session.flush()
    return row


def _enrollment_ttl_seconds() -> int:
    try:
        value = int(os.getenv("TWDS_MFA_ENROLLMENT_TTL_SECONDS", "1800") or 1800)
    except (TypeError, ValueError):
        value = 1800
    return max(300, min(value, 86400))


def _pending_totp_expired(credential: MfaCredential | None) -> bool:
    if not credential or not credential.created_at:
        return False
    created_at = credential.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return (_utcnow() - created_at).total_seconds() >= _enrollment_ttl_seconds()


def _replace_pending_totp(profile: MfaProfile) -> MfaCredential:
    if profile.enabled:
        raise RuntimeError("An enabled MFA credential cannot be replaced by the enrollment flow.")

    # A pending credential is not yet trusted as an enrolled factor. Rotate its
    # encrypted secret in place instead of deleting/reinserting the ORM row.
    # This preserves the durable row identity while immediately invalidating the
    # previously rendered QR/setup key and avoids primary-key reuse ambiguity on
    # SQLite without changing PostgreSQL schema or enrolled-user credentials.
    credential = _totp_credential(profile, create=False)
    if credential is None:
        credential = _totp_credential(profile, create=True)
    else:
        credential.encrypted_secret = _encrypt_secret(pyotp.random_base32())
        credential.label = "Authenticator app"
        credential.credential_id = "primary"
        credential.public_data_json = "{}"
        credential.created_at = _utcnow()
        credential.last_used_at = None

    profile.last_totp_counter = None
    profile.recovery_hashes_json = "[]"
    profile.recovery_codes_generated_at = None
    profile.updated_at = _utcnow()
    db.session.flush()
    return credential


def _provisioning_uri(secret: str, account_name: str, issuer: str) -> str:
    return pyotp.TOTP(secret, digits=6, interval=30).provisioning_uri(
        name=str(account_name),
        issuer_name=str(issuer),
    )


def _format_setup_key(secret: str) -> str:
    value = str(secret or "")
    return " ".join(value[index:index + 4] for index in range(0, len(value), 4))


def _normalize_code(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _verify_totp(profile: MfaProfile, code: str) -> bool:
    credential = _totp_credential(profile, create=False)
    if not credential or not credential.encrypted_secret:
        return False
    normalized = _normalize_code(code)
    if len(normalized) != 6 or not normalized.isdigit():
        return False
    totp = pyotp.TOTP(_decrypt_secret(credential.encrypted_secret), interval=30)
    current_counter = int(time.time() // 30)
    last_counter = int(profile.last_totp_counter) if profile.last_totp_counter is not None else -1
    for counter in (current_counter - 1, current_counter, current_counter + 1):
        if counter <= last_counter:
            continue
        if secrets.compare_digest(totp.at(counter * 30), normalized):
            profile.last_totp_counter = counter
            credential.last_used_at = _utcnow()
            return True
    return False


def _recovery_codes(count: int = 10) -> list[str]:
    result = []
    for _ in range(count):
        raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(12))
        result.append(f"{raw[:4]}-{raw[4:8]}-{raw[8:]}")
    return result


def _set_recovery_codes(profile: MfaProfile) -> list[str]:
    codes = _recovery_codes()
    profile.recovery_hashes_json = json.dumps(
        [generate_password_hash(_normalize_code(code), method="scrypt") for code in codes],
        separators=(",", ":"),
    )
    profile.recovery_codes_generated_at = _utcnow()
    return codes


def _verify_recovery(profile: MfaProfile, code: str) -> bool:
    normalized = _normalize_code(code)
    if len(normalized) != 12:
        return False
    try:
        hashes = list(json.loads(profile.recovery_hashes_json or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        hashes = []
    for index, digest in enumerate(hashes):
        if check_password_hash(str(digest), normalized):
            del hashes[index]
            profile.recovery_hashes_json = json.dumps(hashes, separators=(",", ":"))
            return True
    return False


def _pending_user() -> User | None:
    uid = session.get(MFA_PENDING_USER)
    return db.session.get(User, int(uid)) if uid else None


def _safe_target(value: object, default: str = "/suite") -> str:
    target = str(value or default)
    return target if target.startswith("/") and not target.startswith("//") else default


def _next_url(default: str = "/suite") -> str:
    return _safe_target(session.get(MFA_PENDING_NEXT) or request.args.get("next"), default)


def _mark_verified(user: User) -> None:
    session[MFA_SESSION_USER] = int(user.id)
    session[MFA_SESSION_AT] = int(time.time())
    session.pop(MFA_PENDING_USER, None)
    session.pop(MFA_PENDING_NEXT, None)
    session.permanent = True


def _password_reauth_satisfied(profile: MfaProfile, user: User) -> bool:
    if not profile.reset_at:
        return True
    reset_at = profile.reset_at
    if reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=timezone.utc)
    return bool(
        int(session.get(MFA_PASSWORD_AUTH_USER) or 0) == int(user.id)
        and float(session.get(MFA_PASSWORD_AUTH_AT) or 0.0) >= reset_at.timestamp()
    )


def _force_password_reauth(user: User):
    target = request.full_path if request.method == "GET" else "/suite"
    session[MFA_PENDING_NEXT] = _safe_target(target)
    logout_user()
    session.pop(MFA_SESSION_USER, None)
    session.pop(MFA_SESSION_AT, None)
    return redirect(url_for("auth.login", next=url_for("suite_mfa.setup")))


def _challenge_response(user: User):
    target = request.full_path if request.method == "GET" else "/suite"
    session[MFA_PENDING_USER] = int(user.id)
    session[MFA_PENDING_NEXT] = _safe_target(target)
    logout_user()
    if request.path.startswith("/api/"):
        return jsonify({
            "error": "Two-step verification required.",
            "error_type": "MFARequired",
            "mfa_url": url_for("suite_mfa.challenge"),
        }), 428
    return redirect(url_for("suite_mfa.challenge"))


def _enrollment_response():
    target = request.full_path if request.method == "GET" else "/suite"
    session[MFA_PENDING_NEXT] = _safe_target(target)
    if request.path.startswith("/api/"):
        return jsonify({
            "error": "Two-step verification enrollment is required before continuing.",
            "error_type": "MFAEnrollmentRequired",
            "mfa_url": url_for("suite_mfa.setup"),
        }), 428
    return redirect(url_for("suite_mfa.setup"))


def _make_auth_guard_mfa_aware(app) -> None:
    """Allow pending MFA routes through the older global auth gate.

    ``auth.init_auth`` is installed before Suite MFA and protects all non-auth
    endpoints. During a second-factor challenge Suite MFA intentionally logs the
    password-authenticated session out and keeps only a pending MFA user in the
    signed session. The global guard must therefore defer Suite MFA endpoints to
    their own route-level checks instead of redirecting them back to login.
    """
    functions = app.before_request_funcs.get(None, [])
    for index, function in enumerate(functions):
        if getattr(function, "__name__", "") != "_protect_application":
            continue
        if getattr(function, "_twds_mfa_aware", False):
            return
        original = function

        @wraps(original)
        def mfa_aware_auth_guard(*args, __original=original, **kwargs):
            endpoint = request.endpoint or ""
            if endpoint.startswith("suite_mfa."):
                return None
            return __original(*args, **kwargs)

        mfa_aware_auth_guard._twds_mfa_aware = True
        functions[index] = mfa_aware_auth_guard
        return
    raise RuntimeError("Suite MFA could not locate the Suite authentication request guard.")


def _install_enforcement(app) -> None:
    @app.before_request
    def _enforce_suite_mfa():
        if not app.config.get("AUTH_ENABLED", False) or not _mfa_required():
            return None
        endpoint = request.endpoint or ""
        if endpoint == "static":
            return None
        # Only routes required to complete the second-factor ceremony may run
        # before the session is MFA-verified. Account/admin security management
        # routes are intentionally NOT exempt and must pass the same enforcement
        # gate as every other protected Suite surface.
        if endpoint in {
            "suite_mfa.setup",
            "suite_mfa.restart_setup",
            "suite_mfa.challenge",
        }:
            return None
        if endpoint in {
            "auth.login", "auth.logout", "auth.forgot_password", "auth.reset_password",
            "auth.register", "auth.accept_terms",
        }:
            if endpoint != "auth.accept_terms" or not current_user.is_authenticated:
                return None
        if not current_user.is_authenticated:
            return None
        profile = _profile(current_user.id, create=False)
        if not profile or not profile.enabled:
            if profile and profile.reset_at and not _password_reauth_satisfied(profile, current_user):
                return _force_password_reauth(current_user)
            return _enrollment_response()
        if int(session.get(MFA_SESSION_USER) or 0) != int(current_user.id):
            return _challenge_response(current_user)
        return None

    @app.after_request
    def _remember_successful_password_auth(response):
        # auth.login performs the existing password validation. Record only a
        # successful redirect with an authenticated user, never a failed POST.
        # Preserve sub-second precision so an MFA reset later in the same second
        # can never mistake a pre-reset password authentication for a fresh one.
        if (
            request.endpoint == "auth.login"
            and request.method == "POST"
            and current_user.is_authenticated
            and 300 <= response.status_code < 400
        ):
            session[MFA_PASSWORD_AUTH_USER] = int(current_user.id)
            session[MFA_PASSWORD_AUTH_AT] = time.time()
        return response


def _rate_limit(bucket: str):
    limit = int(os.getenv("TWDS_MFA_ATTEMPT_LIMIT", "10") or 10)
    window = int(os.getenv("TWDS_MFA_ATTEMPT_WINDOW_SECONDS", "300") or 300)
    limited, retry_after = _rate_limited(bucket, limit, window)
    if not limited:
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Too many verification attempts. Try again later.", "retry_after": retry_after}), 429
    return render_template("auth/rate_limited.html", retry_after=retry_after), 429, {"Retry-After": str(retry_after)}


@mfa_bp.route("/mfa/setup", methods=["GET", "POST"])
def setup():
    user = current_user if current_user.is_authenticated else _pending_user()
    if not user or user.status != "active":
        return redirect(url_for("auth.login"))
    profile = _profile(user.id, create=True)
    if profile.enabled:
        if current_user.is_authenticated:
            return redirect(url_for("suite_mfa.account_security"))
        return redirect(url_for("suite_mfa.challenge"))
    if profile.reset_at and not _password_reauth_satisfied(profile, user):
        if current_user.is_authenticated:
            return _force_password_reauth(user)
        return redirect(url_for("auth.login", next=url_for("suite_mfa.setup")))

    credential = _totp_credential(profile, create=True)
    if _pending_totp_expired(credential):
        credential = _replace_pending_totp(profile)
        audit("mfa_enrollment_secret_rotated", user=user, actor=user, detail="reason=expired")
        db.session.commit()
        if request.method == "POST":
            flash(
                "This setup session is no longer valid. A new QR code has been generated. "
                "Scan it and enter the current 6-digit code from your authenticator app.",
                "error",
            )
            return redirect(url_for("suite_mfa.setup"))
        flash("Your previous two-step setup expired. A new QR code and setup key were generated.", "warning")

    secret = _decrypt_secret(credential.encrypted_secret)
    issuer = str(os.getenv("TWDS_MFA_ISSUER") or "Total Water Design Suite")[:80]
    provisioning_uri = _provisioning_uri(secret, user.email, issuer)
    qr_data_uri = qr_svg_data_uri(provisioning_uri)

    if request.method == "POST":
        limited = _rate_limit("mfa-setup")
        if limited:
            return limited
        if not _verify_totp(profile, request.form.get("code") or ""):
            audit("mfa_enrollment_failed", user=user, actor=user, detail="Invalid authenticator code")
            db.session.commit()
            flash(
                "The verification code is incorrect. Enter the current 6-digit code from your authenticator app.",
                "error",
            )
        else:
            profile.enabled = True
            profile.primary_method = "totp"
            profile.enrolled_at = _utcnow()
            profile.reset_at = None
            profile.reset_by_user_id = None
            recovery_codes = _set_recovery_codes(profile)
            audit("mfa_enrolled", user=user, actor=user, detail="method=totp")
            db.session.commit()
            target = _next_url()
            if not current_user.is_authenticated:
                login_user(user, remember=False, fresh=True)
            _mark_verified(user)
            return render_template("auth/mfa_recovery_codes.html", recovery_codes=recovery_codes, next_url=target)
    else:
        # Enrollment spans multiple HTTP requests. Persist the encrypted secret
        # before rendering the provisioning URI so the submitted TOTP is checked
        # against the same credential on the subsequent POST.
        db.session.commit()

    return render_template(
        "auth/mfa_setup.html",
        account_name=user.email,
        secret=secret,
        secret_display=_format_setup_key(secret),
        provisioning_uri=provisioning_uri,
        issuer=issuer,
        qr_data_uri=qr_data_uri,
        enrollment_ttl_minutes=max(1, _enrollment_ttl_seconds() // 60),
    )


@mfa_bp.post("/mfa/setup/restart")
def restart_setup():
    if not current_user.is_authenticated or current_user.status != "active":
        abort(401)
    profile = _profile(current_user.id, create=True)
    if profile.enabled:
        flash("Two-step verification is already enabled for this account.", "error")
        return redirect(url_for("suite_mfa.account_security"))
    if profile.reset_at and not _password_reauth_satisfied(profile, current_user):
        return _force_password_reauth(current_user)

    _replace_pending_totp(profile)
    audit(
        "mfa_enrollment_restarted",
        user=current_user,
        actor=current_user,
        detail="Pending enrollment secret rotated",
    )
    db.session.commit()
    flash(
        "A new QR code and setup key were generated. The previous enrollment QR code and setup key will no longer work.",
        "success",
    )
    return redirect(url_for("suite_mfa.setup"))


@mfa_bp.route("/mfa/challenge", methods=["GET", "POST"])
def challenge():
    user = _pending_user()
    if not user or user.status != "active":
        session.pop(MFA_PENDING_USER, None)
        return redirect(url_for("auth.login"))
    profile = _profile(user.id, create=False)
    if not profile or not profile.enabled:
        return redirect(url_for("suite_mfa.setup"))
    if request.method == "POST":
        limited = _rate_limit("mfa-challenge")
        if limited:
            return limited
        code = request.form.get("code") or ""
        used_recovery = False
        valid = _verify_totp(profile, code)
        if not valid:
            valid = _verify_recovery(profile, code)
            used_recovery = valid
        if valid:
            target = _next_url()
            login_user(user, remember=False, fresh=True)
            _mark_verified(user)
            audit("mfa_verified", user=user, actor=user, detail="method=recovery" if used_recovery else "method=totp")
            db.session.commit()
            return redirect(target)
        audit("mfa_challenge_failed", user=user, detail="Invalid second factor")
        db.session.commit()
        flash("Verification failed. Enter the current authenticator code or an unused recovery code.", "error")
    return render_template("auth/mfa_challenge.html", user=user)


@mfa_bp.get("/account/security")
def account_security():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    profile = _profile(current_user.id, create=False)
    recovery_count = 0
    if profile:
        try:
            recovery_count = len(json.loads(profile.recovery_hashes_json or "[]"))
        except Exception:
            recovery_count = 0
    return render_template("auth/mfa_account.html", profile=profile, recovery_count=recovery_count)


@mfa_bp.post("/account/security/recovery-codes")
def regenerate_recovery_codes():
    if not current_user.is_authenticated:
        abort(401)
    limited = _rate_limit("mfa-recovery-regenerate")
    if limited:
        return limited
    profile = _profile(current_user.id, create=False)
    if not profile or not profile.enabled or not _verify_totp(profile, request.form.get("code") or ""):
        flash("Enter a valid current authenticator code before replacing recovery codes.", "error")
        return redirect(url_for("suite_mfa.account_security"))
    recovery_codes = _set_recovery_codes(profile)
    audit("mfa_recovery_codes_regenerated", user=current_user, actor=current_user)
    db.session.commit()
    return render_template("auth/mfa_recovery_codes.html", recovery_codes=recovery_codes, next_url=url_for("suite_mfa.account_security"))


@mfa_bp.get("/admin/security")
@admin_required
def admin_security():
    users = db.session.scalars(select(User).order_by(User.email)).all()
    profiles = {row.user_id: row for row in db.session.scalars(select(MfaProfile)).all()}
    return render_template("auth/admin_security.html", users=users, profiles=profiles)


@mfa_bp.post("/admin/security/users/<int:user_id>/reset-mfa")
@admin_required
def admin_reset_mfa(user_id: int):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("For security, an administrator cannot reset their own MFA from the web console. Use recovery codes or the server recovery command.", "error")
        return redirect(url_for("suite_mfa.admin_security"))
    profile = _profile(user.id, create=True)
    db.session.query(MfaCredential).filter(MfaCredential.profile_id == profile.id).delete(synchronize_session=False)
    profile.enabled = False
    profile.recovery_hashes_json = "[]"
    profile.last_totp_counter = None
    profile.enrolled_at = None
    profile.reset_at = _utcnow()
    profile.reset_by_user_id = current_user.id
    # Bump reset-token version as defense in depth. Session revocation for MFA
    # recovery is enforced independently by comparing password-auth time to reset_at.
    user.password_version = int(user.password_version or 0) + 1
    audit("mfa_admin_reset", user=user, actor=current_user, detail="Password reauthentication and fresh MFA enrollment required")
    db.session.commit()
    flash(f"MFA reset for {user.email}. The user must sign in with their password and enroll a new factor.", "success")
    return redirect(url_for("suite_mfa.admin_security"))


def _register_cli(app) -> None:
    @app.cli.command("reset-user-mfa")
    @click.argument("email")
    def reset_user_mfa(email: str):
        """Emergency server-console MFA reset, intended for controlled recovery."""
        user = db.session.scalar(select(User).where(User.email == str(email).strip().lower()))
        if not user:
            raise click.ClickException("User not found.")
        profile = _profile(user.id, create=True)
        db.session.query(MfaCredential).filter(MfaCredential.profile_id == profile.id).delete(synchronize_session=False)
        profile.enabled = False
        profile.recovery_hashes_json = "[]"
        profile.last_totp_counter = None
        profile.enrolled_at = None
        profile.reset_at = _utcnow()
        profile.reset_by_user_id = None
        user.password_version = int(user.password_version or 0) + 1
        audit("mfa_cli_reset", user=user, detail="Controlled console recovery; password reauthentication required")
        db.session.commit()
        click.echo(f"MFA reset for {user.email}; password sign-in and re-enrollment are required.")


def init_suite_mfa(app) -> None:
    if "suite_mfa" in app.blueprints:
        return
    with app.app_context():
        db.create_all()
    app.register_blueprint(mfa_bp)
    _make_auth_guard_mfa_aware(app)
    _install_enforcement(app)
    _register_cli(app)
