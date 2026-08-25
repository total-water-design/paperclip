from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOTAL_WATER_ACADEMY_UF_MF_PEARCE_SOURCE_MAP_v1.0.md"


def _text() -> str:
    assert DOC.exists(), f"Missing Pearce UF/MF Academy source map: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_source_identity_and_age_guard():
    text = _text()
    assert "Graeme K. Pearce" in text
    assert "UF/MF Membrane Water Treatment: Principles and Design" in text
    assert "2011" in text
    assert "HIGH_QUALITY_EXPERT_PRACTITIONER_REFERENCE" in text
    assert "must not silently convert any example number into a 2026 design rule" in text


def test_source_maps_across_existing_levels_without_new_hours():
    text = _text()
    assert "without increasing the 360-hour curriculum" in text
    for level in ("Level 1", "Level 2", "Level 3", "Level 4", "Level 6", "Level 7", "Level 8", "Level 9", "Level 10"):
        assert level in text


def test_uf_mf_ratings_and_overlap_are_taught_without_fake_hard_cutoff():
    text = _text()
    for term in ("MWCO", "pore-size", "pore-size distribution", "actual removal performance", "UF versus MF"):
        assert term in text
    assert "Do not create a universal single-pore-size cutoff" in text


def test_flow_configuration_and_energy_tradeoff_are_preserved():
    text = _text()
    for term in ("Crossflow", "Dead-end / direct-flow filtration", "energy", "solids accumulation", "cleaning frequency", "recovery"):
        assert term in text
    assert "Crossflow or Dead-End?" in text


def test_material_science_topics_are_preserved():
    text = _text()
    for term in (
        "hydrophilicity/hydrophobicity",
        "contact angle",
        "zeta potential",
        "mechanical strength",
        "chemical resistance",
        "oxidant resistance",
        "fibre strength",
        "burst pressure versus collapse pressure",
        "Ceramic membranes",
    ):
        assert term in text
    assert "The most hydrophilic membrane is always the least-fouling membrane" in text


def test_transport_flux_tmp_and_permeability_distinctions_are_preserved():
    text = _text()
    for term in ("TMP", "Flux", "Permeability", "viscosity/temperature"):
        assert term in text
    assert "Flux decreased, therefore the membrane fouled" in text


def test_fouling_mechanisms_are_specific_not_generic():
    text = _text()
    for term in ("complete blocking", "standard blocking", "intermediate blocking", "cake filtration", "Gel/organic fouling", "Oil fouling"):
        assert term in text
    assert "Blocking Law Detective" in text


def test_cleaning_hierarchy_is_preserved():
    text = _text()
    for term in ("backwash", "air flush", "air scour", "CEB", "CIP", "Cleaning Ladder"):
        assert term in text
    assert "Do not copy 2011 chemical concentrations or soak durations as 2026 defaults" in text
    assert "More air or more backwash always cleans better" in text


def test_coagulation_before_uf_is_taught_as_tradeoff():
    text = _text()
    for term in ("under-dose", "overdose", "residual metal/polymer", "irreversible fouling"):
        assert term.replace("under-dose", "underdose").replace("over-dose", "overdose") in text or term in text
    assert "No universal coagulant dose is authorized" in text


def test_critical_sustainable_threshold_flux_are_preserved_with_guard():
    text = _text()
    for term in ("Critical flux", "Sustainable flux", "Threshold flux", "The Highest Flux Is Not the Best Flux"):
        assert term in text
    assert "Do not present critical, sustainable or threshold flux as intrinsic universal constants" in text


def test_temperature_normalization_is_preserved():
    text = _text()
    assert "Temperature correction" in text
    assert "colder water has higher viscosity" in text
    assert "Cold Morning, Same Membrane" in text
    assert "Do not hard-code its coefficients" in text


def test_filtrate_quality_requires_multi_signal_monitoring():
    text = _text()
    for term in ("turbidity", "particle counting", "normalized permeability", "membrane integrity test results"):
        assert term in text
    assert "Low turbidity proves the membrane is intact" in text


def test_swro_uf_pretreatment_is_not_declared_universally_superior():
    text = _text()
    for term in ("algae/AOM/TEP", "coagulant strategy", "backwash waste", "cartridge-filter interface", "RO feed-quality targets"):
        assert term in text
    assert "UF/MF is not automatically superior to conventional pretreatment for every SWRO site" in text
    assert "Conventional or UF?" in text


def test_regulatory_material_is_historical_until_current_verification():
    text = _text()
    assert "historical drinking-water and reuse regulatory/approval discussion" in text
    assert "Do not present historical regulatory lists/standards as current requirements" in text


def test_evidence_literacy_and_future_page_extension_policy_are_preserved():
    text = _text()
    assert "What Aged and What Did Not?" in text
    for category in ("fundamental physics", "historical regulation", "product-specific property", "operating example requiring current verification"):
        assert category in text
    assert "Future pages from the same book should extend this map rather than create duplicate source documents" in text


def test_engine_ownership_and_copyright_boundaries_are_preserved():
    text = _text()
    assert "app/total-pretreatment-design" in text
    assert "Academy must not fork a competing professional UF/MF engine" in text
    for protected in ("book pages", "tables", "figures", "long passages"):
        assert protected in text
    assert "Research Basis / Sources & Further Reading" in text
