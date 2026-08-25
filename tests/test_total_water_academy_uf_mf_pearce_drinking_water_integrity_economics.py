from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOTAL_WATER_ACADEMY_UF_MF_PEARCE_DRINKING_WATER_INTEGRITY_ECONOMICS_SOURCE_NOTE_v1.0.md"


def _text() -> str:
    assert DOC.exists(), f"Missing Pearce drinking-water/integrity/economics note: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_source_scope_and_age_guard():
    text = _text()
    assert "pages 181–215" in text
    assert "Drinking Water Treatment" in text
    assert "HIGH_QUALITY_EXPERT_PRACTITIONER_REFERENCE" in text
    for protected in (
        "historical drinking-water regulatory limits",
        "specific historical integrity-test pressure values",
        "specific allowed fibre-break counts",
        "historical CAPEX/OPEX curves",
    ):
        assert protected in text


def test_doc_nom_aoc_are_distinguished():
    text = _text()
    for term in ("DOC", "NOM", "TOC", "AOC"):
        assert term in text
    assert "Carbon Is Not One Number" in text
    assert "organic/biofouling risk is solved" in text


def test_disinfection_is_not_replaced_by_membrane():
    text = _text()
    assert "Membrane filtration replaces disinfection" in text
    for term in ("disinfectant demand", "disinfection by-products", "precursor removal"):
        assert term in text


def test_iron_manganese_and_precipitation_kinetics_are_preserved():
    text = _text()
    for term in ("dissolved Fe/Mn", "oxidation", "precipitation kinetics", "particle size", "contact time"):
        assert term in text
    assert "Equilibrium direction and reaction kinetics are different engineering questions" in text
    assert "Oxidize First or Filter First?" in text


def test_microbial_barrier_and_challenge_testing_are_preserved():
    text = _text()
    for term in ("Viruses and bacteria", "Protozoa / Cryptosporidium and Giardia", "MS2 bacteriophage", "Challenge testing"):
        assert term in text
    assert "nominal pore size alone is not a validated log-removal claim" in text
    assert "below detection" in text
    assert "LRV is infinite" in text


def test_algae_and_silica_are_integrated_with_existing_threads():
    text = _text()
    assert "Cell Count Is Not Fouling Potential" in text
    assert "Silica fouling on UF/MF" in text
    assert "Silica is only an RO problem" in text


def test_integrity_defect_modes_are_broader_than_pore_size():
    text = _text()
    for defect in (
        "broken fibre",
        "pinhole",
        "potting/tubesheet defect",
        "seal/gasket leakage",
        "module housing leak",
        "manifold/connection leak",
    ):
        assert defect in text
    assert "The system barrier includes fibres, potting, seals, manifolds, module hardware and installation integrity" in text


def test_direct_and_indirect_integrity_monitoring_are_preserved():
    text = _text()
    for term in ("Indirect / continuous operational indicators", "Direct integrity tests", "pressure-decay testing", "diffusive-air-flow testing", "vacuum-hold testing"):
        assert term in text
    assert "Turbidity is low, so there is no broken fibre" in text


def test_bubble_point_and_pressure_decay_guardrails_are_preserved():
    text = _text()
    for term in ("Bubble-point physics", "surface tension", "contact angle", "larger defect can pass gas at a lower pressure"):
        assert term in text
    assert "Higher integrity-test pressure is always more sensitive" in text
    assert "ISOLATE → DRAIN/FILL AS REQUIRED → APPLY CLEAN GAS PRESSURE" in text


def test_integrity_test_plc_state_machine_is_preserved():
    text = _text()
    for term in (
        "valve isolation",
        "low/high pressure interlocks",
        "timed hold",
        "decay calculation",
        "rack lockout",
        "retest requirement before return to service",
    ):
        assert term in text
    assert "Integrity Test State Machine" in text


def test_test_zone_sensitivity_and_rack_size_are_preserved():
    text = _text()
    assert "same single broken fibre can be easier to detect in a smaller tested volume" in text
    assert "aggregating too many modules into one integrity test can dilute the signal" in text
    assert "How Big Should the Integrity-Test Zone Be?" in text


def test_lrv_is_taught_with_detection_and_regulatory_guard():
    text = _text()
    assert "LRV = log10(C_feed / C_permeate)" in text
    for term in (
        "analytical detection limits matter",
        "challenge concentration matters",
        "regulatory credit may be lower than experimental performance",
    ):
        assert term in text
    assert "One Broken Fibre, Big Plant" in text


def test_integrity_frequency_is_risk_based_not_universal():
    text = _text()
    assert "Testing and repair frequency" in text
    assert "higher failure likelihood + tighter barrier requirement + larger rack" in text
    assert "Integrity testing should always be daily/weekly/monthly" in text
    assert "How Often Should We Test?" in text


def test_maintainability_and_repairability_are_explicit():
    text = _text()
    for phrase in (
        "Can an individual rack/module be isolated?",
        "Can a broken fibre be identified?",
        "Can the module be retested before return to service?",
        "Are integrity-test and repair records auditable?",
    ):
        assert phrase in text


def test_capex_opex_and_total_water_cost_are_lifecycle_based():
    text = _text()
    for term in ("CAPEX architecture", "OPEX breakdown", "Total Water Cost (TWC)", "Economies of scale"):
        assert term in text
    assert "Double flow means double CAPEX" in text
    assert "UF cost is primarily a function of plant flow" in text


def test_flux_capex_opex_tradeoff_is_preserved():
    text = _text()
    for term in ("Higher design flux", "Lower flux", "TMP", "fouling rate", "membrane replacement"):
        assert term in text
    assert "Cheapest Plant or Cheapest Water?" in text


def test_source_water_changes_economics():
    text = _text()
    for water in ("clean groundwater", "clarified surface water", "direct raw surface water", "seawater pretreatment", "wastewater/reuse water"):
        assert water in text


def test_membrane_life_and_cip_are_sensitivity_variables_not_defaults():
    text = _text()
    assert "Do not publish one membrane-life value as a general expectation" in text
    assert "Clean More or Clean Less?" in text
    assert "If CIP restores permeability, more frequent CIP is always safer" in text
    assert "Do not copy historical concentrations/frequencies into current design defaults" in text


def test_evidence_literacy_rejects_historical_numbers_as_current_rules():
    text = _text()
    for phrase in (
        "The 2011 source reported...",
        "In this historical example...",
        "Current value must be verified against...",
    ):
        assert phrase in text
    for prohibited in (
        "universal UF design flux",
        "universal pathogen LRV",
        "universal fibre-break allowance",
        "current membrane price",
    ):
        assert prohibited in text


def test_engine_ownership_and_no_runtime_change_are_explicit():
    text = _text()
    for owner in ("app/total-pretreatment-design", "engine/shared-water-chemistry", "app/total-water-economics"):
        assert owner in text
    assert "Academy must not create a competing professional UF/MF integrity-credit or cost engine" in text
    assert "Academy runtime calculations" in text
    assert "the 360-hour curriculum allocation" in text


def test_copyright_boundary_is_explicit():
    text = _text()
    for protected in (
        "photographed pages",
        "chapter tables",
        "pressure-decay graphs",
        "LRV/fibre-break graphs",
        "CAPEX/OPEX/TWC graphs",
        "historical cost curves",
    ):
        assert protected in text
    assert "Research Basis / Sources & Further Reading" in text
