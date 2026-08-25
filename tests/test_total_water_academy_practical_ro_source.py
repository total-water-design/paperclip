from pathlib import Path

from academy_content import LEVELS, TOTAL_GUIDED_HOURS, validate_curriculum

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TOTAL_WATER_ACADEMY_PRACTICAL_RO_SOURCE_MAP_v1.0.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ro_source_map_preserves_university_scale_course_structure():
    assert TOTAL_GUIDED_HOURS == 360
    assert sum(level["hours"] for level in LEVELS) == 360
    assert validate_curriculum() == []


def test_ro_source_map_strengthens_existing_academy_levels_without_creating_new_owner():
    text = read(DOC).lower()
    for phrase in (
        "levels 1–2",
        "level 3",
        "level 4",
        "level 6",
        "level 7",
        "level 8",
        "levels 9–10",
    ):
        assert phrase in text

    curriculum_text = " ".join(
        " ".join(
            [
                level["title"],
                level["mission"],
                *level["competencies"],
                *(module["title"] for module in level["modules"]),
            ]
        )
        for level in LEVELS
    ).lower()
    for term in ("pretreatment", "membrane", "pump", "plc", "zld", "capstone"):
        assert term in curriculum_text


def test_ro_source_map_requires_current_validation_for_dated_numeric_guidance():
    text = read(DOC).lower()
    assert "published in 2015" in text
    assert "current manufacturer documentation" in text
    assert "validated twds logic" in text
    assert "historical examples" in text
    assert "textbook rule of thumb" in text
    assert "project-specific validated design calculation" in text


def test_ro_source_map_preserves_specialist_engine_ownership():
    text = read(DOC)
    for owner in (
        "engine/shared-water-chemistry",
        "engine/shared-waterstream",
        "app/total-water-balance",
        "app/total-pretreatment-design",
        "app/total-ro-design",
        "app/total-zld-design",
        "app/total-water-economics",
        "platform/suite-core",
    ):
        assert owner in text


def test_ro_source_map_requires_original_academy_visuals_and_copyright_boundary():
    text = read(DOC).lower()
    assert "original academy graphics" in text
    assert "do not copy copyrighted figures or photographs" in text
    assert "do not reproduce chapters, tables, photographs or figures" in text


def test_ro_source_map_defines_interactive_learning_not_lecture_only():
    text = read(DOC).lower()
    for mission in (
        "recovery slider",
        "boundary-layer visual",
        "array builder",
        "membrane spec-sheet challenge",
        "pretreatment detective",
        "ro skid pfd mission",
        "plc start-up mission",
        "normalization detective",
        "troubleshooting tree",
        "ro-to-zld handoff",
    ):
        assert mission in text
