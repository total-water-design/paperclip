from pathlib import Path

from academy_content import (
    LEVELS,
    PILOT_MODULE,
    TOTAL_GUIDED_HOURS,
    curriculum,
    evaluate_activity,
    validate_curriculum,
)

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_curriculum_has_ten_levels_and_university_scale_guided_hours():
    assert len(LEVELS) == 10
    assert TOTAL_GUIDED_HOURS == 360
    assert sum(level["hours"] for level in LEVELS) == 360
    assert curriculum()["guided_hours"] == 360
    assert validate_curriculum() == []


def test_curriculum_covers_required_process_and_plant_skills():
    text = " ".join(level["title"] + " " + " ".join(level["competencies"]) for level in LEVELS).lower()
    for term in ("pretreatment", "membrane", "biological", "zld", "electrical", "plc", "vfd", "y/delta", "capex", "capstone"):
        assert term in text


def test_pilot_uses_three_quiz_practical_test_contract():
    assert [step["kind"] for step in PILOT_MODULE["steps"]] == [
        "concept", "quiz", "concept", "quiz", "concept", "quiz", "practical", "test"
    ]


def test_pilot_quiz_explains_correct_and_incorrect_reasoning():
    wrong = evaluate_activity("quiz-1", 0)
    right = evaluate_activity("quiz-1", 1)
    assert wrong["correct"] is False
    assert wrong["hint"]
    assert "membrane" in wrong["feedback"].lower()
    assert right["correct"] is True
    assert right["score"] == 100.0
    assert "pretreatment" in right["feedback"].lower()


def test_pilot_practical_is_a_real_sequence_exercise_not_multiple_choice():
    step = next(item for item in PILOT_MODULE["steps"] if item["id"] == "practical-1")
    assert step["practical_type"] == "assemble_train"
    exact = evaluate_activity("practical-1", step["target_sequence"])
    poor = evaluate_activity("practical-1", ["ro", "activated_sludge", "coarse_screen"])
    assert exact["correct"] is True
    assert exact["score"] == 100.0
    assert poor["correct"] is False
    assert poor["score"] < 75.0


def test_pilot_module_test_has_configurable_pass_behavior():
    passed = evaluate_activity("module-test", {"t1": 1, "t2": 0, "t3": 1, "t4": 0, "t5": 1})
    failed = evaluate_activity("module-test", {"t1": 0, "t2": 0, "t3": 0, "t4": 0, "t5": 0})
    assert passed["correct"] is True
    assert passed["score"] == 100.0
    assert failed["correct"] is False


def test_academy_does_not_fork_specialist_calculation_engines():
    app_text = read("academy.py")
    content_text = read("academy_content.py")
    forbidden_direct_engine_imports = (
        "from calculations import",
        "from chemistry_analysis import",
        "from water_chemistry import",
        "from design_optimizer import",
        "from compute_engine import",
    )
    for fragment in forbidden_direct_engine_imports:
        assert fragment not in app_text
        assert fragment not in content_text
    assert "validated Suite adapter" in read("docs/TOTAL_WATER_ACADEMY_ARCHITECTURE_v0.1.md")


def test_hosted_suite_registers_academy_blueprint():
    wsgi = read("wsgi.py")
    assert "from academy import init_total_water_academy" in wsgi
    assert "init_total_water_academy(app)" in wsgi


def test_academy_api_namespace_stays_outside_legacy_ro_api_gate():
    app_text = read("academy.py")
    script = read("static/academy.js")
    assert 'url_prefix="/academy"' in app_text
    assert '"/api/modules/' in app_text
    assert "/academy/api/modules/" in script
    assert "/api/academy/modules/" not in script


def test_learning_ui_has_interactive_design_and_explanation_hooks():
    template = read("templates/academy/module.html")
    script = read("static/academy.js")
    i18n = read("academy_i18n.py")
    assert "data-submit-practical" in template
    assert "data-academy-train" in template
    assert "data-submit-test" in template
    assert "academy_tr('check_reasoning')" in template
    assert '"check_reasoning": "Check my reasoning"' in i18n
    assert "/academy/api/modules/" in script


def test_diploma_is_explicitly_not_professional_licensure():
    text = read("academy_content.py")
    assert "not professional licensure" in text
    assert "third-party accreditation" in text
