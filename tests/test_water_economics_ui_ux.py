from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class WaterEconomicsUiUxTests(unittest.TestCase):
    def test_economics_extends_shared_application_shell(self):
        template = read("templates/economics_suite.html")
        self.assertIn('{% extends "shared/application_shell.html" %}', template)
        self.assertIn("shared/suite_components.html", template)
        self.assertNotIn("<html", template.lower())
        self.assertNotIn("ted-sidebar", template)
        self.assertNotIn("ted-topbar", template)

    def test_approved_identity_and_accent_are_used(self):
        template = read("templates/economics_suite.html")
        catalog = read("suite_catalog.py")
        self.assertIn("Total Water Economics", template)
        self.assertIn("#985A00", template)
        self.assertIn('name="Total Water Economics"', catalog)
        self.assertIn('short_name="Water Economics"', catalog)
        self.assertIn('accent="#985A00"', catalog)

    def test_shared_shell_contract_assets_are_present(self):
        shell = read("templates/shared/application_shell.html")
        components = read("templates/shared/suite_components.html")
        css = read("static/suite_application_shell.css")
        js = read("static/suite_application_shell.js")
        for token in ("twds-app-header", "twds-app-nav", "project_bar", "twds-workspace-nav", "twds-workspace-content"):
            self.assertIn(token, shell)
        for macro in ("master_lockup", "application_identity", "account_menu", "guidance", "project_bar", "calculate_button", "kpi", "handoff_card"):
            self.assertRegex(components, rf"macro {re.escape(macro)}\(")
        for severity in ("information", "review", "warning", "calculation-error", "critical"):
            self.assertIn(severity, css)
        for state in ("idle", "validating", "calculating", "converging", "converged", "attention", "failed", "stale"):
            self.assertRegex(js, rf"\b{state}:\"")

    def test_results_follow_economics_contract_architecture(self):
        template = read("templates/economics_suite.html")
        for heading in ("SYSTEM SUMMARY", "PROCESS / ALTERNATIVE SUMMARY", "DETAILED RESULTS", "WARNINGS & CONSTRAINTS", "ENERGY / ECONOMICS"):
            self.assertIn(heading, template)
        for metric_id in ("resultTotalProjectCost", "resultOpex", "resultLifecycleCost", "resultLcow", "resultTariff", "resultDscr"):
            self.assertIn(metric_id, template)

    def test_data_origin_and_lineage_vocabulary_is_visible(self):
        template = read("templates/economics_suite.html")
        js = read("static/economics.js")
        for label in ("User input", "Inherited", "Database / reference", "Calculated", "Overridden inherited"):
            self.assertIn(label, template)
        self.assertIn("sourceLineageCards", template)
        self.assertIn("twds-handoff-card", js)
        self.assertIn("override_of_summary_id", js)

    def test_primary_calculation_uses_shared_states_without_fake_convergence(self):
        js = read("static/economics.js")
        self.assertIn('setCalcState("validating"', js)
        self.assertIn('setCalcState("calculating"', js)
        self.assertIn('setCalcState("failed"', js)
        self.assertNotIn('setCalcState("converging"', js)
        self.assertIn('activatePanel("results")', js)
        self.assertNotIn("twd-economics-theme", js)
        self.assertNotIn("setupTheme", js)

    def test_common_project_controls_report_and_snapshot_are_wired(self):
        template = read("templates/economics_suite.html")
        js = read("static/economics.js")
        self.assertIn("ui.project_bar", template)
        self.assertIn("reportEstimateBtn", template)
        self.assertIn("exportEstimateBtn", template)
        self.assertIn('document.addEventListener("twds:project-action"', js)
        self.assertIn('product_id: "economics"', js)
        self.assertIn('format: "Total Water Economics Project"', js)
        self.assertIn("window.print()", js)

    def test_economics_css_contains_only_specialist_layout_not_shell_clone(self):
        css = read("static/economics.css")
        self.assertNotIn(".ted-sidebar", css)
        self.assertNotIn(".ted-topbar", css)
        self.assertNotIn(".ted-app{", css)
        self.assertIn("var(--twds-app-accent)", css)
        self.assertIn("var(--twds-surface)", css)
        self.assertIn("@media(max-width:760px)", css)
        self.assertIn("@media print", css)


if __name__ == "__main__":
    unittest.main()
