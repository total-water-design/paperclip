from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_feedback_database_contains_authoritative_workflow_fields():
    text = read("suite_feedback.py")
    for token in (
        'user_first_name', 'user_email', 'context_json', 'admin_review',
        'acceptance_state', 'ai_processing_authorized', 'response_draft',
        'response_approval_state', 'response_sent_at', 'github_issue_id',
        'final_disposition'
    ):
        assert token in text


def test_feedback_lifecycle_contains_required_gates():
    text = read("suite_feedback.py")
    for state in (
        'NEW', 'ADMIN_REVIEW', 'ACCEPTED', 'REJECTED',
        'APPROVED_FOR_PRODUCT_REVIEW', 'GITHUB_ISSUE_CREATED',
        'RESPONSE_DRAFTED', 'RESPONSE_APPROVED', 'RESPONSE_SENT',
        'IMPLEMENTED', 'CLOSED'
    ):
        assert state in text


def test_feedback_does_not_auto_promote_to_github():
    text = read("suite_feedback.py")
    assert 'report.acceptance_state != "accepted"' in text
    assert 'not report.product_review_authorized' in text
    assert 'action == "promote_github"' in text
    assert 'action == "accept"' in text


def test_github_mirror_is_sanitized():
    text = read("suite_feedback.py")
    assert 'technical_requirement' in text
    assert 'reproduction_info' in text
    assert 'Customer name, email, account details, and raw project content are intentionally omitted' in text
    assert 'TWDS_GITHUB_TOKEN' in text


def test_feedback_receipt_uses_transactional_mail_and_first_name():
    text = read("suite_feedback.py")
    assert 'event_type="feedback_receipt"' in text
    assert 'template="feedback_receipt_v1"' in text
    assert 'Thank you for taking the time to send feedback' in text
    assert 'We take user feedback seriously' in text
    assert 'admin@totalrodesign.com' in text


def test_admin_dashboard_has_product_gate_controls_and_date_filter():
    template = read("templates/auth/admin_feedback.html")
    for token in (
        'date_from', 'date_to', 'Approve product review', 'Accept', 'Reject',
        'Request more info', 'Mark duplicate', 'Approve response',
        'Create sanitized GitHub issue', 'Implementation status', 'Release / version'
    ):
        assert token in template


def test_feedback_implementation_state_is_separate_from_customer_record():
    text = read("suite_feedback_state.py")
    assert 'suite_feedback_implementation_state' in text
    assert 'implementation_status' in text
    assert 'release_version' in text
    assert 'feedback_implementation_status_updated' in text
