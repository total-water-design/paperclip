from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CH6 = ROOT / "docs" / "TOTAL_WATER_ACADEMY_UF_MF_PEARCE_CH6_WASTEWATER_REUSE_MBR_SOURCE_NOTE_v1.0.md"
CH7 = ROOT / "docs" / "TOTAL_WATER_ACADEMY_UF_MF_PEARCE_CH7_DESALINATION_PRETREATMENT_SOURCE_NOTE_v1.0.md"
CH8 = ROOT / "docs" / "TOTAL_WATER_ACADEMY_UF_MF_PEARCE_CH8_IMPLEMENTATION_OPERATION_TROUBLESHOOTING_SOURCE_NOTE_v1.0.md"


def _text(path: Path) -> str:
    assert path.exists(), f"Missing Pearce Academy extension: {path}"
    return path.read_text(encoding="utf-8")


def test_ch6_is_wastewater_reuse_mbr_and_historical_guarded():
    text = _text(CH6)
    assert "Wastewater Reuse & MBR" in text
    assert "approximately pages 217–238" in text
    assert "HIGH_QUALITY_EXPERT_PRACTITIONER_REFERENCE" in text
    assert "do **not** treat 2011 supplier tables" in text.lower()
    assert "membrane pretreatment being mandatory" in text


def test_ch6_teaches_mbr_architecture_and_aeration_tradeoff():
    text = _text(CH6)
    for term in (
        "immersed two-tank MBR",
        "immersed single-tank MBR",
        "side-stream MBR",
        "Fine bubbles",
        "larger bubbles",
        "HRT versus SRT",
    ):
        assert term in text
    assert "The aeration already needed for biology is free membrane scour" in text


def test_ch6_connects_reuse_to_ro_and_lifecycle_economics_without_fixed_rule():
    text = _text(CH6)
    assert "Pretreatment Is Part of the RO Economics" in text
    assert "Do not teach the statement that membrane pretreatment is universally mandatory for reuse" in text
    assert "Treat It or Move It?" in text
    assert "Why Did the Studies Disagree?" in text
    assert "informed engineering perspective / school of thought" in text


def test_ch6_preserves_specialist_owner_boundaries():
    text = _text(CH6)
    for owner in (
        "app/total-bio-design",
        "app/total-pretreatment-design",
        "app/total-ro-design",
        "app/total-water-economics",
    ):
        assert owner in text


def test_ch7_is_desalination_pretreatment_and_historical_guarded():
    text = _text(CH7)
    assert "Desalination Pretreatment" in text
    assert "approximately pages 241–268" in text
    assert "HIGH_QUALITY_EXPERT_PRACTITIONER_REFERENCE" in text
    assert "Do not treat 2011 RO element specifications" in text


def test_ch7_teaches_ro_fouling_failure_map():
    text = _text(CH7)
    for term in (
        "adsorption of dissolved organic material",
        "precipitation/inorganic deposits",
        "particle deposition/cake or spacer blockage",
        "biological growth",
    ):
        assert term in text
    assert "If SDI is low, the pretreatment problem is solved" in text


def test_ch7_does_not_make_uf_universal_or_chlorination_binary():
    text = _text(CH7)
    assert "must **not** conclude that membrane pretreatment is universally superior" in text
    assert "UF removes bacteria, therefore RO biofouling is eliminated" in text
    assert "informed engineering opinion / school of thought" in text
    assert "Chlorinate This Plant?" in text


def test_ch7_coagulation_is_variable_and_source_specific():
    text = _text(CH7)
    for term in (
        "too much ferric",
        "variable or conditional dosing",
        "source-water quality should drive chemical strategy",
        "Dose Only When Needed?",
        "Ferric Carryover Incident",
    ):
        assert term in text
    assert "Do not teach Pearce's PES/PVDF comparisons as universal" in text


def test_ch7_teaches_energy_vs_total_water_cost_and_sustainability_boundary():
    text = _text(CH7)
    assert "energy optimum, CAPEX optimum, and Total Water Cost optimum" in text
    assert "Energy Optimum vs Water-Cost Optimum" in text
    assert "The Greener Pretreatment Depends on the Boundary" in text
    assert "study-specific, not universal" in text


def test_ch8_is_implementation_operation_and_historical_guarded():
    text = _text(CH8)
    assert "Implementation, Operation & Troubleshooting" in text
    assert "approximately pages 271–306" in text
    assert "HIGH_QUALITY_EXPERT_PRACTITIONER_REFERENCE" in text
    assert "Do **not** turn 2011 tender language" in text
    for example in (
        "pilot durations",
        "flux margins",
        "CEI/PRI alarm values",
        "warranty periods",
        "membrane-life figures",
    ):
        assert example in text


def test_ch8_teaches_scope_interfaces_and_acceptance():
    text = _text(CH8)
    for term in (
        "general scope",
        "purchaser/owner responsibilities",
        "take-over procedures",
        "commissioning plan",
        "acceptance tests",
        "process-control philosophy",
    ):
        assert term in text
    assert "Write the Tender Basis" in text
    assert "Acceptance Test Witness" in text


def test_ch8_pilot_must_capture_hard_conditions_without_hardcoded_heuristic():
    text = _text(CH8)
    assert "most challenging expected feed conditions" in text
    assert "Pilot the Worst Month" in text
    assert "three-month pilot suggestion" in text
    assert "10–15% flux margin" in text
    assert "source-specific historical heuristics" in text


def test_ch8_monitoring_indices_are_framework_not_universal_alarm_values():
    text = _text(CH8)
    for term in (
        "normalized permeability",
        "CEB recovery",
        "CIP recovery",
        "KPI must link trend → interpretation → action",
        "Build the Operator Dashboard",
    ):
        assert term in text
    assert "Do not copy Pearce's CEI/PRI numerical alarm thresholds" in text


def test_ch8_connects_hydraulics_controls_to_fibre_failure():
    text = _text(CH8)
    for term in (
        "water hammer",
        "pressure spikes",
        "fibre flattening/collapse",
        "progressive fatigue",
        "integrity breach",
        "Level 6 hydraulics",
        "Level 7 PLC/interlock logic",
    ):
        assert term in text
    assert "The Failure Happened Months Later" in text


def test_ch8_failure_modes_and_direction_dependent_integrity_are_preserved():
    text = _text(CH8)
    for term in (
        "Manufacturing-related possibilities",
        "Design/operation-related possibilities",
        "direction-dependent fibre crack",
        "It Passes One Test and Fails Another",
    ):
        assert term in text
    assert "A failed integrity test proves the membrane material was defective" in text


def test_ch8_autopsy_workflow_is_evidence_based():
    text = _text(CH8)
    for term in (
        "Non-destructive/field investigation",
        "Destructive/autopsy methods",
        "microscopy/SEM",
        "EDX/EDAX",
        "deposit morphology",
        "Autopsy Before Blame",
    ):
        assert term in text


def test_ch8_warranty_and_life_are_not_universalized():
    text = _text(CH8)
    for term in (
        "materials/workmanship warranty",
        "performance guarantee",
        "pro-rata replacement concept",
        "Warranty or Operations Problem?",
    ):
        assert term in text
    assert "5–8 years" in text
    assert "not** a current universal expectation" in text


def test_all_three_notes_preserve_copyright_and_source_provenance():
    for path in (CH6, CH7, CH8):
        text = _text(path)
        assert "Research Basis / Sources & Further Reading" in text
        assert "Do not reproduce" in text
