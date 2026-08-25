from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TOTAL_WATER_ACADEMY_PROJECT_DELIVERY_COMMERCIAL_FINANCE_v1.0.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_track_maps_to_level_nine_and_level_ten_without_inflating_course_hours():
    text = read_doc()
    assert "Level 9" in text
    assert "Level 10" in text
    assert "34-hour structure" in text
    assert "360-guided-hour Academy architecture" in text


def test_project_development_sequence_is_explicit():
    text = read_doc().lower()
    for concept in (
        "prefeasibility",
        "feasibility",
        "pre-feed",
        "feed",
        "final investment decision (fid)",
        "financial close",
    ):
        assert concept in text
    assert "fid and financial close are the same" in text


def test_execution_models_are_taught_separately_from_pricing_models():
    text = read_doc().lower()
    for concept in (
        "engineering + procurement (ep)",
        "ep + supply",
        "epc",
        "lump sum turnkey",
        "hybrid epc",
        "cost-plus",
        "design-build (db)",
        "progressive design-build",
        "design-build-operate (dbo)",
        "design-build-operate-maintain (dbom)",
        "design-build-own-operate-maintain (dboom)",
        "boot",
        "dbfom",
    ):
        assert concept in text
    assert "scope-delivery structure and compensation structure are different questions" in text
    assert "responsibility bundle" in text
    assert "not automatically mean lump sum" in text


def test_hybrid_epc_fixed_ep_reimbursable_construction_is_preserved():
    text = read_doc().lower()
    assert "fixed e/p + cost-plus construction" in text
    assert "engineering and procurement may be negotiated on a lump-sum/fixed basis" in text
    assert "construction is reimbursed on a cost-plus" in text
    for risk in (
        "productivity risk",
        "quantity growth",
        "subcontractor escalation",
        "field rework",
        "schedule acceleration",
    ):
        assert risk in text


def test_pdb_two_phase_gmp_open_book_and_off_ramp_are_explicit():
    text = read_doc().lower()
    for concept in (
        "phase 1",
        "open-book",
        "target budget",
        "guaranteed maximum price (gmp)",
        "phase 2",
        "off-ramp",
        "nte",
    ):
        assert concept in text
    assert "gmp is not the same as lump sum" in text


def test_project_finance_and_bankability_are_included():
    text = read_doc().lower()
    for concept in (
        "special-purpose vehicle (spv)",
        "sponsor equity",
        "lenders",
        "debt service",
        "dscr",
        "bankability",
        "conditions precedent",
        "financial close",
        "step-in",
    ):
        assert concept in text
    assert "a project is not bankable merely because the npv is positive" in text


def test_water_purchase_agreement_topics_are_complete_enough_for_awareness():
    text = read_doc().lower()
    for concept in (
        "water purchase agreement",
        "contracted capacity",
        "take-or-pay",
        "capacity payments",
        "variable payment",
        "tariff and indexation",
        "water-quality specification",
        "availability",
        "payment security",
        "termination payment",
    ):
        assert concept in text


def test_contract_terms_include_engineering_and_commercial_risk_items():
    text = read_doc().lower()
    for concept in (
        "battery limits",
        "performance guarantees",
        "acceptance testing",
        "liquidated damages",
        "warranties",
        "change orders",
        "force majeure",
        "change in law",
        "limitations of liability",
        "insurance",
        "bonds",
        "retainage",
        "termination",
        "dispute resolution",
        "intellectual property",
    ):
        assert concept in text


def test_guided_solution_mode_contains_commercial_misconception_training():
    text = read_doc().lower()
    for misconception in (
        "epc means lump sum",
        "turnkey means zero owner risk",
        "gmp means lump sum",
        "cost plus means no cost control",
        "feed means the design is complete",
        "fid and financial close are the same",
        "a technically feasible project is bankable",
        "a wpa is just a water price",
        "risk transfer is free",
    ):
        assert misconception in text


def test_interactive_commercial_missions_are_defined():
    text = read_doc().lower()
    for mission in (
        "delivery model match",
        "scope gap detective",
        "pdb phase 1 to phase 2",
        "gmp builder",
        "fid gate",
        "bankability room",
        "build the wpa",
        "contract red-flag review",
        "capstone commercial wrap",
    ):
        assert mission in text


def test_dbia_material_is_not_reproduced_for_education():
    text = read_doc().lower()
    assert "must **not reproduce dbia contract forms, clauses, figures or tables**" in text
    assert "create original diagrams" in text
    assert "paraphrased educational explanations" in text


def test_source_scope_distinguishes_uploaded_pdb_material_from_other_topics():
    text = read_doc().lower()
    assert "supplied files primarily support pdb" in text
    assert "do **not by themselves** fully source epc/lstk, project finance, fid or water purchase agreement" in text
    assert "fidic epc/turnkey" in text
    assert "world bank ppp resource center" in text


def test_track_is_education_not_legal_or_financial_advice():
    text = read_doc().lower()
    assert "not legal, financial, tax or investment advice" in text
    assert "should not require the learner to draft enforceable legal documents" in text
