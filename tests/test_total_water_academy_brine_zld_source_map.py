from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TOTAL_WATER_ACADEMY_BRINE_ZLD_SOURCE_MAP_v1.0.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_peer_reviewed_brine_review_and_doi_are_preserved():
    text = read_doc()
    assert "Panagopoulos" in text
    assert "Science of the Total Environment" in text
    assert "10.1016/j.scitotenv.2019.07.351" in text


def test_brine_source_strengthens_existing_levels_without_claiming_new_engine_ownership():
    text = read_doc().lower()
    for level in ("level 4", "level 5", "level 8", "level 9", "level 10"):
        assert level in text
    assert "total zld design remains authoritative" in text
    assert "academy does **not** own" in text


def test_disposal_methods_are_explicit():
    text = read_doc().lower()
    for method in (
        "surface-water discharge",
        "sewer discharge",
        "deep-well injection",
        "evaporation ponds",
        "land application",
    ):
        assert method in text


def test_zld_is_taught_as_a_treatment_train():
    text = read_doc().lower()
    assert "zld is a treatment train" in text
    assert "preconcentration → evaporation / high-salinity concentration → crystallization / solids production" in text
    assert "every unit of water removed before the most energy-intensive thermal step" in text


def test_technology_families_cover_membrane_electrical_and_thermal_options():
    text = read_doc().lower()
    for concept in (
        "high-pressure ro",
        "forward osmosis",
        "osmotically assisted ro",
        "membrane distillation",
        "membrane crystallization",
        "edr",
        "electrodialysis metathesis",
        "brine concentrator",
        "forced-circulation brine crystallizer",
        "spray drying",
        "eutectic freeze crystallization",
        "wind-aided intensified evaporation",
    ):
        assert concept in text


def test_forced_circulation_crystallizer_and_seeded_slurry_are_taught():
    text = read_doc().lower()
    assert "seeded-slurry anti-scaling strategy" in text
    assert "forced-circulation crystallizer" in text
    for step in (
        "recirculation pump",
        "external heater",
        "vapor body",
        "product/slurry bleed",
        "centrifugation or filtration",
    ):
        assert step in text


def test_energy_materials_environment_and_resource_recovery_are_linked():
    text = read_doc().lower()
    for concept in (
        "energy hierarchy",
        "materials and corrosion",
        "environmental design",
        "circular-economy nuance",
        "purity",
        "market demand",
        "offtake certainty",
    ):
        assert concept in text


def test_historical_2019_values_are_not_promoted_to_current_design_limits():
    text = read_doc().lower()
    assert "historical/source-labelled values" in text
    assert "historical sec values" in text
    assert "not as current design guarantees" in text
    assert "current design limits must come from validated suite owners" in text


def test_brine_interactive_exercises_are_defined():
    text = read_doc().lower()
    for mission in (
        "follow the reject",
        "disposal-method screening mission",
        "build a zld train",
        "energy cliff",
        "seeded-slurry challenge",
        "crystallizer flow-path challenge",
        "waste or product?",
        "brine environmental decision",
    ):
        assert mission in text


def test_brine_misconception_library_is_present():
    text = read_doc().lower()
    for misconception in (
        "higher recovery is always better",
        "zld means one crystallizer",
        "if liquid discharge is zero, environmental impact is zero",
        "recovered salts automatically create revenue",
        "historical technology limits are current vendor guarantees",
        "brine is just water with more nacl",
    ):
        assert misconception in text


def test_copyright_and_source_policy_requires_original_academy_visuals():
    text = read_doc().lower()
    assert "do not reproduce publisher figures, tables or substantial prose" in text
    assert "build original twda graphics" in text
