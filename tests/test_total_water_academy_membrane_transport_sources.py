from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TOTAL_WATER_ACADEMY_MEMBRANE_TRANSPORT_CP_MODULE_v1.0.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_named_peer_reviewed_membrane_sources_are_preserved():
    text = read_doc()
    assert "Kim, S.; Hoek, E.M.V. (2005)" in text
    assert "10.1016/j.desal.2005.05.017" in text
    assert "Wang, J.; Dlamini, D.S." in text
    assert "10.1016/j.memsci.2013.12.034" in text


def test_sources_map_to_existing_level_four_modules():
    text = read_doc()
    assert "L04-M01" in text
    assert "L04-M03" in text
    for concept in (
        "solution–diffusion",
        "observed versus real/intrinsic rejection",
        "CP modulus",
        "Reynolds, Schmidt, and Sherwood",
        "Film theory versus rigorous modeling",
        "fouling-enhanced ECP",
    ):
        assert concept in text


def test_papers_are_cited_when_materially_used():
    text = read_doc().lower()
    assert "must be cited in academy lesson provenance" in text
    assert "sources & further reading" in text
    assert "do not copy publisher figures, tables, or prose" in text


def test_lab_specific_film_theory_result_is_not_promoted_to_design_limit():
    text = read_doc().lower()
    assert "approximately 16 gfd" in text
    assert "not as a universal twds design limit" in text


def test_state_of_art_claim_requires_newer_literature_review():
    text = read_doc().lower()
    assert "should not alone be described as the final 2026 state of the art" in text
    assert "periodic review of newer peer-reviewed literature" in text


def test_engineering_authority_remains_outside_academy():
    text = read_doc()
    for owner in (
        "app/total-ro-design",
        "engine/shared-water-chemistry",
        "engine/shared-waterstream",
        "app/total-water-balance",
    ):
        assert owner in text


def test_interactive_transport_missions_are_defined():
    text = read_doc().lower()
    for mission in (
        "boundary-layer explorer",
        "observed-versus-real-rejection mission",
        "model-selection mission",
        "fouling-enhanced cp mission",
        "tail-element scaling mission",
    ):
        assert mission in text
