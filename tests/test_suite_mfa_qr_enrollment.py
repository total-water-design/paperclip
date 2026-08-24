from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import pyotp
import pytest
from cryptography.fernet import Fernet
from flask import Flask
from sqlalchemy import select

import auth
import suite_mfa


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "MFA-QR-Validation-2026!"
USER_EMAIL = "mfa-qr-user@example.test"
ADMIN_EMAIL = "mfa-qr-admin@example.test"


@dataclass
class Harness:
    app: Flask
    user_id: int
    admin_id: int

    def client(self):
        return self.app.test_client()


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.setenv("TOTALRO_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("TOTALRO_AUTH_ENABLED", "1")
    monkeypatch.setenv("TOTALRO_SECRET_KEY", "Q" * 64)
    monkeypatch.setenv("TOTALRO_DATABASE_URL", f"sqlite:///{(tmp_path / 'mfa-qr.db').as_posix()}")
    monkeypatch.setenv("TOTALRO_AUTO_CREATE_DB", "1")
    monkeypatch.setenv("TOTALRO_CSRF_ENABLED", "0")
    monkeypatch.setenv("TOTALRO_COOKIE_SECURE", "0")
    monkeypatch.setenv("TOTALRO_LOGIN_IP_LIMIT", "10000")
    monkeypatch.setenv("TWDS_MFA_REQUIRED", "1")
    monkeypatch.setenv("TWDS_MFA_ISSUER", "Total Water Design Suite")
    monkeypatch.setenv("TWDS_MFA_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("TWDS_MFA_ENROLLMENT_TTL_SECONDS", "1800")
    auth._rate_hits.clear()

    app = Flask(
        "mfa_qr_validation",
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )

    @app.get("/")
    def index():
        return "index"

    @app.get("/suite")
    def suite_dashboard():
        return "suite"

    auth.init_auth(app)
    suite_mfa.init_suite_mfa(app)

    now = datetime.now(timezone.utc)
    with app.app_context():
        user = auth.User(
            email=USER_EMAIL,
            full_name="MFA QR User",
            organization="Validation",
            password_hash="",
            role="user",
            licensed_tier="entry",
            status="active",
            terms_accepted_at=now,
        )
        user.set_password(PASSWORD)
        admin = auth.User(
            email=ADMIN_EMAIL,
            full_name="MFA QR Admin",
            organization="Validation",
            password_hash="",
            role="admin",
            licensed_tier="platinum",
            status="active",
            terms_accepted_at=now,
        )
        admin.set_password(PASSWORD)
        auth.db.session.add_all([user, admin])
        auth.db.session.flush()
        auth.ensure_default_entitlements(user, flush=True)
        auth.ensure_default_entitlements(admin, flush=True)
        auth.db.session.commit()
        result = Harness(app=app, user_id=user.id, admin_id=admin.id)

    yield result

    with app.app_context():
        auth.db.session.remove()
        auth.db.drop_all()
    auth._rate_hits.clear()


def _login(client, email: str):
    return client.post(
        "/login?next=/suite",
        data={"email": email, "password": PASSWORD, "remember": ""},
        follow_redirects=False,
    )


def _begin_setup(harness: Harness, client, user_id: int | None = None):
    user_id = user_id or harness.user_id
    with harness.app.app_context():
        email = auth.db.session.get(auth.User, user_id).email
    assert _login(client, email).status_code == 302
    gate = client.get("/suite", follow_redirects=False)
    assert gate.status_code == 302
    assert "/mfa/setup" in gate.headers.get("Location", "")
    page = client.get("/mfa/setup", follow_redirects=False)
    assert page.status_code == 200
    return page


def _secret(harness: Harness, user_id: int) -> str:
    with harness.app.app_context():
        profile = suite_mfa._profile(user_id, create=False)
        credential = suite_mfa._totp_credential(profile, create=False)
        return suite_mfa._decrypt_secret(credential.encrypted_secret)


def _pre_enroll(harness: Harness, user_id: int):
    with harness.app.app_context():
        profile = suite_mfa._profile(user_id, create=True)
        credential = suite_mfa._totp_credential(profile, create=True)
        profile.enabled = True
        profile.primary_method = "totp"
        profile.enrolled_at = datetime.now(timezone.utc)
        profile.reset_at = None
        profile.last_totp_counter = None
        recovery_codes = suite_mfa._set_recovery_codes(profile)
        secret = suite_mfa._decrypt_secret(credential.encrypted_secret)
        auth.db.session.commit()
        return secret, recovery_codes


def _different_current_codes(old_secret: str, new_secret: str) -> tuple[str, str]:
    """Return distinguishable current codes, rotating the caller's secret if needed.

    A six-digit collision is possible but rare; callers can regenerate a pending
    secret and retry rather than altering the process clock used by Flask sessions.
    """
    return pyotp.TOTP(old_secret).now(), pyotp.TOTP(new_secret).now()


def test_qr_uses_exact_standard_totp_uri_and_no_external_service(harness, monkeypatch):
    seen = []
    real_qr = suite_mfa.qr_svg_data_uri

    def capture(payload):
        seen.append(payload)
        return real_qr(payload)

    monkeypatch.setattr(suite_mfa, "qr_svg_data_uri", capture)
    client = harness.client()
    page = _begin_setup(harness, client)
    text = page.get_data(as_text=True)
    secret = _secret(harness, harness.user_id)

    assert len(seen) == 1
    uri = seen[0]
    parsed = urlsplit(uri)
    query = parse_qs(parsed.query)
    assert parsed.scheme == "otpauth"
    assert parsed.netloc == "totp"
    assert USER_EMAIL in unquote(parsed.path)
    assert query["secret"] == [secret]
    assert query["issuer"] == ["Total Water Design Suite"]
    assert set(query) <= {"secret", "issuer", "algorithm", "digits", "period"}
    if "algorithm" in query:
        assert query["algorithm"] == ["SHA1"]
    if "digits" in query:
        assert query["digits"] == ["6"]
    if "period" in query:
        assert query["period"] == ["30"]

    match = re.search(r'src="(data:image/svg\+xml;base64,[^"]+)"', text)
    assert match
    svg = base64.b64decode(match.group(1).split(",", 1)[1])
    assert b"<svg" in svg
    assert secret.encode() not in svg
    assert "Google Charts" not in text
    assert "api.qrserver" not in text
    assert "chart.googleapis" not in text
    assert "data:image/svg+xml;base64," in text
    assert '<details class="auth-details mfa-manual-details">' in text
    assert '<details class="auth-details mfa-manual-details" open' not in text
    assert "Advanced setup URI" in text
    assert "Copy setup key" in text
    assert "/static/mfa_setup.js" in text


def test_valid_code_enables_mfa_invalid_and_missing_codes_do_not_and_secrets_are_not_logged(harness, caplog):
    caplog.set_level(logging.DEBUG)
    client = harness.client()
    _begin_setup(harness, client)
    secret = _secret(harness, harness.user_id)
    uri = suite_mfa._provisioning_uri(secret, USER_EMAIL, "Total Water Design Suite")

    missing = client.post("/mfa/setup", data={"code": ""})
    assert missing.status_code == 200
    with harness.app.app_context():
        assert suite_mfa._profile(harness.user_id, create=False).enabled is False

    valid = pyotp.TOTP(secret).now()
    invalid = valid[:-1] + str((int(valid[-1]) + 1) % 10)
    wrong = client.post("/mfa/setup", data={"code": invalid})
    assert wrong.status_code == 200
    assert b"verification code is incorrect" in wrong.data.lower()
    with harness.app.app_context():
        assert suite_mfa._profile(harness.user_id, create=False).enabled is False

    success = client.post("/mfa/setup", data={"code": pyotp.TOTP(secret).now()})
    assert success.status_code == 200
    codes = re.findall(r"[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}", success.get_data(as_text=True))
    assert len(codes) == 10
    with harness.app.app_context():
        profile = suite_mfa._profile(harness.user_id, create=False)
        assert profile.enabled is True
        assert all(value.startswith("scrypt:") for value in json.loads(profile.recovery_hashes_json))

    logs = caplog.text
    assert secret not in logs
    assert uri not in logs
    assert all(code not in logs for code in codes)


def test_restart_replaces_pending_secret_and_old_qr_cannot_activate(harness):
    client = harness.client()
    _begin_setup(harness, client)
    old_secret = _secret(harness, harness.user_id)

    restarted = client.post("/mfa/setup/restart", follow_redirects=False)
    assert restarted.status_code == 302
    assert restarted.headers["Location"].endswith("/mfa/setup")
    assert client.get("/mfa/setup").status_code == 200
    new_secret = _secret(harness, harness.user_id)
    assert new_secret != old_secret

    old_code, new_code = _different_current_codes(old_secret, new_secret)
    for _ in range(5):
        if old_code != new_code:
            break
        restarted = client.post("/mfa/setup/restart", follow_redirects=False)
        assert restarted.status_code == 302
        assert client.get("/mfa/setup").status_code == 200
        new_secret = _secret(harness, harness.user_id)
        old_code, new_code = _different_current_codes(old_secret, new_secret)
    assert old_code != new_code

    rejected = client.post("/mfa/setup", data={"code": old_code})
    assert rejected.status_code == 200
    assert b"verification code is incorrect" in rejected.data.lower()
    with harness.app.app_context():
        assert suite_mfa._profile(harness.user_id, create=False).enabled is False

    accepted = client.post("/mfa/setup", data={"code": pyotp.TOTP(new_secret).now()})
    assert accepted.status_code == 200
    assert b"Save your recovery codes" in accepted.data


def test_expired_pending_enrollment_rotates_before_verification(harness, monkeypatch):
    monkeypatch.setenv("TWDS_MFA_ENROLLMENT_TTL_SECONDS", "300")
    client = harness.client()
    _begin_setup(harness, client)
    old_secret = _secret(harness, harness.user_id)
    with harness.app.app_context():
        profile = suite_mfa._profile(harness.user_id, create=False)
        credential = suite_mfa._totp_credential(profile, create=False)
        credential.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        auth.db.session.commit()

    response = client.post("/mfa/setup", data={"code": pyotp.TOTP(old_secret).now()}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/mfa/setup")
    new_secret = _secret(harness, harness.user_id)
    assert new_secret != old_secret
    with harness.app.app_context():
        assert suite_mfa._profile(harness.user_id, create=False).enabled is False


def test_enrolled_user_challenge_and_recovery_code_single_use(harness):
    secret, recovery_codes = _pre_enroll(harness, harness.user_id)
    client = harness.client()
    assert _login(client, USER_EMAIL).status_code == 302
    gate = client.get("/suite", follow_redirects=False)
    assert "/mfa/challenge" in gate.headers.get("Location", "")
    page = client.get("/mfa/challenge")
    assert page.status_code == 200

    valid = pyotp.TOTP(secret).now()
    invalid = valid[:-1] + str((int(valid[-1]) + 1) % 10)
    wrong = client.post("/mfa/challenge", data={"code": invalid})
    assert wrong.status_code == 200
    assert b"Verification failed" in wrong.data
    right = client.post("/mfa/challenge", data={"code": pyotp.TOTP(secret).now()}, follow_redirects=False)
    assert right.status_code == 302
    assert right.headers["Location"].endswith("/suite")

    assert client.post("/logout").status_code == 302
    assert _login(client, USER_EMAIL).status_code == 302
    client.get("/suite", follow_redirects=False)
    recovery = recovery_codes[0]
    first = client.post("/mfa/challenge", data={"code": recovery}, follow_redirects=False)
    assert first.status_code == 302
    assert first.headers["Location"].endswith("/suite")
    assert client.post("/logout").status_code == 302
    assert _login(client, USER_EMAIL).status_code == 302
    client.get("/suite", follow_redirects=False)
    reused = client.post("/mfa/challenge", data={"code": recovery})
    assert reused.status_code == 200
    assert b"Verification failed" in reused.data


def test_admin_reset_deletes_old_credential_and_next_setup_gets_new_secret(harness):
    user_secret, _ = _pre_enroll(harness, harness.user_id)
    admin_secret, _ = _pre_enroll(harness, harness.admin_id)
    admin_client = harness.client()
    with harness.app.app_context():
        admin_email = auth.db.session.get(auth.User, harness.admin_id).email
    assert _login(admin_client, admin_email).status_code == 302
    admin_client.get("/suite", follow_redirects=False)
    challenge = admin_client.post(
        "/mfa/challenge",
        data={"code": pyotp.TOTP(admin_secret).now()},
        follow_redirects=False,
    )
    assert challenge.status_code == 302
    assert challenge.headers["Location"].endswith("/suite")

    reset = admin_client.post(f"/admin/security/users/{harness.user_id}/reset-mfa", follow_redirects=False)
    assert reset.status_code == 302
    with harness.app.app_context():
        profile = suite_mfa._profile(harness.user_id, create=False)
        credentials = auth.db.session.scalars(
            select(suite_mfa.MfaCredential).where(suite_mfa.MfaCredential.profile_id == profile.id)
        ).all()
        assert profile.enabled is False
        assert credentials == []

    user_client = harness.client()
    assert _login(user_client, USER_EMAIL).status_code == 302
    gate = user_client.get("/suite", follow_redirects=False)
    assert "/mfa/setup" in gate.headers.get("Location", "")
    setup = user_client.get("/mfa/setup", follow_redirects=False)
    assert setup.status_code == 200
    new_secret = _secret(harness, harness.user_id)
    assert new_secret != user_secret


def test_existing_enrolled_user_secret_is_not_rotated_by_setup_fix(harness):
    secret, _ = _pre_enroll(harness, harness.user_id)
    client = harness.client()
    with harness.app.app_context():
        email = auth.db.session.get(auth.User, harness.user_id).email
    assert _login(client, email).status_code == 302
    gate = client.get("/suite", follow_redirects=False)
    assert "/mfa/challenge" in gate.headers.get("Location", "")
    challenge = client.post(
        "/mfa/challenge",
        data={"code": pyotp.TOTP(secret).now()},
        follow_redirects=False,
    )
    assert challenge.status_code == 302
    assert challenge.headers["Location"].endswith("/suite")
    response = client.get("/mfa/setup", follow_redirects=False)
    assert response.status_code == 302
    assert "/account/security" in response.headers.get("Location", "")
    assert _secret(harness, harness.user_id) == secret


def test_mfa_qr_source_has_no_external_transport_or_secret_logging():
    qr_source = (ROOT / "suite_mfa_qr.py").read_text(encoding="utf-8")
    mfa_source = (ROOT / "suite_mfa.py").read_text(encoding="utf-8")
    template = (ROOT / "templates/auth/mfa_setup.html").read_text(encoding="utf-8")
    js = (ROOT / "static/mfa_setup.js").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "segno>=1.6,<2" in requirements
    assert "urllib" not in qr_source
    assert "requests" not in qr_source
    assert "http://" not in qr_source and "https://" not in qr_source
    for forbidden in ("Google Charts", "chart.googleapis", "api.qrserver", "console.log", "console.debug"):
        assert forbidden not in qr_source
        assert forbidden not in mfa_source
        assert forbidden not in template
        assert forbidden not in js
    assert 'detail="Pending enrollment secret rotated"' in mfa_source
    assert "secret=" not in mfa_source.lower().split("audit(")[-1]
