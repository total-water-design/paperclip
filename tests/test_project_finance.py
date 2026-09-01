import hashlib
import json
import random
import unittest

from project_finance import analyze_project_finance


class ProjectFinanceTests(unittest.TestCase):
    def base_result(self):
        return {
            "cost_hierarchy": {"total_project_cost": 42_514_174.09118067},
            "operating": {
                "capacity_m3d": 25_000,
                "availability": 0.95,
                "annual_opex_y": 6_382_317.677777777,
                "source_opex_breakdown": {},
                "project_level_opex_y": 6_382_317.677777777,
                "project_life_years": 25,
            },
        }

    def base_cfg(self):
        return {
            "enabled": True,
            "construction_months": 24,
            "construction_spend_curve": [1 / 24] * 24,
            "debt_fraction": 0.70,
            "construction_debt_rate": 0.0,
            "debt_interest_rate": 0.07,
            "debt_tenor_years": 18,
            "repayment_profile": "equal_principal",
            "upfront_financing_fee_pct": 0.0,
            "concession_years": 25,
            "tariff_m3": 1.278,
            "tariff_escalation_pct": 0.02,
            "opex_escalation_pct": 0.02,
            "corporate_tax_rate": 0.258,
            "tax_depreciation_method": "straight_line",
            "tax_depreciation_years": 25,
            "receivable_days": 30,
            "inventory_days": 30,
            "inventory_eligible_opex_fraction": 0.15,
            "payable_days": 30,
            "cost_of_equity": 0.20,
            "dsra_months": 3,
        }

    def test_workbook_reference_debt_amount_and_first_year_debt_service(self):
        cfg = self.base_cfg()
        result = analyze_project_finance({"finance": {"tariff_m3": 1.278}, "project_finance": cfg}, self.base_result())
        debt = result["construction"]["debt_funding"]
        self.assertAlmostEqual(debt, 29_759_921.86382647, places=2)
        row1 = result["operations"]["rows"][0]
        self.assertAlmostEqual(row1["principal"], debt / 18.0, places=6)
        expected_interest = (debt + (debt - debt / 18.0)) / 2.0 * 0.07
        self.assertAlmostEqual(row1["interest"], expected_interest, places=6)
        self.assertAlmostEqual(row1["revenue"], 11_078_662.5, places=2)

    def test_construction_idc_is_time_phased_and_funding_ratio_is_preserved(self):
        cfg = self.base_cfg()
        cfg["construction_debt_rate"] = 0.07
        cfg["upfront_financing_fee_pct"] = 0.03
        result = analyze_project_finance({"project_finance": cfg}, self.base_result())
        construction = result["construction"]
        self.assertGreater(construction["idc"], 0)
        self.assertGreater(construction["upfront_financing_fee"], 0)
        self.assertAlmostEqual(construction["debt_fraction_effective"], 0.70, places=12)
        self.assertAlmostEqual(
            construction["debt_funding"] + construction["equity_funding"],
            construction["total_funding_requirement"],
            places=6,
        )

    def test_dsra_is_equity_funded_and_released_as_debt_service_declines(self):
        cfg = self.base_cfg()
        with_dsra = analyze_project_finance({"project_finance": cfg}, self.base_result())
        no_dsra_cfg = dict(cfg); no_dsra_cfg["dsra_months"] = 0
        without_dsra = analyze_project_finance({"project_finance": no_dsra_cfg}, self.base_result())
        construction = with_dsra["construction"]
        self.assertGreater(construction["initial_dsra"], 0)
        self.assertGreater(
            construction["funding_requirement_including_initial_dsra"],
            construction["total_funding_requirement"],
        )
        rows = with_dsra["operations"]["rows"]
        self.assertAlmostEqual(rows[0]["dsra_opening"], construction["initial_dsra"], places=6)
        self.assertTrue(any(row["dsra_release"] > 0 for row in rows))
        self.assertAlmostEqual(rows[-1]["dsra_closing"], 0.0, places=8)
        self.assertLessEqual(with_dsra["returns"]["equity_irr"], without_dsra["returns"]["equity_irr"] + 1e-12)

    def test_configured_straight_line_tax_life_is_not_stretched_to_concession(self):
        cfg = self.base_cfg()
        cfg["tax_depreciation_years"] = 10
        result = analyze_project_finance({"project_finance": cfg}, self.base_result())
        rows = result["operations"]["rows"]
        base = self.base_result()["cost_hierarchy"]["total_project_cost"]
        annual = base / 10.0
        for row in rows[:10]:
            self.assertAlmostEqual(row["depreciation"], annual, places=6)
        for row in rows[10:]:
            self.assertAlmostEqual(row["depreciation"], 0.0, places=8)

    def test_coverage_and_returns_are_calculated(self):
        result = analyze_project_finance({"project_finance": self.base_cfg()}, self.base_result())
        self.assertIsNotNone(result["debt"]["min_dscr"])
        self.assertGreater(result["debt"]["llcr"], 0)
        self.assertGreater(result["debt"]["plcr"], 0)
        self.assertIsNotNone(result["returns"]["project_irr"])
        self.assertIsNotNone(result["returns"]["equity_irr"])
        self.assertEqual(len(result["operations"]["rows"]), 25)

    def test_terminal_value_and_handback_are_separate(self):
        cfg = self.base_cfg()
        cfg["terminal_value"] = 5_000_000
        cfg["handback_cost"] = 1_500_000
        result = analyze_project_finance({"project_finance": cfg}, self.base_result())
        final = result["operations"]["rows"][-1]
        self.assertEqual(final["terminal_value"], 5_000_000)
        self.assertEqual(final["handback_cost"], 1_500_000)

    def test_tariff_solver_meets_minimum_dscr(self):
        cfg = self.base_cfg()
        cfg.update({
            "solve_tariff": True,
            "target_min_dscr": 1.30,
            "target_equity_irr": 0.0,
            "target_project_npv": -1e99,
            "tariff_solver_max": 10.0,
        })
        result = analyze_project_finance({"project_finance": cfg}, self.base_result())
        solved = result["tariff_solver"]
        self.assertTrue(solved["solved"])
        self.assertGreater(solved["required_tariff_m3"], 0)
        self.assertGreaterEqual(solved["result_at_required_tariff"]["min_dscr"], 1.30 - 1e-9)

    def test_debt_tenor_cannot_exceed_concession(self):
        cfg = self.base_cfg()
        cfg["debt_tenor_years"] = 30
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            analyze_project_finance({"project_finance": cfg}, self.base_result())

    def test_v1_covenant_reports_both_bases_and_tests_reserve_aware_by_default(self):
        result = analyze_project_finance({"project_finance": self.base_cfg()}, self.base_result())
        self.assertEqual(result["debt"]["covenant_dscr_basis"], "reserve_aware")
        for row in result["operations"]["rows"]:
            self.assertIn("raw_dscr", row)
            self.assertIn("reserve_aware_dscr", row)
            self.assertIn("reserve_deficiency", row)
            self.assertGreaterEqual(row["reserve_deficiency"], 0.0)
            if row["debt_service"]:
                self.assertAlmostEqual(row["tested_dscr"], row["reserve_aware_dscr"], places=12)

        raw_cfg = self.base_cfg()
        raw_cfg["covenant_dscr_basis"] = "raw"
        raw = analyze_project_finance({"project_finance": raw_cfg}, self.base_result())
        self.assertEqual(raw["debt"]["covenant_dscr_basis"], "raw")
        self.assertAlmostEqual(raw["operations"]["rows"][0]["tested_dscr"], raw["operations"]["rows"][0]["raw_dscr"], places=12)

    def test_sculpting_metadata_persists_exact_scenario_and_cfads_vector(self):
        cfg = self.base_cfg()
        cfg["sculpting_scenario_id"] = "contracted-offtake-p50"
        result = analyze_project_finance({"project_finance": cfg}, self.base_result())
        sculpting = result["debt"]["sculpting"]
        self.assertEqual(sculpting["scenario_id"], "contracted-offtake-p50")
        self.assertEqual(sculpting["cfads_vector"], [row["cfads"] for row in result["operations"]["rows"][:18]])
        self.assertEqual(len(sculpting["debt_schedule"]), 18)
        self.assertIn("informative only", sculpting["note"])

    def test_equity_cure_is_disabled_by_default_and_disclosed_when_used(self):
        cfg = self.base_cfg()
        cfg.update({"tariff_m3": 0.85, "target_min_dscr": 1.30})
        disabled = analyze_project_finance({"project_finance": cfg}, self.base_result())
        self.assertFalse(disabled["debt"]["equity_cure"]["enabled"])
        self.assertEqual(disabled["debt"]["equity_cure"]["uses"], 0)

        cfg["equity_cure"] = {"enabled": True, "amount_basis": "dscr_shortfall", "frequency": "once", "consecutive_use_cap": 1, "total_use_cap": 1, "treatment": "cfads_addition"}
        cured = analyze_project_finance({"project_finance": cfg}, self.base_result())
        debt = cured["debt"]
        self.assertEqual(debt["equity_cure"]["uses"], 1)
        first = cured["operations"]["rows"][0]
        self.assertGreater(first["equity_cure_cfads_addition"], 0)
        self.assertAlmostEqual(first["tested_dscr"], 1.30, places=10)

        prepay_cfg = self.base_cfg()
        prepay_cfg.update({"tariff_m3": 0.85, "target_min_dscr": 1.30, "equity_cure": {"enabled": True, "amount_basis": "fixed_amount", "amount": 100_000, "frequency": "once", "consecutive_use_cap": 1, "total_use_cap": 1, "treatment": "debt_prepayment"}})
        prepaid = analyze_project_finance({"project_finance": prepay_cfg}, self.base_result())
        prepay_rows = prepaid["operations"]["rows"]
        self.assertEqual(prepay_rows[0]["equity_cure_debt_prepayment"], 100_000)
        self.assertEqual(prepay_rows[0]["equity_cure_cfads_addition"], 0.0)
        self.assertLess(prepay_rows[1]["opening_debt"], disabled["operations"]["rows"][1]["opening_debt"])

    def test_project_irr_bases_and_v1_warnings_are_explicit(self):
        result = analyze_project_finance({"project_finance": self.base_cfg()}, self.base_result())
        returns = result["returns"]
        self.assertIn("unlevered tax", returns["project_irr_basis"])
        self.assertIn("interest tax shield", returns["levered_tax_project_irr_basis"])
        self.assertIsNotNone(returns["levered_tax_project_irr"])
        self.assertNotEqual(returns["project_irr"], returns["levered_tax_project_irr"])
        text = " ".join(result["limitations"])
        self.assertIn("seasonality", text)
        self.assertIn("VAT/GST", text)

    def test_one_tranche_legacy_projection_is_byte_stable(self):
        """The validated one-tranche mechanics remain unchanged; v1 fields are additive."""
        output = analyze_project_finance({"project_finance": self.base_cfg()}, self.base_result())
        new_row_keys = {"raw_dscr", "reserve_aware_cfads", "reserve_aware_dscr", "selected_dscr_pre_cure", "tested_dscr", "covenant_dscr_basis", "reserve_deficiency", "equity_cure_amount", "equity_cure_treatment", "equity_cure_cfads_addition", "equity_cure_debt_prepayment", "levered_tax_project_free_cash_flow"}
        legacy = {
            "construction": {key: output["construction"][key] for key in ("months", "curve", "rows", "base_capex", "upfront_financing_fee", "idc", "total_funding_requirement", "debt_funding", "equity_funding", "debt_fraction_effective", "initial_dsra", "funding_requirement_including_initial_dsra")},
            "operations": {"concession_years": output["operations"]["concession_years"], "tariff_m3": output["operations"]["tariff_m3"], "rows": [{key: value for key, value in row.items() if key not in new_row_keys} for row in output["operations"]["rows"]]},
            "returns": {key: output["returns"][key] for key in ("wacc", "project_irr", "equity_irr", "project_npv", "equity_npv", "project_cashflow_sign_changes", "equity_cashflow_sign_changes")},
            "debt": {key: output["debt"][key] for key in ("debt_at_cod", "min_dscr", "average_dscr", "llcr", "plcr", "initial_dsra")},
        }
        canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), "c838128a345dd082875c2252095c8bd891f0ca540da29e4f22bdb0862abc5f54")

    def test_randomized_contract_invariants(self):
        rng = random.Random(336)
        for _ in range(100):
            cfg = self.base_cfg()
            cfg.update({
                "debt_fraction": rng.uniform(0.1, 0.9), "debt_interest_rate": rng.uniform(0.0, 0.12),
                "tariff_m3": rng.uniform(0.5, 2.5), "dsra_months": rng.uniform(0, 12),
                "covenant_dscr_basis": rng.choice(["raw", "reserve_aware"]),
                "target_min_dscr": rng.uniform(0.0, 1.8),
            })
            result = analyze_project_finance({"project_finance": cfg}, self.base_result())
            for row in result["operations"]["rows"]:
                self.assertGreaterEqual(row["reserve_deficiency"], 0.0)
                if row["debt_service"] > 1e-9:
                    expected = row["raw_dscr"] if cfg["covenant_dscr_basis"] == "raw" else row["reserve_aware_dscr"]
                    self.assertAlmostEqual(row["tested_dscr"], expected, places=10)


if __name__ == "__main__":
    unittest.main()
