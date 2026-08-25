from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TOTAL_WATER_ACADEMY_GUIDED_ENGINEERING_SOLUTION_MODE_v1.0.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_guided_mode_teaches_repeatable_engineering_method():
    text = read_doc().lower()
    for phrase in (
        "define the design question",
        "establish the design basis",
        "draw the physical picture / control volume",
        "knowns, unknowns and units",
        "select the governing engineering principle",
        "predict the direction before calculating",
        "interpret the result physically",
        "check constraints and close the balances",
        "compare against a common wrong path",
        "transfer the lesson",
    ):
        assert phrase in text


def test_guided_mode_has_progressive_student_control():
    text = read_doc().lower()
    assert "try it yourself" in text
    assert "give me a hint" in text
    assert "solve it with me" in text
    assert "progressive hint ladder" in text


def test_common_mistake_cards_are_actionable_not_just_warnings():
    text = read_doc().lower()
    for field in (
        "mistake / misconception",
        "why it is tempting",
        "why it fails",
        "how to detect it",
        "how to correct it",
        "related competency",
    ):
        assert field in text


def test_difficult_domains_have_misconception_libraries():
    text = read_doc().lower()
    for domain in (
        "mass and energy balances",
        "membranes / ro",
        "biological systems",
        "pumps / electrical",
        "controls / plc",
        "edi / electromembranes",
        "crystallization / zld",
    ):
        assert domain in text


def test_assessment_does_not_reveal_full_solution_during_active_test():
    text = read_doc().lower()
    assert "do not reveal the full worked solution while the attempt is active" in text
    assert "require an independent attempt first" in text
    assert "step-by-step debrief" in text


def test_guidance_adapts_to_existing_placement_tracks():
    text = read_doc()
    for track in ("Foundation Builder", "Engineering Refresher", "Accelerated Review"):
        assert track in text


def test_guided_mode_preserves_suite_engineering_authority():
    text = read_doc().lower()
    assert "project-grade results must continue to come from the validated specialist owner" in text
    assert "academy owns the teaching sequence" in text
    assert "not parallel professional solvers" in text


def test_misconception_language_is_non_shaming():
    text = read_doc().lower()
    assert "do not use shaming language" in text
    assert "common mistake" in text
    assert "common misconception" in text


def test_success_criterion_is_method_not_answer_memorization():
    text = read_doc().lower()
    assert "what engineering principle did i use?" in text
    assert "what mistake was i most likely to make" in text
    assert "how would i change the approach if the design basis changed?" in text
    assert "not memorizing an answer" in text
