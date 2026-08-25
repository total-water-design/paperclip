from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TOTAL_WATER_ACADEMY_SWRO_INTAKES_OUTFALLS_SOURCE_MAP_v1.0.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_source_identity_and_doi_are_preserved():
    text = read_doc()
    assert "Thomas M. Missimer" in text
    assert "Burton Jones" in text
    assert "Robert G. Maliva" in text
    assert "Intakes and Outfalls for Seawater Reverse-Osmosis Desalination Facilities" in text
    assert "10.1007/978-3-319-13203-7" in text
    assert "2015" in text


def test_source_maps_across_existing_academy_levels():
    text = read_doc().lower()
    for level in ("level 1", "level 3", "level 4", "level 6", "level 8", "level 9", "level 10"):
        assert level in text


def test_intake_and_outfall_are_taught_as_full_system_boundaries():
    text = read_doc().lower()
    assert "the intake is the first treatment barrier" in text
    assert "the outfall is the final engineered environmental interface" in text
    assert "marine source → intake location/type" in text
    assert "receiving environment → monitoring" in text


def test_intake_family_literacy_is_complete():
    text = read_doc().lower()
    for intake in (
        "conventional shoreline/open-ocean intake",
        "velocity cap",
        "passive/cylindrical wedgewire screens",
        "vertical/beach wells",
        "slant/angle wells",
        "horizontal wells",
        "radial collector wells",
        "beach infiltration galleries",
        "seabed infiltration galleries",
        "tunnel conveyance",
    ):
        assert intake in text


def test_intake_selection_is_multicriteria_not_a_single_algorithm():
    text = read_doc().lower()
    for concept in (
        "required reliable capacity",
        "geology/hydrogeology",
        "bathymetry and coastal morphology",
        "impingement/entrainment risk",
        "constructability",
        "maintainability and access",
        "corrosion/biofouling exposure",
        "pretreatment consequences",
        "capex/opex and project risk",
    ):
        assert concept in text
    assert "not a deterministic universal intake-selection algorithm" in text


def test_deep_intake_case_is_used_to_challenge_deeper_is_always_better():
    text = read_doc().lower()
    assert "deeper is always cleaner" in text
    assert "red sea deep-intake case" in text
    assert "irregular tep/toc/algae profiles" in text
    assert "insufficient to justify a different general pretreatment train" in text


def test_passive_screen_teaching_distinguishes_velocity_terms():
    text = read_doc().lower()
    assert "approach velocity and through-screen/through-slot velocity are not interchangeable" in text
    assert "effective screen area = design flow / selected allowable approach velocity" in text
    for requirement in (
        "open-area correction",
        "fouling/blockage allowance",
        "nonuniform flow distribution",
        "clean/dirty headloss",
        "current site-specific permitting requirements",
    ):
        assert requirement in text
    assert "not a complete passive-screen design engine" in text


def test_marine_hydraulics_and_lifecycle_concepts_are_explicit():
    text = read_doc().lower()
    for concept in (
        "screen/conveyance headloss",
        "long-term roughness and marine growth",
        "surge/water-hammer concepts",
        "duty/standby philosophy",
        "clean screens and clean conveyance",
        "fouled screens",
        "conservative long-term roughness",
    ):
        assert concept in text


def test_outfall_dense_brine_and_diffuser_topics_are_explicit():
    text = read_doc().lower()
    for concept in (
        "concentrate density and negative buoyancy",
        "single-port versus multiport diffuser",
        "inclined dense jets",
        "initial dilution",
        "near-field mixing",
        "bottom interaction and re-entrainment",
        "density currents",
        "far-field transport",
        "intake/outfall recirculation risk",
    ):
        assert concept in text


def test_outfall_modeling_hierarchy_requires_model_literacy():
    text = read_doc().lower()
    for concept in (
        "integral near-field model",
        "cfd",
        "hydrodynamic far-field model",
        "coupled near-/far-field modeling",
        "physical modeling",
        "field monitoring/calibration",
    ):
        assert concept in text
    assert "model assumptions, applicability, calibration and validation" in text
    assert "near-field dilution result does not by itself prove acceptable far-field environmental performance" in text


def test_environmental_thread_covers_impingement_entrainment_and_monitoring():
    text = read_doc().lower()
    assert "impingement" in text
    assert "entrainment" in text
    for phase in ("before design / baseline", "construction", "operation"):
        assert phase in text
    for concept in (
        "species/life stages",
        "seasonal/diel variability",
        "protected species observations",
        "outfall plume/salinity",
        "model validation",
    ):
        assert concept in text


def test_project_development_and_finance_connection_is_present():
    text = read_doc().lower()
    for concept in (
        "site feasibility",
        "permitting schedule",
        "critical path",
        "construction weather windows",
        "availability guarantees",
        "insurance and project risk",
        "lender/owner confidence in reliability",
    ):
        assert concept in text
    assert "the cheapest intake is not the cheapest project" in text
    assert "unreliable raw-water supply can undermine the feasibility/bankability" in text


def test_capstone_requires_marine_boundary_defense():
    text = read_doc().lower()
    for item in (
        "intake technology and siting basis",
        "intake hydraulics/pumping philosophy",
        "concentrate characterization",
        "outfall/disposal strategy",
        "intake/outfall recirculation check strategy",
        "monitoring plan",
        "reliability/redundancy/o&m philosophy",
    ):
        assert item in text


def test_common_misconceptions_are_protected():
    text = read_doc().lower()
    for misconception in (
        "the intake is just civil infrastructure",
        "the outfall is just the last pipe",
        "deeper seawater is always better feed water",
        "a passive screen eliminates pretreatment",
        "approach velocity and through-slot velocity are the same",
        "a velocity cap eliminates entrainment",
        "more diffuser ports always improve dilution",
        "near-field dilution proves far-field compliance",
        "historical regulatory values are current global design criteria",
    ):
        assert misconception in text


def test_current_2015_values_are_not_promoted_to_2026_defaults():
    text = read_doc().lower()
    assert "source-labelled historical/reference values" in text
    assert "not automatic 2026 twds design criteria" in text
    assert "revalidate regulatory and project-design limits" in text


def test_no_project_grade_marine_solver_is_invented():
    text = read_doc().lower()
    assert "did not identify a dedicated validated twds marine-intake/outfall/coastal-dispersion project-design engine" in text
    for prohibited in (
        "project-grade marine intake structural design",
        "project-grade tunnel transient analysis",
        "project diffuser sizing/compliance guarantees",
        "near-/far-field salinity plume prediction",
        "regulatory mixing-zone determination",
    ):
        assert prohibited in text


def test_specialist_suite_owners_remain_authoritative_for_owned_calculations():
    text = read_doc().lower()
    for owner in (
        "app/total-pretreatment-design",
        "app/total-ro-design",
        "engine/shared-water-chemistry",
        "app/total-water-balance",
        "app/total-zld-design",
        "app/total-water-economics",
    ):
        assert owner in text


def test_copyright_policy_requires_original_academy_visuals_and_matrices():
    text = read_doc().lower()
    assert "springer book is copyright protected" in text
    assert "create original academy diagrams" in text
    assert "create original comparison matrices" in text
    assert "must not be copied into twda" in text


def test_interactive_missions_are_defined():
    text = read_doc().lower()
    for mission in (
        "intake family selector",
        "the intake is pretreatment",
        "algal bloom day",
        "deeper is always better?",
        "passive screen tradeoff",
        "tunnel critical path",
        "near field or far field?",
        "will the brine return?",
        "marine monitoring plan",
        "capstone marine boundary defense",
    ):
        assert mission in text
