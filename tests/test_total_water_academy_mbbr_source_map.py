from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TOTAL_WATER_ACADEMY_MBBR_SOURCE_MAP_v1.0.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_mbbr_maps_across_unit_ops_bio_energy_controls_and_capstone():
    text = read_doc().lower()
    for level in ("level 2", "level 5", "level 6", "level 7", "level 10"):
        assert level in text


def test_attached_growth_transport_and_media_concepts_are_explicit():
    text = read_doc().lower()
    for concept in (
        "attached-growth process",
        "bulk liquid ↔ biofilm ↔ carrier surface",
        "boundary layer/biofilm",
        "protected surface area",
        "fill fraction",
        "media-retention screens",
    ):
        assert concept in text


def test_hydraulic_and_biomass_retention_are_distinguished():
    text = read_doc().lower()
    assert "hrt and biomass retention are not the same concept" in text
    assert "srt in suspended activated sludge" in text
    assert "attached biomass retention in mbbr" in text


def test_aeration_is_taught_as_oxygen_and_mixing():
    text = read_doc().lower()
    assert "aeration is both oxygen transfer and mixing" in text
    assert "carrier/media mixing and movement" in text
    assert "reducing air cannot be evaluated only as an energy-saving action" in text


def test_solids_and_downstream_separation_are_not_omitted():
    text = read_doc().lower()
    assert "mbbr does not eliminate solids handling" in text
    for method in ("secondary clarification", "lamella/tube settlers", "flotation", "filtration", "membrane separation"):
        assert method in text


def test_mbbrranges_are_historical_examples_not_design_defaults():
    text = read_doc().lower()
    assert "historical/example ranges" in text
    assert "must not become academy design defaults without verification" in text
    assert "project design values must come from validated total bio design logic" in text


def test_mbbrrange_quality_caveats_are_explicit():
    text = read_doc().lower()
    for caveat in (
        "2014 presentation",
        "secondary citations",
        "terminology is inconsistent",
        "units/labels appear questionable",
        "carrier technologies and protected-area definitions vary",
    ):
        assert caveat in text


def test_mbbr_interactive_exercises_are_defined():
    text = read_doc().lower()
    for mission in (
        "suspended or attached?",
        "build the mbbr train",
        "follow a molecule",
        "carrier-media comparison",
        "airflow tradeoff",
        "nitrification challenge",
        "media escape incident",
        "clarifier interface",
        "retrofit mission",
        "read the package-system data sheet",
    ):
        assert mission in text


def test_mbbr_misconception_library_is_present():
    text = read_doc().lower()
    for misconception in (
        "mbbr is just activated sludge with plastic media",
        "carrier surface area alone sizes the reactor",
        "more media is always better",
        "mbbr needs no solids separation",
        "aeration is only for oxygen",
        "a published hrt range is a design equation",
        "mbbr always eliminates sludge recycle",
    ):
        assert misconception in text


def test_total_bio_design_remains_authoritative():
    text = read_doc().lower()
    assert "app/total-bio-design" in text
    assert "must not create a parallel mbbr sizing engine" in text


def test_original_academy_visuals_are_required():
    text = read_doc().lower()
    assert "academy must create original diagrams rather than reuse presentation graphics" in text
