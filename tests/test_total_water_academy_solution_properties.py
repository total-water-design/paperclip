from pathlib import Path

from academy_content import (
    ACADEMY_VERSION,
    LEVELS,
    SOLUTION_PROPERTIES_THREAD,
    TOTAL_GUIDED_HOURS,
    curriculum,
    validate_curriculum,
)

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def level(level_id: str):
    return next(item for item in LEVELS if item["id"] == level_id)


def test_solution_properties_thread_progresses_foundation_to_ro_to_zld():
    stages = SOLUTION_PROPERTIES_THREAD["stages"]
    assert [stage["level_id"] for stage in stages] == ["L02", "L04", "L08"]
    assert [stage["depth"] for stage in stages] == ["foundation", "applied", "advanced"]
    assert stages[0]["module_ids"] == ["L02-M06"]
    assert stages[1]["module_ids"] == ["L04-M03"]
    assert stages[2]["module_ids"] == ["L08-M02", "L08-M03", "L08-M04"]


def test_level_two_teaches_solution_literacy_inside_unit_operations():
    item = level("L02")
    text = " ".join([*item["competencies"], *(module["title"] for module in item["modules"])]).lower()
    for term in ("solution", "solubility", "saturation", "activity", "ionic strength", "physical properties"):
        assert term in text
    assert item["hours"] == 42


def test_membrane_level_reuses_solution_thermodynamics_for_scaling():
    item = level("L04")
    text = " ".join([*item["competencies"], *(module["title"] for module in item["modules"])]).lower()
    assert "activity" in text
    assert "scaling" in text
    assert "concentration polarization" in text


def test_zld_level_explicitly_covers_concentrated_solution_and_crystallization_physics():
    item = level("L08")
    text = " ".join([item["mission"], *item["competencies"], *(module["title"] for module in item["modules"])]).lower()
    for term in ("solution thermodynamics", "brine physical properties", "nucleation", "hydrate"):
        assert term in text
    assert "crystallization" in text or "crystallizer" in text

    advanced_topics = " ".join(SOLUTION_PROPERTIES_THREAD["stages"][2]["topics"]).lower()
    for term in ("viscosity", "diffusivity", "latent heat", "metastable", "phase-diagram", "crystal-growth"):
        assert term in advanced_topics


def test_curriculum_exposes_learning_thread_without_changing_total_hours():
    snapshot = curriculum()
    assert ACADEMY_VERSION == "0.4.0"
    assert snapshot["learning_threads"][0]["id"] == "solutions-to-zld"
    assert TOTAL_GUIDED_HOURS == 360
    assert sum(item["hours"] for item in LEVELS) == 360
    assert validate_curriculum() == []


def test_placement_surface_uses_the_same_academy_version_constant():
    source = read("academy_placement.py")
    assert "from academy_content import ACADEMY_VERSION" in source
    assert "app_version=ACADEMY_VERSION" in source
    assert 'app_version="0.2.0"' not in source


def test_source_intake_policy_preserves_authority_and_copyright_boundaries():
    doc = read("docs/TOTAL_WATER_ACADEMY_SOLUTIONS_AND_ZLD_v0.3.md").lower()
    assert "does **not** own a competing electrolyte, scaling, membrane or crystallizer solver" in doc
    assert "paraphrase copyrighted material" in doc
    assert "engine/shared-water-chemistry" in doc
    assert "app/total-zld-design" in doc
    assert "interactive learning direction" in doc
