from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_report_provider_interface_keeps_engineering_logic_out_of_core():
    text = read("suite_reports.py")
    assert 'register_report_provider' in text
    assert 'ReportProvider' in text
    assert 'ReportResult' in text
    assert 'provider.generate(snapshot, context)' in text
    assert 'calculations.py' not in text


def test_full_report_uses_saved_project_snapshot():
    text = read("suite_reports.py")
    assert 'json.loads(row.snapshot_json)' in text
    assert '/api/suite/projects/<int:revision_id>/full-report' in text
    assert 'ProjectReportHistory' in text
    assert 'project_full_report_generated' in text


def test_project_library_separates_reporting_from_admin_debugging():
    template = read("templates/auth/project_library.html")
    auth = read("auth.py")
    assert 'Generate Full Report' in template
    assert 'admin_project_json' in auth
    assert 'admin_project_inspected' in auth


def test_provider_absence_fails_safely():
    text = read("suite_reports.py")
    assert 'provider_required' in text
    assert 'has not registered its full-report provider yet' in text
