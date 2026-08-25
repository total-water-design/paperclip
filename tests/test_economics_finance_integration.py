import unittest

from economics import economic_analysis


class EconomicsFinanceIntegrationTests(unittest.TestCase):
    def base(self):
        return {
            "model": "total_economic_design",
            "project": {"project_name": "PF Test", "currency": "USD", "capacity_m3d": 10000},
            "source_summaries": [],
            "cost_items": [
                {
                    "item_id": "eq-1",
                    "description": "Equipment",
                    "bucket": "equipment_purchase",
                    "quantity": 1,
                    "unit": "LS",
                    "unit_cost": 10_000_000,
                    "currency": "USD",
                    "source_type": "user",
                    "source_reference": "Integration test",
                },
                {
                    "item_id": "di-1",
                    "description": "Installation",
                    "bucket": "direct_installation",
                    "quantity": 1,
                    "unit": "LS",
                    "unit_cost": 5_000_000,
                    "currency": "USD",
                    "source_type": "user",
                    "source_reference": "Integration test",
                },
            ],
            "allowances": {},
            "operating": {
                "capacity_m3d": 10000,
                "availability": 0.95,
                "fixed_opex_y": 1_000_000,
                "other_opex_y": 0,
                "project_life_years": 25,
                "discount_rate": 0.06,
            },
            "finance": {"debt_fraction": 0.70, "interest_rate": 0.06, "debt_tenor_years": 20, "target_dscr": 1.30, "tariff_m3": 1.0},
        }

    @staticmethod
    def advanced_cfg():
        return {
            "enabled": True,
            "construction_months": 24,
            "debt_fraction": 0.70,
            "construction_debt_rate": 0.06,
            "debt_interest_rate": 0.06,
            "debt_tenor_years": 20,
            "concession_years": 25,
            "repayment_profile": "equal_principal",
            "tariff_m3": 1.0,
            "corporate_tax_rate": 0.25,
            "cost_of_equity": 0.15,
            "dsra_months": 3,
        }

    def test_basic_economics_contract_remains_v02_and_finance_is_optional(self):
        result = economic_analysis(self.base())
        self.assertEqual(result["engine_version"], "0.2")
        self.assertEqual(result["project_finance"]["enabled"], False)
        self.assertEqual(result["project_finance"]["version"], "0.2")
        self.assertEqual(result["cost_hierarchy"]["total_direct_cost"], 15_000_000)

    def test_advanced_finance_runs_through_economic_analysis(self):
        payload = self.base()
        payload["project_finance"] = self.advanced_cfg()
        result = economic_analysis(payload)
        self.assertTrue(result["project_finance"]["enabled"])
        self.assertEqual(result["project_finance"]["version"], "0.2")
        self.assertGreater(result["project_finance"]["construction"]["idc"], 0)
        self.assertGreater(result["project_finance"]["construction"]["initial_dsra"], 0)
        self.assertEqual(len(result["project_finance"]["operations"]["rows"]), 25)
        self.assertIsNotNone(result["project_finance"]["debt"]["min_dscr"])

    def test_advanced_finance_warns_if_legacy_financing_allowances_remain(self):
        payload = self.base()
        payload["allowances"] = {"financing_pct": 2.0, "working_capital_pct": 1.0}
        payload["project_finance"] = self.advanced_cfg()
        result = economic_analysis(payload)
        pf = result["project_finance"]
        self.assertGreaterEqual(len(pf["warnings"]), 2)
        self.assertIn("capital_reconciliation", pf)
        self.assertGreater(pf["capital_reconciliation"]["foundational_financing_idc_allowance"], 0)
        self.assertGreater(pf["capital_reconciliation"]["foundational_working_capital_allowance"], 0)
        self.assertEqual(
            pf["capital_reconciliation"]["advanced_initial_dsra"],
            pf["construction"]["initial_dsra"],
        )

    def test_local_cross_currency_cost_uses_canonical_cost_schema(self):
        payload = self.base()
        payload["cost_items"] = [{
            "item_id": "clp-civil",
            "description": "Local civil work",
            "bucket": "direct_installation",
            "quantity": 1,
            "unit": "LS",
            "native_amount": 1_000_000,
            "native_currency": "CLP",
            "fx_rate": 0.0011,
            "fx_source": "test snapshot",
            "fx_snapshot_id": "fx-test-1",
            "reporting_currency": "USD",
            "source_type": "user",
            "source_reference": "Local estimate",
        }]
        result = economic_analysis(payload)
        self.assertAlmostEqual(result["cost_hierarchy"]["direct_installation_cost"], 1100.0)
        self.assertEqual(result["project_cost_schema"]["schema_id"], "twds.cost_item")
        self.assertEqual(result["project_cost_currency_lineage"][0]["fx_snapshot_id"], "fx-test-1")

    def test_specialist_project_level_bucket_is_rejected_before_aggregation(self):
        payload = self.base()
        payload["cost_items"] = []
        payload["source_summaries"] = [{
            "contract": "twds.economic_summary",
            "version": "1.0",
            "summary_id": "ro:scope:base",
            "source": {"application_id": "ro", "application_name": "Total RO Design"},
            "currency": "USD",
            "capex": {"buckets": {"equipment_purchase": 1_000_000, "contingency": 100_000}},
        }]
        with self.assertRaisesRegex(ValueError, "project-level CAPEX bucket"):
            economic_analysis(payload)

    def test_system_integration_summary_keeps_application_identity(self):
        payload = self.base()
        payload["cost_items"] = []
        payload["source_summaries"] = [{
            "contract": "twds.economic_summary",
            "version": "1.0",
            "summary_id": "system:case:base",
            "source": {
                "application_id": "system_integration",
                "application_name": "Total Water Design — System Integration & Optimization",
            },
            "currency": "USD",
            "capex": {"buckets": {"equipment_purchase": 1000}},
            "opex": {"annual": {"other": 100}},
        }]
        result = economic_analysis(payload)
        source = result["source_aggregation"]["sources"][0]
        self.assertEqual(source["source"]["application_id"], "system_integration")
        self.assertEqual(result["integration"]["application_count"], 1)


if __name__ == "__main__":
    unittest.main()
