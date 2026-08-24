from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_feedback_service_is_suite_scoped():
    text = read("suite_feedback.py")
    assert '/api/suite/feedback/report' in text
    assert '/admin/feedback' in text
    assert 'suite_feedback_reports' in text
    assert 'support@totalrodesign.com' in text


def test_shared_shell_exposes_one_common_feedback_control():
    text = read("templates/shared/application_shell.html")
    assert 'data-twds-feedback-open' in text
    assert 'data-twds-feedback-dialog' in text
    assert "suite_feedback.js" in text
    assert "suite_feedback.css" in text


def test_feedback_client_posts_to_common_endpoint():
    text = read("static/suite_feedback.js")
    assert "'/api/suite/feedback/report'" in text
    assert 'TWDSFeedbackContextProvider' in text
    assert 'project_id' in text
    assert 'workspace' in text


def test_feedback_delivery_has_persistent_status_and_retry():
    text = read("suite_feedback.py")
    for token in ('delivery_status', 'attempts', 'last_error', 'retry_feedback'):
        assert token in text


def test_feedback_configuration_supports_suite_and_legacy_names():
    service = read("suite_feedback.py")
    env = read("deploy/totalrodesign.env.example")
    for token in ('TWDS_FEEDBACK_TO', 'TWDS_SMTP_HOST', 'TWDS_SMTP_USER', 'TWDS_SMTP_PASSWORD'):
        assert token in service or token in env
    assert 'TOTALRO_SMTP_HOST' in service


def test_feedback_uses_existing_admin_sender_identity():
    env = read("deploy/totalrodesign.env.example")
    docs = read("docs/UNIFIED_FEEDBACK_SERVICE_v1.0.md")
    assert 'TWDS_SMTP_USER=admin@totalrodesign.com' in env
    assert 'TWDS_SMTP_FROM=admin@totalrodesign.com' in env
    assert 'TOTALRO_SMTP_USER=admin@totalrodesign.com' in env
    assert 'TOTALRO_SMTP_FROM=admin@totalrodesign.com' in env
    assert 'admin@totalrodesign.com' in docs
    assert 'totalrodesign@gmail.com' not in env
    assert 'totalrodesign@gmail.com' not in docs


def test_shared_feedback_contains_no_ai_debug_instructions():
    combined = "\n".join([
        read("suite_feedback.py"),
        read("static/suite_feedback.js"),
        read("templates/shared/application_shell.html"),
        read("templates/auth/admin_feedback.html"),
    ]).lower()
    for forbidden in ('chatgpt', 'openai', 'investigation prompt', 'stack trace'):
        assert forbidden not in combined
