from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOTAL_WATER_ACADEMY_ALGAL_BLOOMS_SWRO_RESILIENCE_SOURCE_MAP_v1.0.md"


def _text() -> str:
    assert DOC.exists(), f"Missing Academy algal-bloom source map: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_source_map_identifies_villacorte_reference_and_historical_guard():
    text = _text()
    assert "Algal Blooms and Membrane Based Desalination Technology" in text
    assert "Loreen Ople Villacorte" in text
    assert "2014" in text
    assert "must not be silently promoted to universal 2026 design criteria" in text
    assert "mechanism" in text
    assert "numerical design criterion" in text


def test_source_map_complements_existing_swro_sources_instead_of_duplicating_them():
    text = _text()
    assert "TOTAL_WATER_ACADEMY_SWRO_PRETREATMENT_ALGAL_BLOOMS_SOURCE_MAP_v1.0.md" in text
    assert "TOTAL_WATER_ACADEMY_SWRO_INTAKES_OUTFALLS_MARINE_INFRASTRUCTURE_SOURCE_MAP_v1.0.md" in text
    assert "Tabatabai 2014" in text
    assert "Missimer et al. 2013" in text
    assert "marine event → intake → pretreatment → membrane fouling → operation → recovery → lifecycle reliability" in text


def test_source_map_teaches_bloom_as_dynamic_event_not_static_number():
    text = _text()
    assert "time-varying biological, chemical, colloidal and hydraulic event" in text
    for term in (
        "background",
        "initiation / growth",
        "rapid growth",
        "peak biomass",
        "stationary / nutrient stress",
        "senescence / decay",
        "post-bloom recovery",
    ):
        assert term in text


def test_source_map_distinguishes_hab_red_tide_and_non_toxic_operational_risk():
    text = _text()
    assert "not every red tide is harmful" in text
    assert "not every harmful bloom is red" in text
    assert "not every harmful bloom is toxic" in text
    assert "If the bloom is non-toxic, it is not a serious SWRO problem" in text
    assert "High biomass and AOM can overwhelm pretreatment" in text


def test_source_map_teaches_species_as_engineering_risk_profiles():
    text = _text()
    for group in (
        "diatoms",
        "dinoflagellates",
        "haptophytes",
        "raphidophytes",
        "cyanobacteria",
    ):
        assert group in text
    for variable in (
        "cell size",
        "chain/colony formation",
        "motility",
        "toxin potential",
        "AOM/TEP production",
        "bloom duration",
    ):
        assert variable in text
    assert "Meet the Bloom" in text


def test_source_map_teaches_aom_eom_iom_and_bloom_phase():
    text = _text()
    assert "Algal organic matter (AOM)" in text
    assert "Extracellular organic matter (EOM)" in text
    assert "Intracellular organic matter (IOM)" in text
    assert "Removing intact algal cells removes the bloom problem" in text
    assert "Senescence and cell lysis can release IOM/AOM and nutrients" in text
    assert "The Bloom Is Over... Or Is It?" in text


def test_source_map_teaches_tep_as_hydrated_sticky_conditioning_layer():
    text = _text()
    for term in (
        "highly hydrated",
        "gel-like",
        "sticky",
        "conditioning layer",
        "bacterial attachment",
        "biofilm development",
    ):
        assert term in text
    assert "TEP is just another suspended-solid concentration" in text
    assert "From Invisible Gel to Biofilm" in text


def test_source_map_protects_cell_count_vs_fouling_distinction():
    text = _text()
    assert "Cell concentration is not fouling potential" in text
    assert "cell count is useful for bloom magnitude" in text
    assert "neither alone fully predicts membrane-fouling potential" in text
    assert "The highest cell count is the worst membrane-fouling day" in text
    assert "Cell Count vs Fouling Detective" in text


def test_source_map_connects_solution_chemistry_to_algal_biopolymer_fouling():
    text = _text()
    for term in (
        "pH",
        "ionic strength",
        "Ca2+",
        "cation bridging",
        "polymer charge",
        "membrane surface chemistry",
    ):
        assert term in text
    assert "Organic fouling is independent of seawater chemistry because the foulant is organic" in text
    assert "Alginate Is Not Algae" in text
    assert "model fidelity matters" in text


def test_source_map_distinguishes_uf_surface_fouling_from_capillary_plugging():
    text = _text()
    assert "Surface/cake fouling" in text
    assert "Axial/capillary plugging" in text
    for lever in (
        "shorten filtration-cycle duration",
        "lower flux",
        "forward flush",
        "cross-flow/bleed",
        "improve upstream cell removal",
    ):
        assert lever in text
    assert "Where Did My UF Area Go?" in text
    assert "capacity derating can protect reliability" in text


def test_source_map_keeps_gmf_daf_uf_as_tradeoffs():
    text = _text()
    assert "Granular media filtration (GMF/DMF)" in text
    assert "Dissolved air flotation (DAF)" in text
    assert "Ultrafiltration (UF)" in text
    assert "shift behavior toward surface/cake blocking" in text
    assert "particularly suited to removal of low-density algal/floc particles" in text
    assert "UF eliminates algal-bloom risk" in text
    assert "UF changes where and how the risk appears" in text


def test_source_map_distinguishes_organic_fouling_and_biofouling():
    text = _text()
    assert "Organic fouling versus biofouling" in text
    assert "Organic fouling and biofouling are the same thing" in text
    assert "biological growth is a separate process" in text
    assert "AOM pre-fouling can accelerate subsequent biofilm development" in text


def test_source_map_requires_post_bloom_surveillance():
    text = _text()
    assert "Delayed post-bloom biofouling" in text
    assert "Once the water clears, the plant can immediately return to normal operating mode" in text
    assert "POST-BLOOM SURVEILLANCE" in text
    assert "The 10-Day Surprise" in text
    assert "Do not exit bloom mode based only on lower cell count" in text


def test_source_map_uses_multi_tier_monitoring_not_one_parameter():
    text = _text()
    assert "no single parameter describes bloom risk" in text
    for term in (
        "cell count",
        "chlorophyll-a",
        "TEP",
        "biopolymer concentration / LC-OCD",
        "MFI / MFI-UF",
        "SDI",
        "ATP",
        "AOC",
        "BDOC",
        "normalized permeability",
        "feed-channel pressure drop",
    ):
        assert term in text
    assert "Bloom Early-Warning Dashboard" in text


def test_source_map_defines_bloom_response_state_machine():
    text = _text()
    for state in (
        "NORMAL",
        "WATCH",
        "BLOOM RESPONSE",
        "SEVERE BLOOM",
        "RECOVERY",
        "POST-BLOOM SURVEILLANCE",
    ):
        assert state in text
    assert "When Can We Return to Normal?" in text
    assert "deliberate plant derating" in text


def test_source_map_crosslinks_subsurface_intake_without_making_it_universal():
    text = _text()
    assert "Subsurface intake as bloom-resilience strategy" in text
    assert "A bloom-prone coast should always use beach wells" in text
    assert "hydrogeologic investigation" in text
    assert "Avoid the Bloom or Treat the Bloom?" in text


def test_source_map_distinguishes_toxin_rejection_from_operability():
    text = _text()
    assert "Toxins: distinguish public-health removal from operational fouling" in text
    assert "RO rejects the toxin, so the bloom does not matter" in text
    assert "plant operability and membrane protection remain critical" in text


def test_source_map_carries_bloom_response_into_residuals_and_controls():
    text = _text()
    for residual in (
        "DAF float sludge",
        "coagulant-rich solids",
        "GMF backwash volume",
        "UF backwash volume",
        "CEB waste",
        "CIP waste",
    ):
        assert residual in text
    for control in (
        "bloom-watch permissive",
        "UF high-TMP alarm",
        "maximum safe flux override",
        "operator-confirmed derating",
        "event historian tags",
    ):
        assert control in text


def test_source_map_requires_design_for_variability_and_event_risk():
    text = _text()
    assert "variability" in text
    for term in (
        "normal versus bloom design basis",
        "worst credible episodic event",
        "pretreatment redundancy",
        "hydraulic turndown",
        "sludge handling capacity",
        "emergency water-supply obligations",
    ):
        assert term in text
    assert "Design for the average annual water quality and add a safety factor" in text


def test_source_map_requires_pilot_to_cover_actual_bloom_risk():
    text = _text()
    assert "Pilot-testing philosophy for bloom-prone SWRO" in text
    assert "seasonal coverage" in text
    assert "bloom-season operation if possible" in text
    assert "actual local species/AOM" in text
    assert "The pilot ran for three months without trouble, so the design is validated" in text
    assert "Three non-bloom months may not challenge the process against the design event" in text


def test_source_map_contains_reusable_misconception_library():
    text = _text()
    for misconception in (
        "Red tide = harmful algal bloom",
        "Non-toxic bloom = no desalination risk",
        "Cell count = membrane fouling potential",
        "Low SDI = low biofouling risk",
        "Alginate is a complete surrogate for AOM",
        "The bloom ends when cells fall",
        "Organic fouling = biofouling",
        "A subsurface intake is always the best bloom solution",
    ):
        assert misconception in text


def test_source_map_defines_high_value_interactive_exercises():
    text = _text()
    for mission in (
        "Bloom Lifecycle Simulator",
        "Species Is Not Just a Name",
        "TEP Hydrogel Explorer",
        "Calcium Bridge",
        "GMF Depth or Surface Blocking?",
        "UF Is the Shield — Until It Isn't",
        "Build the Bloom PLC State Machine",
        "Residuals During the Worst Week",
        "Full SWRO Bloom Resilience Defense",
    ):
        assert mission in text


def test_source_map_defines_guided_engineering_solution_mode_for_bloom_case():
    text = _text()
    assert "Guided Engineering Solution Mode — full example" in text
    assert "Can the pretreatment maintain sufficient hydraulic capacity" in text
    assert "Does acceptable SDI prove the organic risk is low?" in text
    assert "planned plant derating" in text
    assert "Do not wait for severe RO performance deterioration before acting" in text


def test_source_map_maps_content_across_levels_without_creating_new_hours():
    text = _text()
    for level in (
        "Level 1",
        "Level 2",
        "Level 3",
        "Level 4",
        "Level 6",
        "Level 7",
        "Level 8",
        "Level 9",
        "Level 10",
    ):
        assert level in text
    assert "Level 10 capstone requirement — Bloom Resilience Annex" in text


def test_source_map_preserves_engineering_owner_boundaries():
    text = _text()
    assert "Academy does **not** own project-grade engineering models" in text
    assert "pretreatment sizing" in text
    assert "RO membrane projection" in text
    assert "ecological bloom prediction" in text
    assert "HAB forecasting" in text
    assert "app/total-pretreatment-design" in text
    assert "app/total-ro-design" in text
    assert "independent production **HAB prediction engine**" in text


def test_source_map_preserves_provenance_current_state_and_copyright_rules():
    text = _text()
    assert "Research Basis / Sources & Further Reading" in text
    assert "Do not label this single 2014 dissertation as the complete" in text
    assert "2026 state of the art." in text
    assert "supplement it with newer peer-reviewed literature" in text
    assert "copyrighted" in text.lower()
    for protected in (
        "publisher pages",
        "figures",
        "microscopy panels",
        "tables",
        "long passages",
        "page layouts",
    ):
        assert protected in text
    assert "build original TWDA graphics" in text


def test_source_map_states_it_is_content_architecture_until_authored():
    text = _text()
    assert "Completion criteria for future lesson authoring" in text
    assert "content/source architecture" in text
    assert "not proof that every lesson screen is already implemented" in text
