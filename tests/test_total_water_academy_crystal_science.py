from pathlib import Path

from academy_content import (
    ACADEMY_VERSION,
    CRYSTAL_SCIENCE_THREAD,
    LEVELS,
    TOTAL_GUIDED_HOURS,
    curriculum,
    validate_curriculum,
)

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def level(level_id: str):
    return next(item for item in LEVELS if item["id"] == level_id)


def test_crystal_science_progresses_foundation_to_zld_to_capstone():
    stages = CRYSTAL_SCIENCE_THREAD["stages"]
    assert [stage["level_id"] for stage in stages] == ["L02", "L08", "L10"]
    assert [stage["depth"] for stage in stages] == ["foundation", "advanced", "capstone"]
    assert stages[0]["module_ids"] == ["L02-M06"]
    assert stages[1]["module_ids"] == ["L08-M02", "L08-M03", "L08-M04"]
    assert stages[2]["module_ids"] == ["L10-M03"]


def test_foundation_teaches_crystal_identity_without_turning_into_mineralogy_course():
    item = level("L02")
    text = " ".join([*item["competencies"], *(module["title"] for module in item["modules"])]).lower()
    for term in ("crystalline", "habit", "polymorphism", "hydrate", "crystal"):
        assert term in text

    foundation_topics = " ".join(CRYSTAL_SCIENCE_THREAD["stages"][0]["topics"]).lower()
    for term in ("amorphous", "unit cells", "lattice", "crystal faces", "polymorphism"):
        assert term in foundation_topics


def test_zld_crystal_science_covers_nucleation_growth_hydrodynamics_and_csd():
    item = level("L08")
    text = " ".join([item["mission"], *item["competencies"], *(module["title"] for module in item["modules"])]).lower()
    for term in ("primary/secondary nucleation", "crystal-growth", "hydrodynamics", "ostwald", "crystal-size distribution"):
        assert term in text

    topics = " ".join(CRYSTAL_SCIENCE_THREAD["stages"][1]["topics"]).lower()
    for term in (
        "metastable zone", "induction time", "homogeneous", "heterogeneous", "contact", "attrition",
        "critical nucleus", "burton-cabrera-frank", "screw-dislocation", "boundary layer",
        "arrhenius", "desupersaturation", "ostwald ripening", "growth-rate dispersion",
    ):
        assert term in topics


def test_crystal_science_is_connected_to_real_zld_operability():
    capstone = " ".join(CRYSTAL_SCIENCE_THREAD["stages"][2]["topics"]).lower()
    for term in ("supersaturation-control", "nucleation sources", "seeding", "hydrodynamics", "dewatering", "zld engine"):
        assert term in capstone

    doc = read("docs/TOTAL_WATER_ACADEMY_CRYSTALS_GROWTH_NUCLEATION_v0.4.md").lower()
    for term in ("excessive fines", "impeller", "poor mixing", "filtration", "centrifugation"):
        assert term in doc


def test_crystal_science_preserves_suite_engine_authority():
    policy = CRYSTAL_SCIENCE_THREAD["engine_policy"].lower()
    assert "shared water chemistry" in policy
    assert "total zld design" in policy
    doc = read("docs/TOTAL_WATER_ACADEMY_CRYSTALS_GROWTH_NUCLEATION_v0.4.md").lower()
    assert "academy does **not** own" in doc
    assert "app/total-zld-design" in doc
    assert "engine/shared-water-chemistry" in doc


def test_crystal_science_keeps_course_at_360_hours_and_is_exposed_in_curriculum():
    snapshot = curriculum()
    assert ACADEMY_VERSION == "0.4.0"
    assert TOTAL_GUIDED_HOURS == 360
    assert sum(item["hours"] for item in LEVELS) == 360
    assert validate_curriculum() == []
    assert [thread["id"] for thread in snapshot["learning_threads"]] == [
        "solutions-to-zld", "crystals-nucleation-growth"
    ]
