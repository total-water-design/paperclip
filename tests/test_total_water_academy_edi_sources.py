from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/TOTAL_WATER_ACADEMY_EDI_ELECTROMEMBRANE_MODULE_v1.0.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_named_edi_sources_and_dois_are_preserved():
    text = read_doc()
    for required in (
        "Rathi and P. Senthil Kumar (2020)",
        "10.1007/s10311-020-01006-9",
        "J. Wood, J. Gifford, J. Arba and M. Shaw (2010)",
        "10.1016/j.desal.2009.09.084",
        "Ö. Arar, Ü. Yüksel, N. Kabay and M. Yüksel (2014)",
        "10.1016/j.desal.2014.01.028",
        "L. Alvarado and A. Chen (2014)",
        "10.1016/j.electacta.2014.03.165",
    ):
        assert required in text


def test_edi_maps_across_foundation_membranes_electrical_controls_and_integration():
    text = read_doc()
    for module_id in (
        "L02-M05",
        "L04-M01",
        "L04-M03",
        "L06-M04",
        "L07-M01",
        "L07-M04",
        "L09-M04",
    ):
        assert module_id in text
    assert "Level 10 capstone" in text


def test_edi_transport_science_is_explicit():
    text = read_doc().lower()
    for concept in (
        "diffusion",
        "electromigration",
        "convection",
        "nernst–einstein",
        "nernst–planck",
        "transport numbers",
        "limiting current",
        "concentration polarization",
        "water dissociation",
        "electroregeneration",
        "counterions",
        "co-ions",
        "permselectivity",
    ):
        assert concept in text


def test_ed_and_edi_limiting_current_nuance_is_protected():
    text = read_doc().lower()
    assert "in conventional ed" in text
    assert "in cedi" in text
    assert "must **not** be promoted as a universal edi rule" in text
    assert "role of water splitting differs between ed and edi" in text


def test_edi_feed_and_integration_teaching_is_present():
    text = read_doc().lower()
    for concept in (
        "ro→edi integration",
        "hardness",
        "silica",
        "dissolved co2",
        "organics / toc",
        "concentrate flow",
        "pretreatment",
        "regenerable mixed-bed ix",
    ):
        assert concept in text


def test_edi_historical_numbers_are_not_promoted_to_current_design_limits():
    text = read_doc().lower()
    assert "historical/example envelope" in text
    assert "current selected manufacturer’s limits" in text
    assert "individual experimental removal efficiencies must remain source-labelled examples" in text
    assert "current 2026 market facts" in text


def test_edi_project_sizing_is_not_invented_by_academy():
    text = read_doc().lower()
    assert "no dedicated authoritative edi project-design engine" in text
    assert "must not invent a project-grade edi sizing model" in text
    assert "not yet assigned/validated in the current repository" in text
    assert "must not generate project-grade stack size" in text


def test_edi_sources_require_provenance_and_original_visuals():
    text = read_doc().lower()
    assert "research basis" in text
    assert "sources & further reading" in text
    assert "do not reproduce publisher figures, tables, or prose" in text
    assert "create original academy diagrams" in text


def test_edi_interactive_missions_are_defined():
    text = read_doc().lower()
    for mission in (
        "build the cedi cell",
        "follow the ion",
        "current–voltage explorer",
        "ed versus edi water-splitting challenge",
        "flow-rate tradeoff mission",
        "ro→edi feed-quality gate",
        "edi controls mission",
        "polishing technology decision",
        "vendor-data handoff",
    ):
        assert mission in text
