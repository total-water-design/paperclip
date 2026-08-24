from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from flask import Flask

import auth
import suite_mfa


ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "MFA-Management-Enforcement-2026!"
ADMIN_EMAIL = "mfa-management-admin@example.test"
USER_EMAIL = "mfa-management-user@example.test"


@pytest.fixture
def app_and_users(tmp_path, monkeypatch):
    monkeypatch.setenv("TOTALRO_DEPLOYMENT_MODE", "server")
    monkeypatch.setenv("TOTALRO_AUTH_ENABLED", "1")
    monkeypatch.setenv("TOTALRO_SECRET_KEY", "M" * 64)
    monkeypatch.setenv("TOTALRO_DATABASE_URL", f"sqlite:///{(tmp_path / 'mfa-management.db').as_posix()}")
    monkeypatch.setenv("TOTALRO_AUTO_CREATE_DB", "1")
    monkeypatch.setenv("TOTALRO_CSRF_ENABLED", "0")
    monkeypatch.setenv("TOTALRO_COOKIE_SECURE", "0")
    monkeypatch.setenv("TOTALRO_LOGIN_IP_LIMIT", "10000")
    monkeypatch.setenv("TWDS_MFA_REQUIRED", "1")
    monkeypatch.setenv("TWDS_MFA_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    auth._rate_hits.clear()

    app = Flask(
        "mfa_management_enforcement",
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )

    @app.get("/")
    def index():
        return "index"

    @app.get("/suite")
    def suite_dashboard():
        return "suite"

    # admin_security.html inherits the shared Suite admin navigation. The
    # isolated MFA fixture does not initialize unrelated communications or
    # commercial services, so provide inert route names solely to let the real
    # admin template render after MFA verification. Product behavior is not
    # stubbed: the security route itself remains the real Suite MFA view.
    app.add_url_rule(
        "/_validation/admin/communications",
        endpoint="suite_communications.admin_communications",
        view_func=lambda: "communications",
    )
    app.add_url_rule(
        "/_validation/admin/products",
        endpoint="suite_commercial.admin_products",
        view_func=lambda: "products",
    )

    auth.init_auth(app)
    suite_mfa.init_suite_mfa(app)

    now = datetime.now(timezone.utc)
    with app.app_context():
        admin = auth.User(
            email=ADMIN_EMAIL,
            full_name="MFA Management Admin",
            organization="Validation",
            password_hash="",
            role="admin",
            licensed_tier="platinum",
            status="active",
            terms_accepted_at=now,
        )
        admin.set_password(PASSWORD)
        user = auth.User(
            email=USER_EMAIL,
            full_name="MFA Management User",
            organization="Validation",
            password_hash="",
            role="user",
            licensed_tier="entry",
            status="active",
            terms_accepted_at=now,
        )
        user.set_password(PASSWORD)
        auth.db.session.add_all([admin, user])
        auth.db.session.flush()
        auth.ensure_default_entitlements(admin, flush=True)
        auth.ensure_default_entitlements(user, flush=True)

        admin_profile = suite_mfa._profile(admin.id, create=True)
        suite_mfa._totp_credential(admin_profile, create=True)
        admin_profile.enabled = True
        admin_profile.enrolled_at = now
        admin_recovery = suite_mfa._set_recovery_codes(admin_profile)

        user_profile = suite_mfa._profile(user.id, create=True)
        suite_mfa._totp_credential(user_profile, create=True)
        user_profile.enabled = True
        user_profile.enrolled_at = now
        suite_mfa._set_recovery_codes(user_profile)
        auth.db.session.commit()
        ids = (admin.id, user.id)

    yield app, ids, admin_recovery

    with app.app_context():
        auth.db.session.remove()
        auth.db.drop_all()
    auth._rate_hits.clear()


def _login(client, next_path: str):
    return client.post(
        f"/login?next={next_path}",
        data={"email": ADMIN_EMAIL, "password": PASSWORD, "remember": ""},
        follow_redirects=False,
    )


def _assert_challenge(response):
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/mfa/challenge")


def test_password_only_admin_security_is_challenged_then_allowed_after_mfa(app_and_users):
    app, _, recovery = app_and_users
    client = app.test_client()

    login = _login(client, "/admin/security")
    assert login.status_code == 302
    assert login.headers["Location"].endswith("/admin/security")

    gate = client.get("/admin/security", follow_redirects=False)
    _assert_challenge(gate)

    with client.session_transaction() as session:
        assert session.get(suite_mfa.MFA_PENDING_USER)
        assert not session.get(suite_mfa.MFA_SESSION_USER)

    verify = client.post(
        "/mfa/challenge",
        data={"code": recovery[0]},
        follow_redirects=False,
    )
    assert verify.status_code == 302
    assert verify.headers["Location"].endswith("/admin/security")

    allowed = client.get("/admin/security", follow_redirects=False)
    assert allowed.status_code == 200


def test_password_only_account_security_and_mutations_cannot_bypass_mfa(app_and_users):
    app, (admin_id, user_id), recovery = app_and_users

    account_client = app.test_client()
    assert _login(account_client, "/account/security").status_code == 302
    _assert_challenge(account_client.get("/account/security", follow_redirects=False))
    verify = account_client.post(
        "/mfa/challenge",
        data={"code": recovery[0]},
        follow_redirects=False,
    )
    assert verify.status_code == 302
    assert verify.headers["Location"].endswith("/account/security")
    assert account_client.get("/account/security").status_code == 200

    reset_client = app.test_client()
    assert _login(reset_client, "/admin/security").status_code == 302
    with app.app_context():
        profile = suite_mfa._profile(user_id, create=False)
        before = (
            profile.enabled,
            profile.reset_at,
            profile.last_totp_counter,
            profile.recovery_hashes_json,
        )
    reset_attempt = reset_client.post(
        f"/admin/security/users/{user_id}/reset-mfa",
        follow_redirects=False,
    )
    _assert_challenge(reset_attempt)
    with app.app_context():
        profile = suite_mfa._profile(user_id, create=False)
        after = (
            profile.enabled,
            profile.reset_at,
            profile.last_totp_counter,
            profile.recovery_hashes_json,
        )
        assert after == before

    regenerate_client = app.test_client()
    assert _login(regenerate_client, "/account/security").status_code == 302
    with app.app_context():
        profile = suite_mfa._profile(admin_id, create=False)
        recovery_before = list(json.loads(profile.recovery_hashes_json))
    regenerate_attempt = regenerate_client.post(
        "/account/security/recovery-codes",
        data={"code": "000000"},
        follow_redirects=False,
    )
    _assert_challenge(regenerate_attempt)
    with app.app_context():
        profile = suite_mfa._profile(admin_id, create=False)
        assert list(json.loads(profile.recovery_hashes_json)) == recovery_before
