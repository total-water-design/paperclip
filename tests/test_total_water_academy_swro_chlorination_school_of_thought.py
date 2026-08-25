from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "TOTAL_WATER_ACADEMY_SWRO_CHLORINATION_SCHOOL_OF_THOUGHT_SOURCE_NOTE_v1.0.md"


def _text() -> str:
    assert DOC.exists(), f"Missing Academy chlorination source note: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_khan_paper_is_explicitly_school_of_thought_not_universal_rule():
    text = _text()
    assert "informed opinion / school of thought" in text
    assert "not as a universal rule" in text
    assert "This is not a universal TWDS design rule" in text
    assert "chlorination = prohibited" in text
    assert "chlorination = required" in text


def test_full_scale_cta_hff_context_is_preserved():
    text = _text()
    for term in (
        "full-scale SWRO plant",
        "Red Sea coast of Saudi Arabia",
        "cellulose triacetate (CTA)",
        "hollow-fine-fiber",
        "intermittent direct chlorine exposure",
    ):
        assert term in text


def test_source_note_separates_distinct_chlorination_questions():
    text = _text()
    for term in (
        "Intake chlorination",
        "Pretreatment chlorination",
        "Direct chlorination of chlorine-tolerant CTA RO membranes",
        "Chlorine exposure of polyamide thin-film-composite RO membranes",
    ):
        assert term in text


def test_source_note_teaches_dose_is_not_exposure():
    text = _text()
    assert "dosing is not exposure" in text.lower()
    assert "chlorine dose ≠ chlorine residual ≠ CT at the target surface" in text
    for mechanism in (
        "physical plugging",
        "consumption of chlorine by organic foulants",
        "shielding of microorganisms",
        "spatial variation in chemical penetration",
    ):
        assert mechanism in text


def test_source_note_teaches_evidence_triangulation():
    text = _text()
    for method in (
        "ATP measurements",
        "SEM imaging",
        "FTIR",
        "solid-state 13C NMR",
        "pyrolysis-GC/MS",
        "ICP-OES",
        "flow cytometry",
        "microbial-community sequencing",
    ):
        assert method in text
    assert "evidence triangulation" in text


def test_source_note_protects_spatial_fouling_interpretation():
    text = _text()
    assert "highest foulant mass ≠ highest biological activity" in text
    assert "Where is the biofilm hiding?" in text
    assert "rear/middle module regions" in text


def test_source_note_teaches_selection_not_sterility():
    text = _text()
    assert "select for the organisms and niches that remain" in text
    assert "Do not claim" in text
    assert "community selection is possible" in text


def test_source_note_handles_intermittent_chlorination_as_debate():
    text = _text()
    assert "Shock treatment or ecological cycling?" in text
    assert "intermittent chlorine exposure" in text
    assert "The student should identify what data would be required" in text


def test_source_note_includes_sbs_without_overclaiming_causation():
    text = _text()
    assert "Sodium bisulfite / dechlorination" in text
    assert "did not observe the same phenomenon in the second campaign" in text
    assert "must not be taught as a universal rule that SBS causes biofouling" in text
    assert "Cause, Correlation or Coincidence?" in text


def test_source_note_includes_dbp_and_material_tradeoff():
    text = _text()
    assert "Disinfection by-products (DBPs)" in text
    assert "material-compatibility" in text
    assert "Project-grade DBP prediction" in text


def test_source_note_labels_authors_conclusion_as_position():
    text = _text()
    assert "Khan et al. (2015) position / school of thought" in text
    assert "recommended against chlorination in SWRO pretreatment" in text
    assert "specific full-scale CTA hollow-fine-fiber plant" in text


def test_source_note_requires_comparison_with_other_operating_philosophies():
    text = _text()
    for philosophy in (
        "continuous intake chlorination",
        "intermittent/slug chlorination",
        "minimal chlorination with strong physical pretreatment",
        "chlorination only for specific intake/conveyance conditions",
        "chlorine-avoidance strategies",
    ):
        assert philosophy in text
    assert "technically defensible disagreements" in text


def test_source_note_defines_guided_engineering_decision_exercise():
    text = _text()
    assert "Should this SWRO plant chlorinate?" in text
    for step in (
        "Define the target problem",
        "Identify membrane compatibility",
        "Map the chlorine demand",
        "Map hydraulic access",
        "Evaluate dechlorination",
        "Evaluate DBPs/environment",
        "Choose an operating philosophy and defend it",
    ):
        assert step in text


def test_source_note_contains_key_misconceptions():
    text = _text()
    for misconception in (
        "Chlorine kills bacteria, therefore it prevents RO biofouling",
        "A measured residual at the RO inlet proves chlorination of the complete module",
        "The Khan paper proves chlorine never works",
        "The authors recommend no chlorine, so TWDS should remove chlorination from every pretreatment design",
        "CTA and polyamide RO can use the same chlorination strategy",
        "More disinfectant always creates more reliable operation",
    ):
        assert misconception in text


def test_source_note_maps_across_academy_without_new_hours():
    text = _text()
    for level in ("Level 2", "Level 3", "Level 4", "Level 7", "Level 9", "Level 10"):
        assert level in text
    assert "without increasing the 360-hour total" in text
    assert "SWRO Biological Control Philosophy" in text


def test_source_note_preserves_engineering_owner_boundary():
    text = _text()
    assert "Academy owns the **teaching of the debate and reasoning**" in text
    for excluded in (
        "project-grade chlorine dose selection",
        "disinfectant residual prediction",
        "detailed DBP formation prediction",
        "membrane oxidative-degradation calculation",
        "current membrane-vendor chemical limits",
    ):
        assert excluded in text


def test_source_note_preserves_provenance_copyright_and_current_state_guard():
    text = _text()
    assert "Research Basis / Sources & Further Reading" in text
    assert "copyrighted" in text.lower()
    assert "do not label it by itself as the complete **2026 state of the art**" in text
    assert "supplement this source with newer peer-reviewed work" in text
    assert "current membrane-manufacturer compatibility guidance" in text


def test_future_lesson_must_include_opposing_view_and_site_specific_defense():
    text = _text()
    assert "include an opposing/alternative operating philosophy for comparison" in text
    assert "require the student to defend a site-specific decision" in text
    assert "content architecture" in text
