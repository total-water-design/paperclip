import unittest

from economics import economic_analysis
from economic_summary_contract import aggregate_summaries
from total_economic_design import analyze_estimate, assess_estimate_maturity


class TotalEconomicDesignTests(unittest.TestCase):
    @staticmethod
    def _summary(app_id, summary_id, equipment, installation, annual_opex, *, currency="USD"):
        return {
            "contract": "twds.economic_summary",
            "version": "1.0",
            "summary_id": summary_id,
            "source": {
                "application_id": app_id,
                "application_name": {
                    "pretreatment": "Total Pretreatment Design",
                    "bio": "Total Bio Design",
                    "ro": "Total RO Design",
                    "zld": "Total ZLD Design",
                }.get(app_id, app_id),
                "project_id": f"{summary_id}-project",
                "scenario_id": "base",
            },
            "currency": currency,
            "capex": {
                "buckets": {
                    "equipment_purchase": equipment,
                    "direct_installation": installation,
                }
            },
            "opex": {
                "annual": {
                    "energy": annual_opex * 0.50,
                    "chemicals": annual_opex * 0.20,
                    "maintenance": annual_opex * 0.20,
                    "replacement": annual_opex * 0.10,
                }
            },
        }

    def test_cost_hierarchy_keeps_tic_project_cost_and_capital_requirement_distinct(self):
        result = analyze_estimate({
            "project": {"currency": "USD"},
            "cost_items": [
                {"description": "Equipment", "bucket": "equipment_purchase", "amount": 100.0},
                {"description": "Installation", "bucket": "direct_installation", "amount": 150.0},
                {"description": "Construction indirects", "bucket": "construction_indirect", "amount": 25.0},
                {"description": "Engineering", "bucket": "engineering_procurement", "amount": 10.0},
                {"description": "Owner", "bucket": "owner_cost", "amount": 5.0},
                {"description": "Contingency", "bucket": "contingency", "amount": 20.0},
                {"description": "Escalation", "bucket": "escalation", "amount": 7.0},
                {"description": "Financing", "bucket": "financing", "amount": 4.0},
                {"description": "Working capital", "bucket": "working_capital", "amount": 1.0},
            ],
            "operating": {"capacity_m3d": 1, "availability": 1, "project_life_years": 25},
        })
        h = result["cost_hierarchy"]
        self.assertEqual(h["total_direct_cost"], 250.0)
        self.assertEqual(h["total_installed_cost"], 275.0)
        self.assertEqual(h["project_cost_before_contingency"], 290.0)
        self.assertEqual(h["total_project_cost"], 317.0)
        self.assertEqual(h["total_capital_requirement"], 322.0)

    def test_explicit_bucket_overrides_percentage_allowance(self):
        result = analyze_estimate({
            "project": {"currency": "USD"},
            "cost_items": [
                {"description": "Equipment", "bucket": "equipment_purchase", "amount": 100.0},
                {"description": "Installation", "bucket": "direct_installation", "amount": 100.0},
                {"description": "Quoted construction indirects", "bucket": "construction_indirect", "amount": 30.0, "source_type": "vendor_quote"},
            ],
            "allowances": {"construction_indirect_pct": 50.0},
            "operating": {"capacity_m3d": 1, "availability": 1, "project_life_years": 25},
        })
        self.assertEqual(result["cost_hierarchy"]["construction_indirect_cost"], 30.0)
        generated = [x for x in result["cost_items"] if x["item_id"] == "allowance-construction_indirect"]
        self.assertEqual(generated, [])

    def test_maturity_reaches_expected_end_classes(self):
        self.assertEqual(assess_estimate_maturity({})["recommended_class"], "Class 5")
        keys = [x["key"] for x in assess_estimate_maturity({})["deliverables"]]
        self.assertEqual(assess_estimate_maturity({key: 1.0 for key in keys})["recommended_class"], "Class 1")

    def test_required_tariff_reproduces_target_dscr(self):
        base = {
            "project": {"currency": "USD"},
            "cost_items": [
                {"description": "Equipment", "bucket": "equipment_purchase", "amount": 10_000_000},
                {"description": "Installation", "bucket": "direct_installation", "amount": 5_000_000},
            ],
            "operating": {"capacity_m3d": 20_000, "availability": 0.95, "fixed_opex_y": 900_000, "project_life_years": 25},
            "finance": {"debt_fraction": 0.70, "interest_rate": 0.06, "debt_tenor_years": 20, "target_dscr": 1.30},
        }
        first = analyze_estimate(base)
        tariff = first["finance"]["required_tariff_for_target_dscr"]
        base["finance"]["tariff_m3"] = tariff
        second = analyze_estimate(base)
        self.assertAlmostEqual(second["finance"]["dscr"], 1.30, places=10)

    def test_provenance_reports_source_mix(self):
        result = analyze_estimate({
            "project": {"currency": "USD"},
            "cost_items": [
                {"description": "Quoted equipment", "bucket": "equipment_purchase", "amount": 80.0, "source_type": "vendor_quote"},
                {"description": "Concept allowance", "bucket": "direct_installation", "amount": 20.0, "source_type": "parametric"},
            ],
            "operating": {"capacity_m3d": 1, "availability": 1, "project_life_years": 25},
        })
        distribution = {x["source_type"]: x for x in result["provenance"]["distribution"]}
        self.assertAlmostEqual(distribution["vendor_quote"]["share"], 0.8)
        self.assertAlmostEqual(distribution["parametric"]["share"], 0.2)
        self.assertGreater(result["provenance"]["weighted_score"], 0.8)

    def test_api_dispatch_selects_total_economic_design_only_when_requested(self):
        result = economic_analysis({"model": "total_economic_design"})
        self.assertEqual(result["application"], "Total Economic Design")
        self.assertEqual(result["engine_version"], "0.2")
        self.assertEqual(result["integration"]["mode"], "manual_project_estimate")

    def test_single_application_summary_produces_standalone_economics(self):
        result = economic_analysis({
            "model": "total_economic_design",
            "project": {"currency": "USD", "capacity_m3d": 20_000},
            "source_summaries": [self._summary("ro", "RO-BASE", 10_000_000, 5_000_000, 1_200_000)],
            "allowances": {},
            "operating": {
                "capacity_m3d": 20_000,
                "availability": 0.95,
                "electricity_price_kwh": 0.10,
                "project_life_years": 25,
                "discount_rate": 0.06,
            },
        })
        self.assertEqual(result["integration"]["mode"], "single_application")
        self.assertEqual(result["integration"]["application_count"], 1)
        self.assertEqual(result["source_aggregation"]["capex_total"], 15_000_000)
        self.assertEqual(result["cost_hierarchy"]["total_direct_cost"], 15_000_000)
        self.assertAlmostEqual(result["operating"]["source_application_opex_y"], 1_200_000)
        self.assertAlmostEqual(result["operating"]["annual_opex_y"], 1_200_000)
        self.assertGreater(result["operating"]["annualized_capital_y"], 0)
        self.assertAlmostEqual(
            result["operating"]["combined_annual_cost_y"],
            result["operating"]["annualized_capital_y"] + 1_200_000,
        )

    def test_multiple_applications_combine_before_project_allowances(self):
        result = economic_analysis({
            "model": "total_economic_design",
            "project": {"currency": "USD", "capacity_m3d": 40_000},
            "source_summaries": [
                self._summary("pretreatment", "PRE-BASE", 4_000_000, 2_000_000, 400_000),
                self._summary("ro", "RO-BASE", 10_000_000, 5_000_000, 1_200_000),
            ],
            "allowances": {"construction_indirect_pct": 10.0, "contingency_pct": 10.0},
            "operating": {"capacity_m3d": 40_000, "availability": 0.95, "project_life_years": 25, "discount_rate": 0.06},
        })
        h = result["cost_hierarchy"]
        self.assertEqual(result["integration"]["mode"], "combined_applications")
        self.assertEqual(result["integration"]["application_count"], 2)
        self.assertEqual(result["source_aggregation"]["capex_total"], 21_000_000)
        self.assertEqual(h["total_direct_cost"], 21_000_000)
        self.assertEqual(h["construction_indirect_cost"], 2_100_000)
        self.assertEqual(h["total_installed_cost"], 23_100_000)
        self.assertEqual(h["contingency"], 2_310_000)
        self.assertEqual(h["total_project_cost"], 25_410_000)
        self.assertAlmostEqual(result["operating"]["source_application_opex_y"], 1_600_000)

    def test_duplicate_application_summary_is_rejected(self):
        duplicate = self._summary("ro", "RO-SAME", 1_000_000, 500_000, 100_000)
        with self.assertRaisesRegex(ValueError, "same source summary"):
            aggregate_summaries([duplicate, duplicate], project_currency="USD")

    def test_legacy_total_capex_and_opex_are_imported_with_warnings(self):
        aggregate = aggregate_summaries([{
            "summary_id": "LEGACY-RO",
            "source": {"application_id": "ro", "application_name": "Total RO Design"},
            "currency": "USD",
            "capex_usd": 5_000_000,
            "annual_opex_usd": 750_000,
        }], project_currency="USD")
        self.assertEqual(aggregate["capex_total"], 5_000_000)
        self.assertEqual(aggregate["annual_opex_total"], 750_000)
        self.assertGreaterEqual(len(aggregate["warnings"]), 2)

    def test_currency_mismatch_is_rejected_until_fx_is_explicit(self):
        euro = self._summary("ro", "RO-EUR", 1_000_000, 500_000, 100_000, currency="EUR")
        with self.assertRaisesRegex(ValueError, "do not match reporting currency"):
            aggregate_summaries([euro], project_currency="USD")

    def test_legacy_ro_economics_path_is_preserved(self):
        result = economic_analysis({
            "product_capacity_m3d": 1000,
            "availability": 0.95,
            "electricity_price": 0.10,
            "project_life": 25,
            "discount_rate": 0.06,
            "base_capex_per_m3d": 1000,
            "cases": {
                "px": {
                    "feed_flow_m3h": 100,
                    "product_flow_m3h": 45,
                    "ro_sec": 2.5,
                    "pretreatment_sec": 0.2,
                    "total_sec": 2.7,
                }
            },
        })
        self.assertEqual(result["preferred"], "px")
        self.assertEqual(result["preferred_label"], "Isobaric Chamber")
        self.assertIn("px", result["cases"])
        self.assertNotIn("application", result)


if __name__ == "__main__":
    unittest.main()
