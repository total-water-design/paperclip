from pathlib import Path

from academy_content import LEVELS, TOTAL_GUIDED_HOURS, validate_curriculum

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TOTAL_WATER_ACADEMY_CRYSTALLIZER_SELECTION_SIZING_MODULE_v1.0.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_crystallizer_module_preserves_academy_scale_and_curriculum_integrity():
    assert TOTAL_GUIDED_HOURS == 360
    assert sum(level["hours"] for level in LEVELS) == 360
    assert validate_curriculum() == []


def test_crystallizer_module_maps_to_existing_level_8_and_capstone():
    text = read_doc()
    for module_id in ("L08-M02", "L08-M03", "L08-M04"):
        assert module_id in text
    assert "Level 10 capstone" in text


def test_crystallizer_module_teaches_population_balance_sizing_not_flow_only():
    text = read_doc().lower()
    for phrase in (
        "a crystallizer is not sized from feed flow alone",
        "mean residence time",
        "tau = v / q",
        "population-density slope",
        "suspension density",
        "working suspension volume",
        "target crystal-size distribution",
    ):
        assert phrase in text


def test_crystallizer_module_preserves_screening_vs_production_design_boundary():
    text = read_doc().lower()
    assert "screening / idealized sizing relation" in text
    assert "validated design calculation" in text
    assert "lpd = 3 g tau" in text
    assert "not a complete industrial crystallizer model" in text


def test_crystallizer_module_challenges_ideal_msmpr_assumptions():
    text = read_doc().lower()
    for term in (
        "size-dependent growth",
        "growth-rate dispersion",
        "agglomeration",
        "breakage",
        "classification",
        "fines removed or destroyed",
    ):
        assert term in text


def test_crystallizer_module_teaches_csd_control_features():
    text = read_doc().lower()
    for term in (
        "classified product removal",
        "fines destruction",
        "fines removal",
        "combined fines control + classified product removal",
    ):
        assert term in text


def test_crystallizer_module_includes_impurity_and_solution_environment_effects():
    text = read_doc().lower()
    for term in (
        "impurity incorporation",
        "crystal habit",
        "interfacial mass transfer",
        "water versus ethanol",
        "mother-liquor composition",
        "hydrodynamics",
    ):
        assert term in text


def test_crystallizer_module_does_not_invent_complete_equipment_selection_rules():
    text = read_doc().lower()
    assert "do not yet establish" in text
    assert "complete authoritative selection matrix" in text
    assert "should therefore not yet publish universal rules" in text
    assert "next source needed" in text


def test_crystallizer_module_preserves_engineering_ownership_and_confidentiality():
    text = read_doc()
    for owner in (
        "engine/shared-water-chemistry",
        "engine/shared-waterstream",
        "app/total-water-balance",
        "app/total-zld-design",
        "app/total-water-economics",
        "platform/suite-core",
    ):
        assert owner in text

    lower = text.lower()
    assert "confidential-source boundary" in lower
    assert "do not reproduce confidential project" in lower


def test_crystallizer_module_defines_interactive_design_missions():
    text = read_doc().lower()
    for mission in (
        "msmpr sizing lab",
        "csd slope lab",
        "model-violation detective",
        "fines-control mission",
        "purity-versus-growth mission",
        "dewatering handoff",
        "zld crystallizer design-basis mission",
        "screening-vs-production-design challenge",
    ):
        assert mission in text
