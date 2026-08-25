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


if __name__ == "__main__":
    unittest.main()
