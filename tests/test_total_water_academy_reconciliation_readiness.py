from pathlib import Path

from academy_content import LEVELS, TOTAL_GUIDED_HOURS, validate_curriculum

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_all_ten_levels_are_present_in_persistent_academy_navigation():
    template = read("templates/academy/base.html")
    assert len(LEVELS) == 10
    for level in LEVELS:
        assert f"level_id='{level['id']}'" in template
    assert template.count("academy_tr('level')") >= 10


def test_academy_remains_on_shared_suite_application_shell():
    template = read("templates/academy/base.html")
    assert '{% extends "shared/application_shell.html" %}' in template
    assert 'meta name="csrf-token"' in template
    assert "suite_application_shell" not in read("static/academy.css")


def test_academy_curriculum_integrity_remains_reconciliation_safe():
    assert TOTAL_GUIDED_HOURS == 360
    assert sum(level["hours"] for level in LEVELS) == TOTAL_GUIDED_HOURS
    assert validate_curriculum() == []
    level_ids = [level["id"] for level in LEVELS]
    assert level_ids == [f"L{i:02d}" for i in range(1, 11)]
    module_ids = [module["id"] for level in LEVELS for module in level["modules"]]
    assert len(module_ids) == len(set(module_ids))
    assert all(module_id.startswith(f"{level['id']}-M") for level in LEVELS for module_id in [module["id"] for module in level["modules"]])


def test_academy_hosted_registration_is_additive_and_uses_academy_namespace():
    wsgi = read("wsgi.py")
    academy = read("academy.py")
    placement = read("academy_placement.py")
    assert "from academy import init_total_water_academy" in wsgi
    assert "from academy_placement import init_academy_placement" in wsgi
    assert "init_total_water_academy(app)" in wsgi
    assert "init_academy_placement(app)" in wsgi
    assert 'url_prefix="/academy"' in academy
    assert 'url_prefix="/academy"' in placement


def test_academy_does_not_take_over_specialist_engine_authority():
    combined = read("academy.py") + "\n" + read("academy_content.py") + "\n" + read("academy_placement.py")
    for forbidden in (
        "from calculations import",
        "from chemistry_analysis import",
        "from water_chemistry import",
        "from design_optimizer import",
        "from compute_engine import",
    ):
        assert forbidden not in combined


def test_diploma_language_does_not_claim_licensure_or_accreditation_in_any_locale():
    content = read("academy_content.py").lower()
    diploma = read("templates/academy/diploma.html")
    i18n = read("academy_i18n.py")
    assert "not professional licensure" in content
    assert "third-party accreditation" in content
    assert "academy_tr('completion_not_licensure')" in diploma
    assert "Applied engineering completion—not licensure" in i18n
    assert "Finalización de ingeniería aplicada; no es una licencia" in i18n
    assert "إكمال هندسي تطبيقي — وليس ترخيصاً مهنياً" in i18n
