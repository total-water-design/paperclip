from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_server_wires_all_suite_platform_services():
    text = read("wsgi.py")
    for token in (
        'apply_suite_metrics_hardening()',
        'register_suite_metrics(app)',
        'init_suite_mfa(app)',
        'init_suite_feedback(app)',
        'init_suite_feedback_state(app)',
        'init_suite_communications(app)',
        'init_suite_reports(app)',
        'init_suite_commercial(app)',
    ):
        assert token in text


def test_metrics_hardening_runs_before_metrics_registration():
    text = read("wsgi.py")
    assert text.index('apply_suite_metrics_hardening()') < text.index('register_suite_metrics(app)')
    assert 'TOTALRO_EC2_INSTANCE_TYPE", "unknown"' in text


def test_cross_app_services_do_not_import_engineering_calculations():
    files = (
        'suite_mfa.py', 'suite_feedback.py', 'suite_feedback_state.py',
        'suite_feedback_hardening.py', 'suite_communications.py', 'suite_reports.py',
        'suite_commercial.py', 'suite_mail.py', 'suite_metrics.py',
        'suite_metrics_hardening.py',
    )
    combined = '\n'.join(read(name) for name in files)
    assert 'from calculations import' not in combined
    assert 'from flowsheet import' not in combined
    assert 'from water_chemistry import' not in combined


def test_admin_navigation_exposes_platform_controls():
    text = read("templates/auth/admin_base.html")
    for label in ('Metrics', 'Feedback', 'Security', 'Communications', 'Products'):
        assert f'>{label}<' in text
