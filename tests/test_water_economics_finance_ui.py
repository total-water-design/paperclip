from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class WaterEconomicsFinanceUiTests(unittest.TestCase):
    def test_finance_overlay_preserves_existing_suite_ui(self):
        overlay = read("templates/economics_suite_v04.html")
        self.assertIn('{% extends "economics_suite.html" %}', overlay)
        self.assertIn("economics_polish.css", overlay)
        self.assertIn("economics_finance.css", overlay)
        self.assertIn("economics_finance.js", overlay)

    def test_visual_polish_uses_suite_tokens_and_stays_app_scoped(self):
        css = read("static/economics_polish.css")
        self.assertIn('[data-app-id="economics"]', css)
        self.assertIn("var(--twds-app-accent)", css)
        self.assertIn("var(--twds-surface)", css)
        self.assertIn("var(--twds-line)", css)
        self.assertIn("@media(max-width:760px)", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotIn(".twds-app-shell{", css)
        self.assertNotIn(".twds-app-header{", css)

    def test_product_preview_uses_finance_overlay(self):
        text = read("templates/product_status.html")
        self.assertIn("economics_suite_v04.html", text)

    def test_finance_ui_exposes_required_boot_sections(self):
        js = read("static/economics_finance.js")
        for label in (
            "TIME-PHASED PROJECT FINANCE",
            "BOOT / DBOOM cash-flow model",
            "Construction period",
            "Minimum offtake / take-or-pay",
            "DSRA requirement",
            "Corporate tax rate",
            "BOOT handback cost",
            "Target minimum DSCR",
            "Target equity IRR",
            "Minimum DSCR",
            "LLCR",
            "PLCR",
            "Required Tariff",
        ):
            self.assertIn(label, js)

    def test_finance_ui_preserves_reference_model_defect_exclusions(self):
        js = read("static/economics_finance.js")
        for phrase in (
            "broken standalone DSCR units",
            "stale tenor text",
            "disabled MAT logic",
            "legacy #REF! terminal-value sheets",
        ):
            self.assertIn(phrase, js)

    def test_finance_ui_handles_project_restore_and_new_project_clear(self):
        js = read("static/economics_finance.js")
        self.assertIn(r"/\/api\/projects\/\d+/", js)
        self.assertIn("data?.snapshot?.result", js)
        self.assertIn("clearProjectFinance", js)
        self.assertIn('event.detail?.action === "new"', js)

    def test_finance_ui_shows_dsra_and_full_funding_requirement(self):
        js = read("static/economics_finance.js")
        self.assertIn("Initial DSRA", js)
        self.assertIn('id="pfDsra"', js)
        self.assertIn("funding_requirement_including_initial_dsra", js)
        self.assertIn("row.dsra_closing", js)

    def test_finance_ui_is_responsive_and_uses_shared_tokens(self):
        css = read("static/economics_finance.css")
        self.assertIn("var(--twds-line)", css)
        self.assertIn("var(--twds-app-accent)", css)
        self.assertIn("@media(max-width:1050px)", css)
        self.assertIn("@media(max-width:760px)", css)


if __name__ == "__main__":
    unittest.main()
