from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOTAL_WATER_ACADEMY_UF_MF_PEARCE_COMMERCIAL_MODULES_SYSTEM_CONFIGURATION_SOURCE_NOTE_v1.0.md"


def _text() -> str:
    assert DOC.exists(), f"Missing Pearce UF/MF commercial-module source note: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_chapter3_scope_and_evidence_guard_are_explicit():
    text = _text()
    assert "Commercial UF/MF Membranes & Modules" in text
    assert "approximately pages 95–128" in text
    assert "HIGH_QUALITY_EXPERT_PRACTITIONER_REFERENCE" in text
    assert "The following are **not** current 2026 design rules" in text
    for term in ("market-share statements", "supplier rankings", "historical product tables", "historical operating fluxes"):
        assert term in text


def test_module_architecture_is_taught_as_engineering_not_packaging():
    text = _text()
    for term in (
        "feed-channel size",
        "packing density",
        "solids tolerance",
        "hydraulic resistance",
        "backwashability",
        "repairability",
        "pressure containment",
        "ease of integrity testing",
    ):
        assert term in text
    assert "The most compact module is not automatically the most robust module" in text


def test_hollow_fibre_and_potting_topics_are_preserved():
    text = _text()
    for term in ("lumen", "wall thickness", "fibre bundle", "potting/tubesheet", "filtrate/permeate collection"):
        assert term in text
    for term in ("seal the feed and permeate compartments", "mechanically retain the fibres", "pressure and cyclic loading"):
        assert term in text
    assert "If the membrane polymer is chemically compatible, the whole module is chemically compatible" in text


def test_manufacturing_science_is_preserved_without_product_equivalence_assumption():
    text = _text()
    for term in (
        "polymer dope preparation",
        "phase inversion",
        "spinneret geometry",
        "bore liquid",
        "coagulation bath",
        "air gap",
        "module assembly",
        "integrity testing",
    ):
        assert term in text
    assert "PVDF is PVDF, so every PVDF UF membrane should perform similarly" in text


def test_integrity_is_taught_across_factory_commissioning_and_operation():
    text = _text()
    for stage in ("manufacturing integrity", "commissioning integrity", "operational integrity"):
        assert stage in text
    assert "Factory Pass, Plant Fail" in text


def test_polymeric_and_ceramic_manufacturing_comparison_is_preserved():
    text = _text()
    assert "polymer solution/dope → spinning/casting → phase inversion" in text
    assert "ceramic powder/support formation → firing/sintering" in text
    assert "graded ceramic structure" in text
    assert "The entire ceramic wall must have the same tiny pore size" in text


def test_configuration_taxonomy_keeps_independent_design_dimensions():
    text = _text()
    for term in (
        "membrane form",
        "filtration direction",
        "hydraulic mode",
        "pressure arrangement",
        "orientation",
        "material family",
    ):
        assert term in text
    assert "Outside-in means submerged" in text
    assert "separate design dimensions" in text


def test_inside_out_outside_in_are_taught_with_nonuniversal_guard():
    text = _text()
    for term in ("Inside-out", "Outside-in", "lumen plugging risk", "solids transport around bundles", "air scour/backwash interaction"):
        assert term in text
    assert "inside-out = clean water" in text
    assert "outside-in = dirty water" in text
    assert "not" in text


def test_feed_screening_is_module_specific_not_fixed_micron_rule():
    text = _text()
    for term in ("lumen/channel geometry", "fibre spacing", "stringy/fibrous material", "vendor requirements"):
        assert term in text
    assert "Do not convert the historical example screen sizes" in text
    assert "The Fibre Plugged but TMP Looked Fine" in text


def test_dead_end_crossflow_lifecycle_tradeoff_is_preserved():
    text = _text()
    for term in ("recirculation energy", "solids accumulation during filtration", "backwash/air/chemical cleaning"):
        assert term in text
    assert "Crossflow is technically better because it fouls less" in text


def test_pressurized_and_submerged_architectures_are_both_preserved():
    text = _text()
    for term in ("pressurized UF/MF system", "Submerged UF/MF", "permeate suction", "air-scour system", "pressure-vessel/module hardware"):
        assert term in text
    assert "Submerged UF always uses less energy than pressurized UF" in text
    assert "Pressurized or Submerged?" in text


def test_pressurized_submerged_design_matrix_is_multivariable():
    text = _text()
    for term in (
        "feed turbidity and TSS",
        "design flux",
        "membrane packing density",
        "feed pressure",
        "permeate suction",
        "air requirement",
        "recovery",
        "integrity testing",
        "lifecycle cost",
    ):
        assert term in text
    assert "No one column should be labeled universally “best.”" in text


def test_orientation_and_permeate_collection_are_taught_as_hydraulic_choices():
    text = _text()
    for term in ("Vertical versus horizontal configuration", "Single-end versus dual-end permeate collection", "internal pressure loss", "flow distribution"):
        assert term in text
    assert "Where Did the Permeate Pressure Go?" in text


def test_polymeric_vs_ceramic_comparison_is_balanced():
    text = _text()
    for term in ("Polymeric systems", "Ceramic systems", "packing density", "chemical resistance", "brittleness/impact sensitivity", "lifecycle economics"):
        assert term in text
    assert "Ceramic membrane = always more robust and therefore always better" in text


def test_process_sequence_and_controls_use_module_architecture():
    text = _text()
    assert "FILTRATION → DRAIN/RELAX → BACKWASH/BACKFLUSH → AIR FLUSH/AIR SCOUR → RINSE → FILTRATE TO WASTE → RETURN TO SERVICE" in text
    for term in ("valve positions", "pump permissives", "blower permissives", "sequence timers", "interlocks"):
        assert term in text
    assert "Program the UF Train" in text


def test_module_architecture_and_fouling_are_coupled():
    text = _text()
    for term in ("dead zones", "channel plugging", "air distribution", "backwash distribution", "cleaning chemical access"):
        assert term in text
    assert "same membrane chemistry + different module architecture can produce different operating behavior" in text
    assert "Same Polymer, Different Module" in text


def test_module_selection_workflow_ends_with_current_authority_verification():
    text = _text()
    assert "Module selection workflow" in text
    for term in (
        "Define feed and product requirements",
        "Compare inside-out versus outside-in",
        "Compare pressurized versus submerged",
        "Define integrity-test approach",
        "Estimate complete-system energy and recovery",
        "Compare lifecycle cost and maintainability",
    ):
        assert term in text
    assert "Verify with current manufacturer design tools/data and Total Pretreatment Design authority" in text


def test_misconception_library_preserves_core_guardrails():
    text = _text()
    for phrase in (
        "UF module format is just packaging",
        "More membrane area per cubic metre is always better",
        "Inside-out is always cleaner than outside-in",
        "Submerged UF always uses less energy",
        "The smallest feed screen is safest",
        "A 2011 supplier table is a current design shortlist",
    ):
        assert phrase in text


def test_engine_ownership_and_copyright_boundaries_are_preserved():
    text = _text()
    assert "app/total-pretreatment-design" in text
    assert "Academy must not hard-code historical Pearce values" in text
    for protected in ("module-format comparison table", "supplier table", "manufacturing schematics", "module photographs", "process diagrams"):
        assert protected in text
    assert "Research Basis / Sources & Further Reading" in text
