from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = ROOT / "deploy" / "verify_auth_install.py"


def test_auth_install_smoke_uses_canonical_wsgi_composition():
    text = VERIFY.read_text(encoding="utf-8")
    assert "import wsgi as wsgi_module" in text
    assert "app = wsgi_module.app" in text
    assert "import app as app_module" not in text


def test_mfa_blueprint_remains_registered_while_general_smoke_disables_only_enforcement():
    text = VERIFY.read_text(encoding="utf-8")
    import_pos = text.index("import wsgi as wsgi_module")
    disable_pos = text.index('os.environ["TWDS_MFA_REQUIRED"] = "0"')
    assert import_pos < disable_pos
    assert '"suite_mfa.admin_security"' in text
    assert "Dedicated MFA tests" in text


def test_all_unconditional_admin_navigation_endpoints_are_required_by_smoke():
    text = VERIFY.read_text(encoding="utf-8")
    for endpoint in (
        "auth.admin_users",
        "auth.admin_projects",
        "auth.admin_metrics",
        "suite_feedback.feedback_admin_page",
        "suite_mfa.admin_security",
        "suite_communications.admin_communications",
        "suite_commercial.admin_products",
    ):
        assert f'"{endpoint}"' in text
    assert 'client.get("/admin/users")' in text
    assert 'client.get("/admin/projects")' in text


def test_admin_create_smoke_uses_current_required_country_contract():
    text = VERIFY.read_text(encoding="utf-8")
    assert '"country_code": "US"' in text
    assert 'product_user.country_code == "US"' in text


def test_harness_does_not_change_dependency_or_production_mfa_configuration_files():
    # This regression is intentionally scoped to the verifier. Production WSGI
    # must still mandate MFA; the verifier may only override its subprocess env.
    wsgi = (ROOT / "wsgi.py").read_text(encoding="utf-8")
    assert 'os.environ["TWDS_MFA_REQUIRED"] = "1"' in wsgi
    assert 'init_suite_mfa(app)' in wsgi
