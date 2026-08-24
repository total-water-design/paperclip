from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_mfa_is_mandatory_and_suite_wide():
    text = read("suite_mfa.py")
    wsgi = read("wsgi.py")
    assert 'TWDS_MFA_REQUIRED' in text
    assert 'os.environ["TWDS_MFA_REQUIRED"] = "1"' in wsgi
    assert 'init_suite_mfa(app)' in wsgi


def test_totp_secret_is_encrypted_and_recovery_codes_are_hashed():
    text = read("suite_mfa.py")
    assert 'pyotp.TOTP' in text
    assert 'encrypted_secret' in text
    assert 'Fernet' in text
    assert 'generate_password_hash' in text
    assert 'recovery_hashes_json' in text
    assert 'totp_secret = db.Column' not in text


def test_mfa_has_replay_protection_and_rate_limiting():
    text = read("suite_mfa.py")
    assert 'last_totp_counter' in text
    assert 'counter <= last_counter' in text
    assert 'TWDS_MFA_ATTEMPT_LIMIT' in text
    assert '_rate_limited' in text


def test_mfa_has_controlled_recovery_and_audit_events():
    text = read("suite_mfa.py")
    for token in (
        'mfa_enrolled', 'mfa_verified', 'mfa_admin_reset',
        'mfa_cli_reset', 'reset-user-mfa', 'mfa_recovery_codes_regenerated'
    ):
        assert token in text
    assert 'user.password_version = int(user.password_version or 0) + 1' in text


def test_admin_reset_requires_a_new_password_authentication():
    text = read("suite_mfa.py")
    assert 'MFA_PASSWORD_AUTH_AT' in text
    assert '_password_reauth_satisfied' in text
    assert '_force_password_reauth' in text
    assert 'profile.reset_at' in text
    assert 'request.endpoint == "auth.login"' in text


def test_mfa_architecture_is_extensible_to_webauthn():
    text = read("suite_mfa.py")
    assert 'MfaCredential' in text
    assert 'credential_id' in text
    assert 'public_data_json' in text
    assert 'WebAuthn' in text


def test_mfa_environment_requires_no_committed_secret():
    env = read("deploy/totalrodesign.env.example")
    assert 'TWDS_MFA_ENCRYPTION_KEY=REPLACE_WITH_STABLE_FERNET_KEY' in env
    assert 'TWDS_MFA_REQUIRED=1' in env
