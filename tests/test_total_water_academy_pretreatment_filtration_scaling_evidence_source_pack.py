from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOTAL_WATER_ACADEMY_PRETREATMENT_FILTRATION_SCALING_EVIDENCE_SOURCE_PACK_v1.0.md"


def _text() -> str:
    assert DOC.exists(), f"Missing Academy evidence source pack: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_source_pack_defines_evidence_classification_contract():
    text = _text()
    for label in (
        "FUNDAMENTAL_PRINCIPLE",
        "PEER_REVIEWED_FINDING",
        "AGENCY_CASE_STUDY",
        "PRODUCT_SPECIFICATION",
        "VENDOR_RECOMMENDATION",
        "HISTORICAL_PRACTICE",
        "RESEARCH_OR_INNOVATION_CASE",
        "CLAIM_REQUIRING_VERIFICATION",
    ):
        assert label in text


def test_source_pack_rejects_rule_of_thumb_as_substitute_for_engineering():
    text = _text()
    assert "Rule-of-thumb safeguard" in text
    assert "Never use “rule of thumb” to hide missing engineering" in text
    for required in (
        "media-fluidization calculations",
        "bed-expansion curves",
        "pilot testing",
        "source-water characterization",
        "membrane projection",
        "scaling/speciation calculation",
        "jar testing",
    ):
        assert required in text


def test_source_pack_requires_source_labeling_for_numerical_values():
    text = _text()
    for phrase in (
        "The study reported",
        "The manufacturer recommends for this product",
        "This historical manual used",
        "In this pilot",
        "verify with current design authority",
    ):
        assert phrase in text


def test_source_pack_includes_bolto_gregory_as_high_strength_mechanistic_source():
    text = _text()
    assert "Bolto & Gregory (2007)" in text
    assert "peer-reviewed review" in text
    for term in (
        "polymer conformation",
        "polymer bridging",
        "charge neutralization",
        "polymer shear degradation",
        "residual polymer",
        "streaming-current",
    ):
        assert term in text
    assert "more polymer will improve it further" in text


def test_source_pack_teaches_granular_filtration_as_more_than_sieving():
    text = _text()
    assert "filtration is not simply a sieve" in text
    for term in (
        "deep-bed filtration",
        "attachment/adsorption",
        "coarse-to-fine grading",
        "head loss",
        "filter-to-waste",
        "mudballs",
        "compaction",
        "channeling",
    ):
        assert term in text


def test_source_pack_does_not_hardcode_multimedia_bed_recipe():
    text = _text()
    assert "Do not teach a fixed anthracite:sand:garnet depth fraction as universal" in text
    assert "A multi-media filter is always 55% anthracite, 30% sand and 15% garnet" in text
    assert "Design the bed from properties" in text
    for term in (
        "effective size",
        "specific gravity",
        "UC",
        "expansion curves",
    ):
        assert term in text


def test_source_pack_replaces_fixed_backwash_rate_with_expansion_reasoning():
    text = _text()
    assert "replace fixed flow rules with fluidization reasoning" in text
    assert "Backwash every filter at 15 gpm/ft²" in text
    for term in (
        "desired bed expansion",
        "water temperature/viscosity",
        "underdrain limits",
        "manufacturer bed-expansion curve",
        "Cold Morning Backwash",
    ):
        assert term in text


def test_source_pack_teaches_multisignal_filter_termination():
    text = _text()
    assert "Do not decide to backwash from only one signal" in text
    for signal in (
        "terminal head loss",
        "effluent turbidity/particle breakthrough",
        "filter run time",
        "upstream water-quality change",
        "available wash-water inventory",
    ):
        assert signal in text
    assert "Backwash Now?" in text


def test_source_pack_teaches_cartridge_rating_context_and_no_microbe_credit():
    text = _text()
    assert "Nominal versus absolute rating" in text
    assert "5 micron” is incomplete" in text
    assert "must **not** be presented as a validated microbial barrier" in text
    assert "Nominal 5 µm vs Absolute 5 µm" in text


def test_source_pack_keeps_greensandplus_as_product_case():
    text = _text()
    assert "GreensandPlus as a product case" in text
    for term in (
        "catalytic oxidation media concept",
        "manganese-dioxide-coated media",
        "oxidant demand",
        "breakthrough and run-length reasoning",
    ):
        assert term in text
    for product_specific in (
        "service-flow range",
        "chlorine contact time",
        "oxidant-demand formula",
        "loading capacity",
        "backwash rate",
    ):
        assert product_specific in text


def test_source_pack_keeps_opuntia_as_research_innovation_case():
    text = _text()
    assert "Miller et al. (2008)" in text
    assert "research/innovation case" in text
    assert "adsorption/bridging" in text
    assert "technology readiness and scale-up" in text
    assert "Do NOT teach" in text
    assert "Research to Plant Gate Review" in text


def test_source_pack_teaches_cryptosporidium_as_barrier_problem():
    text = _text()
    assert "Cryptosporidium — barrier thinking, not “disinfect harder”" in text
    assert "resistant to conventional chlorine/chloramine disinfection" in text
    for term in (
        "coagulation",
        "flocculation",
        "sedimentation",
        "filtration",
        "pH",
        "NOM",
        "turbidity",
    ):
        assert term in text
    assert "Build the Barriers" in text


def test_source_pack_adds_authoritative_chlorine_nombromide_chemistry_layer():
    text = _text()
    assert "Chlorine, NOM, humics and bromide" in text
    assert "WHO Environmental Health Criteria" in text
    for term in (
        "HOCl ⇌ H+ + OCl-",
        "NOM provides organic precursor",
        "bromide",
        "DBP formation",
        "precursor removal before chlorination",
    ):
        assert term in text
    assert "Dose, demand, residual, speciation and contact time are different concepts" in text


def test_source_pack_complements_khan_chlorination_school_of_thought():
    text = _text()
    assert "Complement to Khan et al. chlorination school-of-thought note" in text
    for term in (
        "disinfection objective",
        "oxidant demand",
        "hydraulic accessibility",
        "membrane compatibility",
        "NOM/AOM/TEP",
        "dechlorination",
        "downstream biological regrowth",
    ):
        assert term in text


def test_source_pack_marks_filmtec_values_as_historical_vendor_guidance():
    text = _text()
    assert "Historical FilmTec scale-control manual" in text
    assert "published 2000" in text
    assert "Treat them as one source" in text
    for prohibited_default in (
        "stated LSI/S&DSI limits with inhibitor",
        "stated SHMP concentrate/feed dosage",
        "recommendation to use inhibitor above a particular recovery",
        "specific cleaning intervals",
    ):
        assert prohibited_default in text
    assert "timeless membrane limit" in text


def test_source_pack_uses_amjad_hooley_for_induction_not_dose_rules():
    text = _text()
    assert "Amjad & Hooley (1994)" in text
    for term in (
        "induction/lag time",
        "nucleation",
        "crystal growth",
        "polymer molecular weight",
        "temperature dependence",
    ):
        assert term in text
    assert "must **not** become RO feed-dose guidance" in text
    assert "Delay is not equilibrium" in text


def test_source_pack_uses_reclamation_case_to_teach_evidence_not_universal_shmp_rule():
    text = _text()
    assert "Bureau of Reclamation high-recovery study" in text
    assert "tested magnetic device" in text
    assert "tested high-voltage capacitance device" in text
    assert "2 mg/L SHMP always permits 93% recovery" in text
    assert "A mechanism claim or vendor testimonial does not replace controlled testing" in text
    assert "Would You Buy the Device?" in text


def test_source_pack_preserves_tail_element_diagnostic_principle():
    text = _text()
    assert "Tail-element monitoring and spatial diagnostics" in text
    assert "lead elements can see the highest feed foulant loading" in text
    assert "tail elements see the most concentrated feed" in text
    assert "train-average normalized data can hide a local problem" in text


def test_source_pack_adds_engineering_evidence_literacy_competencies():
    text = _text()
    for competency in (
        "ENG-EVIDENCE-01",
        "ENG-EVIDENCE-02",
        "ENG-EVIDENCE-03",
    ):
        assert competency in text
    assert "Where did this number come from, and why is it applicable here?" in text


def test_source_pack_maps_across_existing_curriculum_without_new_hours():
    text = _text()
    assert "does not add hours to the 360-hour curriculum" in text
    for level in (
        "Level 1",
        "Level 2",
        "Level 3",
        "Level 4",
        "Level 7",
        "Level 8",
        "Level 9",
        "Level 10",
    ):
        assert level in text


def test_source_pack_preserves_current_design_authority_boundary():
    text = _text()
    assert "does not authorize Academy to set production design criteria" in text
    for criterion in (
        "coagulation dose",
        "polymer dose",
        "multimedia filter loading",
        "backwash rate",
        "disinfection dose/CT",
        "RO recovery",
        "antiscalant dose",
        "scaling limit",
    ):
        assert criterion in text
    for owner in (
        "app/total-pretreatment-design",
        "app/total-ro-design",
        "engine/shared-water-chemistry",
    ):
        assert owner in text


def test_source_pack_preserves_provenance_copyright_and_source_age_guard():
    text = _text()
    assert "Research Basis / Sources & Further Reading" in text
    for protected in (
        "manual pages",
        "manufacturer brochure layouts",
        "figures",
        "photographs",
        "charts",
        "tables",
        "paper figures",
        "long passages",
    ):
        assert protected in text
    assert "complete **2026 state of the art**" in text
    assert "current manufacturer documentation" in text
    assert "current regulations" in text


def test_source_pack_states_content_architecture_not_finished_lessons():
    text = _text()
    assert "Completion standard for future lesson authoring" in text
    assert "content/source architecture" in text
    assert "not proof that every learner-facing screen has already been authored" in text
