from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOTAL_WATER_ACADEMY_PDH_PROVIDER_PATH_v1.0.md"


def _text() -> str:
    assert DOC.exists(), f"Missing Academy PDH provider path: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_pdh_path_prioritizes_engineering_specific_rcep_then_jurisdictions():
    text = _text()
    assert "PDH-ready course architecture → RCEP provider pathway → selected state/jurisdiction verification" in text
    assert "Registered Continuing Education Program for Engineers and Surveyors (RCEP)" in text
    assert "managed by the American Council of Engineering Companies (ACEC)" in text


def test_self_paced_pdh_cannot_equal_browser_time_or_guided_hours():
    text = _text()
    assert "Do not simply assign the current Academy guided-hour target as PDH" in text
    assert "excluding idle/browser-open time" in text
    assert "must not grant credit solely from elapsed browser time" in text


def test_florida_readiness_fields_and_special_laws_rules_restriction_are_present():
    text = _text()
    for phrase in (
        "participant/licensee name",
        "PE/license number",
        "course number if applicable",
        "course topic",
        "presenter",
        "continuing-education hours awarded",
        "brief course description",
    ):
        assert phrase in text
    assert "Florida Laws & Rules course is not an ordinary technical course" in text


def test_iacet_is_parallel_broader_quality_path_not_engineering_board_substitute():
    text = _text()
    assert "IACET as broader quality/accreditation path" in text
    assert "IACET accredits the **provider organization**, not one isolated Academy course" in text
    assert "1 CEU per 10 qualifying contact hours" in text
    assert "can complement RCEP/state engineering approval, not replace it" in text


def test_professional_credit_states_default_to_completion_only():
    text = _text()
    for state in (
        "completion_only",
        "pdh_candidate",
        "rcep_ready",
        "rcep_registered",
        "pdh_eligible_verified",
        "iacet_ceu_eligible",
    ):
        assert state in text
    assert "Default for every Academy course is" in text
    assert "`completion_only`" in text


def test_self_paced_credit_has_identity_assessment_and_auditability_controls():
    text = _text()
    for requirement in (
        "authenticated learner",
        "periodic knowledge checks",
        "interactive engineering work",
        "final assessment",
        "minimum passing score",
        "anomaly/idle detection",
        "auditable attempt and progress records",
    ):
        assert requirement in text


def test_first_pdh_candidate_courses_are_explicit():
    text = _text()
    for module_id in ("L04-M01", "L04-M03", "L03-M02", "L08-M03", "L07-M03"):
        assert module_id in text


def test_no_current_pdh_claim_is_explicit():
    text = _text()
    assert "no current PDH/CEH approval claim" in text
    assert "no professional-development credit is currently claimed" in text
