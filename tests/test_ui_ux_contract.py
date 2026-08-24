from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_contract_is_versioned_and_contains_required_hierarchy():
    text = read("docs/UI_UX_CONTRACT_v1.0.md")
    assert "Contract version:** 1.0" in text
    assert "Suite → Application → Project → Workspace → Inputs / Results" in text
    assert "Inputs → Validate → Calculate → Converge → Results → Report" in text


def test_contract_contains_project_prefixes_and_conformity_matrix():
    text = read("docs/UI_UX_CONTRACT_v1.0.md")
    for prefix in ("TPRE", "TBIO", "TROD", "TZLD", "TWBAL", "TWECO", "TWSYS"):
        assert f"`{prefix}`" in text
    assert "| Standard | RO | Bio | ZLD | Required correction |" in text


def test_shared_shell_exposes_common_structure():
    text = read("templates/shared/application_shell.html")
    for token in ("twds-app-header", "twds-app-nav", "project_bar", "twds-workspace-nav", "twds-workspace-content"):
        assert token in text


def test_guidance_component_supports_contract_severities():
    css = read("static/suite_application_shell.css")
    for severity in ("information", "review", "warning", "calculation-error", "critical"):
        assert severity in css


def test_input_origins_are_visually_distinct():
    css = read("static/suite_application_shell.css")
    for origin in ("user", "calculated", "database", "constraint"):
        assert f".twds-field--{origin}" in css


def test_calculation_state_vocabulary_is_centralized():
    js = read("static/suite_application_shell.js")
    for state in ("idle", "validating", "calculating", "converging", "converged", "attention", "failed", "stale"):
        assert re.search(rf"\b{state}:\"", js)


def test_shared_customer_ui_contains_no_ai_or_trace_language():
    combined = "\n".join([
        read("templates/shared/application_shell.html"),
        read("templates/shared/suite_components.html"),
        read("static/suite_application_shell.js"),
        read("static/suite_application_shell.css"),
    ]).lower()
    for forbidden in ("chatgpt", "openai", "traceback", "stack trace"):
        assert forbidden not in combined
