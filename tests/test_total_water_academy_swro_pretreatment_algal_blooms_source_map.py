from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOTAL_WATER_ACADEMY_SWRO_PRETREATMENT_ALGAL_BLOOMS_SOURCE_MAP_v1.0.md"


def _text() -> str:
    assert DOC.exists(), f"Missing Academy source map: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_source_map_identifies_authoritative_supplied_source_and_age_guard():
    text = _text()
    assert "Coagulation and Ultrafiltration in Seawater Reverse Osmosis Pretreatment" in text
    assert "S. Assiyeh Alizadeh Tabatabai" in text
    assert "2014" in text
    assert "not automatic 2026 TWDS design criteria" in text
    assert "current source-water characterization and pilot data" in text


def test_source_map_teaches_pretreatment_as_reliability_system():
    text = _text()
    assert "SWRO pretreatment is a reliability system" in text
    for term in (
        "hydraulic capacity",
        "particulate/colloidal loading",
        "organic fouling potential",
        "biological fouling potential",
        "RO feed channels/spacers",
        "contracted plant availability",
    ):
        assert term in text


def test_source_map_connects_unit_operations_to_swro_pretreatment():
    text = _text()
    for term in (
        "Darcy flow and resistance-in-series",
        "Cake/gel filtration",
        "Carman-Kozeny reasoning",
        "Compressible cakes",
        "Mixing, G and Gt",
        "Perikinetic and orthokinetic aggregation",
    ):
        assert term in text


def test_source_map_preserves_core_swro_pretreatment_technology_set():
    text = _text()
    for term in (
        "Granular media filtration",
        "dissolved air flotation",
        "microfiltration",
        "ultrafiltration",
        "cartridge filtration",
        "inline coagulation",
        "sedimentation",
    ):
        assert term.lower() in text.lower()


def test_source_map_teaches_algal_cells_aom_tep_as_distinct_risks():
    text = _text()
    for term in (
        "algal cells",
        "algal organic matter (AOM)",
        "transparent exopolymer particles (TEP)",
        "biopolymers",
        "conditioning layer",
        "biofilm",
    ):
        assert term in text
    assert "If UF removes the algal cells, the RO is safe" in text


def test_source_map_teaches_sdi_limitations_and_mfi_uf():
    text = _text()
    assert "SDI alone predicts all RO fouling" in text
    assert "MFI / MFI-UF" in text
    assert "MFI-UF was developed to capture smaller foulants" in text
    assert "Do not teach one MFI threshold as globally valid" in text


def test_source_map_keeps_daf_gmf_uf_as_tradeoff_not_single_answer():
    text = _text()
    assert "no single train is universally optimal" in text
    assert "DAF solves the whole algal-bloom problem" in text
    assert "UF is not immune" in text
    assert "transition from desired depth filtration toward surface/cake blocking" in text


def test_source_map_distinguishes_inline_from_conventional_coagulation():
    text = _text()
    assert "Conventional coagulation goal" in text
    assert "Inline coagulation/UF goal" in text
    for term in (
        "lower pore blocking",
        "more permeable cake/gel structure",
        "better backwashability",
        "lower non-backwashable fouling",
    ):
        assert term in text
    assert "Large settleable flocs are not necessarily required" in text


def test_source_map_calls_out_coagulant_and_ph_tradeoffs():
    text = _text()
    assert "more is better" in text
    for term in (
        "coagulant type",
        "dose",
        "pH",
        "rapid-mix G",
        "residual metal",
        "sludge production",
    ):
        assert term in text


def test_source_map_teaches_backwash_ceb_cip_hierarchy():
    text = _text()
    assert "Hydraulic backwash" in text
    assert "Chemically enhanced backwash (CEB)" in text
    assert "Cleaning in place (CIP)" in text
    for term in (
        "backwashable fouling",
        "non-backwashable fouling",
        "CEB-recoverable fouling",
        "CIP-recoverable fouling",
        "irreversible residual loss",
    ):
        assert term in text


def test_source_map_teaches_flux_as_capacity_and_fouling_tradeoff():
    text = _text()
    assert "Flux as a design and operating lever" in text
    assert "accelerate TMP development" in text
    assert "compress AOM cake/gel layers" in text
    assert "require more membrane area" in text
    assert "Flux versus robustness" in text


def test_source_map_keeps_low_mwco_uf_as_research_tradeoff_not_default():
    text = _text()
    assert "10 kDa and 150 kDa" in text
    assert "surface porosity" in text
    assert "Choose the tightest UF membrane available" in text
    assert "Do not present 10 kDa as a universal commercial SWRO pretreatment recommendation" in text


def test_source_map_keeps_precoating_as_research_not_production_standard():
    text = _text()
    assert "Ferric-hydroxide pre-coating" in text
    assert "research-method and innovation case" in text
    assert "not as a standard TWDS process recommendation" in text
    assert "technology readiness" in text.lower()


def test_source_map_carries_residuals_and_chemical_burden_into_plant_design():
    text = _text()
    for term in (
        "spent UF backwash",
        "CEB waste",
        "CIP waste",
        "coagulant-rich sludge",
        "DAF float sludge",
        "sludge thickening/dewatering",
    ):
        assert term in text
    assert "Chemical cost is only the cost of FeCl3 per tonne" in text


def test_source_map_adds_swro_pretreatment_controls_and_bloom_state_machine():
    text = _text()
    assert "NORMAL → BLOOM WATCH → BLOOM RESPONSE → RECOVERY → NORMAL" in text
    for term in (
        "chlorophyll-a",
        "UF TMP",
        "permeability",
        "backwash frequency",
        "CEB frequency",
        "RO feed DP",
    ):
        assert term in text


def test_source_map_defines_advanced_capstone_pretreatment_defense():
    text = _text()
    assert "Pretreatment Design Basis & Operating Philosophy" in text
    for term in (
        "source-water risks",
        "coagulation philosophy",
        "normal and bloom operating flux",
        "backwash/CEB/CIP philosophy",
        "pilot-testing plan",
    ):
        assert term in text


def test_source_map_defines_high_value_interactive_missions():
    text = _text()
    for mission in (
        "Bloom Early-Warning Dashboard",
        "GMF Surface-Blocking Mission",
        "DAF Bubble-Floc Challenge",
        "UF Flux vs TMP Lab",
        "SDI vs MFI Detective",
        "TEP Conditioning-Layer Animation",
        "Inline Coagulation Mixer",
        "Backwashability Ladder",
        "10 kDa vs 150 kDa Research Case",
        "Full SWRO Pretreatment Defense",
    ):
        assert mission in text


def test_source_map_preserves_specialist_engine_ownership():
    text = _text()
    assert "Academy does not own" in text
    assert "app/total-pretreatment-design" in text
    assert "app/total-ro-design" in text
    assert "must not fork them into an independent production pretreatment engine" in text


def test_source_map_preserves_copyright_and_provenance_rules():
    text = _text()
    assert "copyrighted" in text.lower()
    assert "must not reproduce its figures, tables, diagrams, long passages or publisher layout" in text
    assert "Research Basis / Sources & Further Reading" in text
    assert "supplement this 2014 source with newer peer-reviewed" in text
