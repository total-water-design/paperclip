from pathlib import Path

from academy_content import LEVELS, TOTAL_GUIDED_HOURS, validate_curriculum
from academy_placement import DIAGNOSTIC_QUESTIONS, recommend_track, score_diagnostic

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_level_two_is_core_unit_operations_before_specialist_design():
    level = next(item for item in LEVELS if item["id"] == "L02")
    assert "Unit Operations" in level["title"]
    assert level["hours"] == 42
    text = " ".join([level["title"], *level["competencies"], *(m["title"] for m in level["modules"])]).lower()
    for concept in (
        "mass", "component", "energy", "heat transfer", "fluid flow", "momentum",
        "mass transfer", "diffusion", "separation", "equilibrium", "reaction",
    ):
        assert concept in text


def test_curriculum_keeps_university_scale_total_and_internal_hour_consistency():
    assert TOTAL_GUIDED_HOURS == 360
    assert sum(level["hours"] for level in LEVELS) == 360
    assert validate_curriculum() == []
    for level in LEVELS:
        assert sum(module["hours"] for module in level["modules"]) == level["hours"]


def test_entry_diagnostic_samples_process_engineering_and_water_practice():
    assert len(DIAGNOSTIC_QUESTIONS) >= 10
    domains = {question["domain"] for question in DIAGNOSTIC_QUESTIONS}
    for domain in (
        "units", "mass_balance", "energy_heat", "fluids", "mass_transfer",
        "chemistry", "water_process", "electrical_controls",
    ):
        assert domain in domains


def test_diagnostic_scoring_and_tracks_are_deterministic():
    correct_answers = {q["id"]: q["answer"] for q in DIAGNOSTIC_QUESTIONS}
    zero_answers = {q["id"]: -1 for q in DIAGNOSTIC_QUESTIONS}
    perfect, domain_scores = score_diagnostic(correct_answers)
    zero, _ = score_diagnostic(zero_answers)
    assert perfect == 100.0
    assert zero == 0.0
    assert all(value == 100.0 for value in domain_scores.values())
    assert recommend_track(40) == "Foundation Builder"
    assert recommend_track(65) == "Engineering Refresher"
    assert recommend_track(90) == "Accelerated Review"


def test_placement_personalizes_but_does_not_waive_diploma_requirements():
    source = read("academy_placement.py")
    template = read("templates/academy/placement.html")
    i18n = read("academy_i18n.py")
    assert "does not grant engineering\ncredit, waive diploma requirements" in source
    assert "academy_tr('recommendation_copy')" in template
    assert "Diploma requirements remain the same for everyone" in i18n
    assert "Los requisitos del Diploma son iguales para todos" in i18n
    assert "تبقى متطلبات الدبلوم نفسها للجميع" in i18n
    assert "academy_tr('skip_now')" in template
    assert "academy_placement_skipped" in source


def test_hosted_suite_registers_placement_and_navigation_exposes_it_in_localized_form():
    wsgi = read("wsgi.py")
    base = read("templates/academy/base.html")
    i18n = read("academy_i18n.py")
    assert "from academy_placement import init_academy_placement" in wsgi
    assert "init_academy_placement(app)" in wsgi
    assert "academy_tr('knowledge_check')" in base
    assert "academy_tr('nav_unit_operations')" in base
    assert '"knowledge_check": "Knowledge Check"' in i18n
    assert '"nav_unit_operations": "Unit Operations"' in i18n
