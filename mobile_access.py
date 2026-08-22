"""Mobile-app access policy for hosted Total Water Design Suite.

The policy is intentionally disabled by default. When enabled, authenticated
engineering routes remain available from desktop browsers and from verified
TWDS native-app sessions, while phone browsers receive a mobile-app-required
response. Native app verification is pluggable so Apple App Attest and Google
Play Integrity can be integrated without changing engineering code.
"""
from __future__ import annotations

import os
import re
import time
from typing import Callable

from flask import Blueprint, current_app, jsonify, make_response, render_template, request, session
from flask_login import current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from auth import csrf, db, record_telemetry


mobile_access_bp = Blueprint("mobile_access", __name__)

MOBILE_APP_COOKIE = "twds_mobile_app"
_MOBILE_SESSION_SALT = "twds-mobile-app-session-v1"

_PHONE_UA_RE = re.compile(
    r"iphone|ipod|windows phone|blackberry|bb10|opera mini|opera mobi|iemobile|"
    r"android[^;)]*mobile|mobile safari|webos|fennec",
    re.I,
)

_PROTECTED_EXACT = {"/suite", "/ro"}
_PROTECTED_PREFIXES = (
    "/ro/",
    "/report/",
    "/api/",
    "/bio",
    "/zld",
    "/pretreatment",
    "/balance",
    "/economics",
    "/system-integration",
)
_MOBILE_API_PREFIX = "/api/mobile/"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def classify_request_device(user_agent: str = "", sec_ch_ua_mobile: str = "") -> str:
    """Return phone or non_phone using server-visible browser hints.

    This is a commercial routing control, not a cryptographic device proof.
    The official native app is verified separately through attestation.
    """
    hint = str(sec_ch_ua_mobile or "").strip()
    if hint == "?1":
        return "phone"
    ua = str(user_agent or "")
    if _PHONE_UA_RE.search(ua):
        return "phone"
    return "non_phone"


def request_device_class() -> str:
    return classify_request_device(
        request.headers.get("User-Agent", ""),
        request.headers.get("Sec-CH-UA-Mobile", ""),
    )


def is_protected_engineering_path(path: str) -> bool:
    path = str(path or "/")
    if path.startswith(_MOBILE_API_PREFIX):
        return False
    if path == "/api/suite/catalog":
        return False
    if path in _PROTECTED_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _PROTECTED_PREFIXES)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_MOBILE_SESSION_SALT)


def _store_urls() -> dict[str, str]:
    return {
        "ios": str(current_app.config.get("MOBILE_APP_IOS_STORE_URL") or ""),
        "android": str(current_app.config.get("MOBILE_APP_ANDROID_STORE_URL") or ""),
    }


def _session_ttl_seconds() -> int:
    return max(900, int(current_app.config.get("MOBILE_APP_SESSION_SECONDS", 28800) or 28800))


def verified_app_claims() -> dict | None:
    if not current_user.is_authenticated:
        return None
    token = request.cookies.get(MOBILE_APP_COOKIE, "")
    if not token:
        return None
    try:
        claims = _serializer().loads(token, max_age=_session_ttl_seconds())
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(claims, dict):
        return None
    if int(claims.get("uid", -1)) != int(current_user.id):
        return None
    if claims.get("platform") not in {"ios", "android"}:
        return None
    return claims


def access_channel() -> str:
    claims = verified_app_claims()
    if claims:
        return f"{claims['platform']}_app"
    if request_device_class() == "phone":
        return "mobile_web"
    return "desktop_web"


def _attestation_verifiers() -> dict[str, Callable]:
    return dict(current_app.extensions.get("twds_mobile_attestation_verifiers") or {})


def _verify_attestation(platform: str, payload: dict) -> tuple[bool, dict, str]:
    verifier = _attestation_verifiers().get(platform)
    if not callable(verifier):
        return False, {}, "attestation_verifier_not_configured"
    try:
        result = verifier(payload)
    except Exception:
        current_app.logger.exception("TWDS mobile attestation verifier failed for %s", platform)
        return False, {}, "attestation_verification_failed"
    if result is True:
        return True, {}, "verified"
    if isinstance(result, dict) and bool(result.get("valid")):
        safe = {
            "device_key_id": str(result.get("device_key_id") or "")[:160],
            "app_id": str(result.get("app_id") or "")[:160],
            "integrity_level": str(result.get("integrity_level") or "")[:80],
        }
        return True, safe, "verified"
    return False, {}, "attestation_rejected"


def _record_channel_event(event_type: str, channel: str, *, success: bool = True, status: str = "") -> None:
    if not current_user.is_authenticated:
        return
    try:
        record_telemetry(
            event_type,
            application="suite",
            module=str(channel)[:80],
            success=success,
            metadata={"status": status or ("ok" if success else "blocked")},
            user=current_user,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to record TWDS mobile access telemetry")


@mobile_access_bp.get("/api/mobile/status")
def mobile_status():
    claims = verified_app_claims()
    return jsonify({
        "require_mobile_app_on_phone": bool(current_app.config.get("REQUIRE_MOBILE_APP_ON_PHONE", False)),
        "device_class": request_device_class(),
        "access_channel": access_channel(),
        "verified_app": ({
            "platform": claims.get("platform"),
            "app_version": claims.get("app_version"),
            "verified_at": claims.get("verified_at"),
        } if claims else None),
        "store_urls": _store_urls(),
    })


@mobile_access_bp.post("/api/mobile/session/verify")
@csrf.exempt
def verify_mobile_app_session():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required.", "error_type": "AuthenticationRequired"}), 401

    payload = request.get_json(silent=True) or {}
    platform = str(payload.get("platform") or "").strip().lower()
    app_version = str(payload.get("app_version") or "").strip()[:40]
    if platform not in {"ios", "android"}:
        return jsonify({"error": "platform must be ios or android"}), 400
    if not app_version:
        return jsonify({"error": "app_version is required"}), 400

    valid, evidence, reason = _verify_attestation(platform, payload)
    if not valid:
        _record_channel_event("mobile_app_attestation_failed", f"{platform}_app", success=False, status=reason)
        status = 503 if reason == "attestation_verifier_not_configured" else 403
        return jsonify({
            "error": "Official mobile app verification is not available." if status == 503 else "Official mobile app verification failed.",
            "error_type": "MobileAppVerificationError",
            "reason": reason,
        }), status

    now = int(time.time())
    claims = {
        "uid": int(current_user.id),
        "platform": platform,
        "app_version": app_version,
        "verified_at": now,
        "device_key_id": evidence.get("device_key_id", ""),
        "app_id": evidence.get("app_id", ""),
    }
    token = _serializer().dumps(claims)
    response = jsonify({
        "ok": True,
        "platform": platform,
        "app_version": app_version,
        "expires_in_seconds": _session_ttl_seconds(),
        "access_channel": f"{platform}_app",
    })
    response.set_cookie(
        MOBILE_APP_COOKIE,
        token,
        max_age=_session_ttl_seconds(),
        httponly=True,
        secure=bool(current_app.config.get("SESSION_COOKIE_SECURE", False)),
        samesite="Lax",
        path="/",
    )
    session["twds_access_channel"] = f"{platform}_app"
    _record_channel_event("mobile_app_verified", f"{platform}_app", success=True, status="verified")
    return response


@mobile_access_bp.post("/api/mobile/session/revoke")
@csrf.exempt
def revoke_mobile_app_session():
    response = jsonify({"ok": True})
    response.delete_cookie(MOBILE_APP_COOKIE, path="/")
    if current_user.is_authenticated:
        _record_channel_event("mobile_app_session_revoked", access_channel(), success=True, status="revoked")
    session.pop("twds_access_channel", None)
    return response


def _mobile_required_response():
    urls = _store_urls()
    _record_channel_event("mobile_web_blocked", "mobile_web", success=False, status="app_required")
    if request.path.startswith("/api/"):
        return jsonify({
            "error": "The Total Water Design Suite mobile app is required on phones.",
            "error_type": "MobileAppRequired",
            "store_urls": urls,
        }), 426
    return make_response(render_template(
        "mobile_app_required.html",
        ios_store_url=urls["ios"],
        android_store_url=urls["android"],
    ), 426)


def init_mobile_access(app, *, verifiers: dict[str, Callable] | None = None) -> None:
    """Register mobile policy after auth has initialized the Flask app.

    Enabling enforcement is deliberately fail-safe: required native platforms
    must have attestation verifiers configured first.
    """
    app.config.update(
        REQUIRE_MOBILE_APP_ON_PHONE=_env_bool("TOTALRO_REQUIRE_MOBILE_APP_ON_PHONE", False),
        MOBILE_APP_IOS_STORE_URL=os.getenv("TOTALRO_IOS_APP_STORE_URL", ""),
        MOBILE_APP_ANDROID_STORE_URL=os.getenv("TOTALRO_ANDROID_PLAY_STORE_URL", ""),
        MOBILE_APP_SESSION_SECONDS=int(os.getenv("TOTALRO_MOBILE_APP_SESSION_SECONDS", "28800") or 28800),
        MOBILE_APP_REQUIRED_PLATFORMS=[
            x.strip().lower() for x in os.getenv("TOTALRO_MOBILE_REQUIRED_PLATFORMS", "ios,android").split(",")
            if x.strip().lower() in {"ios", "android"}
        ],
    )
    app.extensions["twds_mobile_attestation_verifiers"] = dict(verifiers or {})

    if app.config["REQUIRE_MOBILE_APP_ON_PHONE"]:
        missing = [p for p in app.config["MOBILE_APP_REQUIRED_PLATFORMS"] if not callable(app.extensions["twds_mobile_attestation_verifiers"].get(p))]
        if missing:
            raise RuntimeError(
                "Mobile-app enforcement cannot be enabled before attestation verifiers are configured for: "
                + ", ".join(missing)
            )

    app.register_blueprint(mobile_access_bp)

    @app.before_request
    def _enforce_phone_app_policy():
        if not app.config.get("REQUIRE_MOBILE_APP_ON_PHONE", False):
            return None
        if not current_user.is_authenticated:
            return None
        if request.endpoint and request.endpoint.startswith("mobile_access."):
            return None
        if not is_protected_engineering_path(request.path):
            return None

        claims = verified_app_claims()
        if claims:
            session["twds_access_channel"] = f"{claims['platform']}_app"
            return None

        if request_device_class() == "phone":
            session["twds_access_channel"] = "mobile_web"
            return _mobile_required_response()

        if session.get("twds_access_channel") != "desktop_web":
            session["twds_access_channel"] = "desktop_web"
            _record_channel_event("access_channel", "desktop_web", success=True, status="allowed")
        return None
