from pathlib import Path

from academy_content import LEVELS, TOTAL_GUIDED_HOURS, validate_curriculum

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "TOTAL_WATER_ACADEMY_UF_MEMBRANE_CLEANING_GILABERT_ORIOL_SOURCE_MAP_v1.0.md"


def text() -> str:
    assert SOURCE.is_file(), f"Missing Gilabert-Oriol UF cleaning source map: {SOURCE}"
    return SOURCE.read_text(encoding="utf-8")


def test_source_identifies_authoritative_book_and_current_corroboration():
    value = text()
    assert "Guillem Gilabert-Oriol" in value
    assert "Ultrafiltration Membrane Cleaning Processes" in value
    assert "De Gruyter, 2021" in value
    assert "10.1515/9783110715149" in value
    assert "Morten Lykkegaard Christensen" in value
    assert "IWA Publishing, 2024" in value
    assert "DuPont Water Solutions" in value


def test_source_is_primarily_mapped_to_l03_m04_without_changing_hours():
    value = text()
    assert "L03-M04 — MF/UF Pretreatment and Fouling Risk" in value
    assert "UF Membrane Cleaning, Recovery & Cleaning Optimization" in value
    assert "should not add guided hours" in value
    assert TOTAL_GUIDED_HOURS == 360
    assert sum(level["hours"] for level in LEVELS) == 360
    assert validate_curriculum() == []


def test_cleaning_hierarchy_distinguishes_hydraulic_ceb_and_cip():
    value = text()
    assert "filtration → hydraulic cleaning → CEB → CIP" in value
    assert "Hydraulic cleaning" in value
    assert "Chemically enhanced backwash (CEB)" in value
    assert "CIP" in value
    assert "CEB and CIP are interchangeable" in value
    assert "False. They differ in function, intensity, frequency and restoration role." in value


def test_backwash_optimization_teaches_incremental_value_not_a_two_step_rule():
    value = text()
    assert "factorial Design of Experiments (DoE) and ANOVA" in value
    assert "prove the incremental value of every cleaning substep" in value
    assert 'The engineering significance is **not** "use only two steps."' in value
    assert "What physical mechanism is this step intended to provide?" in value
    assert "What happens if it is removed?" in value


def test_doe_and_validation_are_first_class_cleaning_competencies():
    value = text()
    for phrase in (
        "define factors → define responses → design experiment",
        "analyze main effects/interactions",
        "validate side-by-side",
        "confirm long-term TMP behavior",
        "ANOVA",
        "controlled validation",
    ):
        assert phrase in value


def test_tmp_cycle_model_separates_filtration_bw_and_ceb_effects():
    value = text()
    assert "TMP sawtooth model" in value
    assert "ΔTMP_filtration" in value
    assert "ΔTMP_BW" in value
    assert "ΔTMP_CEB" in value
    for phrase in (
        "within-cycle reversible increase",
        "post-backwash baseline",
        "long-term baseline drift",
        "post-CEB reset",
        "eventual CIP trigger",
    ):
        assert phrase in value


def test_empirical_model_extrapolation_is_explicitly_prohibited():
    value = text()
    assert "Model envelope and extrapolation discipline" in value
    assert "model applicability envelope" in value
    assert "Revalidate or refit" in value
    assert "An empirical TMP model can be extrapolated to any UF" in value
    assert "False. State and respect the validation envelope." in value


def test_whole_system_metrics_include_availability_recovery_net_production_and_cost():
    value = text()
    assert "Availability = productive filtration time / total elapsed time" in value
    assert "Recovery = useful product water / feed water" in value
    assert "Source cleaning/process efficiency = Availability × Recovery" in value
    assert "source's process-efficiency definition" in value
    for phrase in (
        "net production",
        "water consumed for cleaning",
        "chemical mass per treated volume",
        "energy",
        "labor",
        "Total Water Cost",
    ):
        assert phrase in value


def test_chemical_burden_is_not_reduced_to_concentration_alone():
    value = text()
    assert "Continuous Equivalent Chemical" in value
    assert "chemical burden per treated feed/product volume and time basis" in value
    assert "concentration alone does not describe chemical burden" in value
    for phrase in (
        "chemical active mass",
        "number of events per day/week",
        "chemical mass per m³",
    ):
        assert phrase in value


def test_overcleaning_and_undercleaning_are_both_taught_as_risks():
    value = text()
    assert "Under-cleaning can lead to" in value
    assert "Over-cleaning can lead to" in value
    assert "Do not make \"lower TMP after cleaning\" the only optimization objective." in value
    assert "could the CEB be more frequent or more intense than necessary?" in value
    assert "must **not** teach automatic dose reduction" in value


def test_transition_downtime_is_counted_not_only_nominal_backwash_seconds():
    value = text()
    for phrase in (
        "pump deceleration",
        "valve closure/opening time",
        "blower start/stop",
        "chemical displacement",
        "repressurization",
        "filtrate-to-waste stabilization",
    ):
        assert phrase in value
    assert "same nominal backwash seconds can have different availability" in value


def test_uf_to_ro_cleaning_interface_is_explicit_and_protects_downstream_ro():
    value = text()
    assert "UF → RO interface" in value
    for phrase in (
        "chemical injected too late",
        "inadequate displacement/rinse",
        "diffusion/backflow",
        "dead volume",
        "incorrect valve sequence",
        "dedicated post-CEB rinse/flush",
        "verify residual",
    ):
        assert phrase in value
    assert "Current RO membrane chlorine tolerance" in value
    assert "Total RO Design authority" in value


def test_orp_is_not_misrepresented_as_quantitative_chlorine_measurement():
    value = text()
    assert "ORP/redox monitoring" in value
    assert "ORP trend ≠ exact chlorine concentration" in value
    assert "not inherently a quantitative free-chlorine measurement" in value
    assert "validated analytical/instrument method" in value


def test_ro_brine_backwash_remains_research_case_not_default_recommendation():
    value = text()
    assert "backwashing UF with RO brine" in value
    assert "RESEARCH / SITE-SPECIFIC VALIDATION CASE — NOT A DEFAULT TWDS RECOMMENDATION" in value
    for phrase in (
        "ionic concentration and saturation state",
        "antiscalant carryover",
        "reducing agent/SMBS carryover",
        "precipitation risk",
        "pilot or side-by-side evidence",
    ):
        assert phrase in value
    assert '"What evidence would make brine backwash defensible here?"' in value


def test_membrane_material_findings_are_not_turned_into_universal_rankings():
    value = text()
    assert "PVDF and PES-family" in value
    assert 'Do not teach "PVDF is always more cleanable"' in value
    assert "Product-specific cleaning compatibility remains manufacturer authority." in value


def test_source_specific_numbers_are_explicitly_not_2026_design_rules():
    value = text()
    assert "source-specific or historical" in value
    for phrase in (
        "exact filtration fluxes",
        "exact backwash fluxes/flows",
        "exact CEB and CIP concentrations",
        "exact NaOCl, NaOH, acid or other cleaning-chemical doses",
        "maximum TMP/CIP trigger",
        "cost-of-water savings percentages",
    ):
        assert phrase in value
    assert "Current manufacturer O&M manuals" in value
    assert "Total Pretreatment Design" in value


def test_learning_exercises_include_design_controls_diagnostics_and_economics():
    value = text()
    for title in (
        "Which Backwash Step Actually Cleans?",
        "Five Steps or Two? DoE Detective",
        "Gross Flux vs Net Flux",
        "The Cleanest Membrane Is Not the Best Plant",
        "Build the TMP Sawtooth",
        "Over-Cleaning or Under-Cleaning?",
        "Stay Inside the Model Envelope",
        "Hidden Downtime",
        "CEB State Machine",
        "Where Did the Chlorine Go?",
        "ORP Says Something Changed",
        "Can We Backwash with RO Brine?",
        "Cleaning Cost per m³",
        "Side-by-Side Validation",
        "Defend the UF Cleaning Philosophy",
    ):
        assert title in value


def test_source_complements_pearce_without_replacing_engine_authority():
    value = text()
    assert "Pearce remains the broader backbone" in value
    assert "Gilabert-Oriol adds a deeper specialist layer" in value
    assert "The two sources complement rather than duplicate one another." in value
    assert "Academy does **not** own" in value
    assert "Total Pretreatment Design" in value
    assert "Total RO Design" in value


def test_source_layer_does_not_claim_runtime_implementation():
    value = text()
    assert "source/curriculum architecture addition only" in value
    for phrase in (
        "does not:\n\n- modify Academy runtime routes",
        "change the current 360 guided hours",
        "change the 50-course catalog",
        "modify the multilingual runtime",
        "add project-grade UF equations",
        "change Total Pretreatment Design",
        "change Total RO Design",
        "change Suite Core",
    ):
        assert phrase in value


def test_future_learner_chapter_must_enter_multilingual_workflow():
    value = text()
    assert "L03-M04 learner-facing chapter" in value
    assert "English / `es-419` / Arabic translation workflow" in value
