import unittest

from economic_risk_costs import analyze_risk_costs
from economics import economic_analysis


class RiskCostScheduleTests(unittest.TestCase):
    def test_corridor_economics_and_expiry_warning(self):
        result = analyze_risk_costs({"land_rights": [
            {"item_id": "row-1", "type": "per_km_row", "length_km": 12, "rate_per_km": 5000, "treatment": "capex", "start_period": 0, "source": "quotation", "reference": "ROW-17"},
            {"item_id": "lease-1", "type": "annual_rental", "amount": 1000, "treatment": "opex", "start_period": 1, "end_period": 3, "required_through_period": 5},
        ]})
        self.assertEqual(result["capitalized_total"], 60000)
        self.assertEqual(result["schedules"]["land_opex_by_period"], {1: 1000, 2: 1000, 3: 1000})
        self.assertIn("expires in period 3", result["warnings"][0])
        self.assertEqual(result["land_rights"][0]["provenance"]["reference"], "ROW-17")

    def test_insurance_requires_explicit_premium_and_supports_miga_categories(self):
        with self.assertRaisesRegex(ValueError, "no premium default"):
            analyze_risk_costs({"insurance_policies": [{"policy_id": "p1", "category": "expropriation", "start_period": 0, "end_period": 10, "treatment": "capitalized"}]})
        result = analyze_risk_costs({"insurance_policies": [{
            "policy_id": "p1", "category": "transfer_restriction", "start_period": 1, "end_period": 2,
            "premium_basis": "percent_insured_value", "insured_value": 1_000_000, "premium_rate": .01,
            "broker_fee": 500, "premium_tax": 250, "frequency": "annual", "treatment": "expensed",
        }]})
        self.assertTrue(result["insurance_policies"][0]["miga_relevant"])
        self.assertEqual(result["schedules"]["insurance_opex_by_period"], {1: 10750, 2: 10750})
        self.assertFalse(result["checks"]["wacc_adjustment_applied"])

    def test_capitalization_and_no_double_counting_in_economic_response(self):
        payload = {
            "model": "total_economic_design",
            "project": {"currency": "USD", "capacity_m3d": 100},
            "operating": {"capacity_m3d": 100, "availability": 1, "project_life_years": 10},
            "risk_costs": {
                "land_rights": [{"item_id": "land", "type": "purchase", "amount": 100000, "start_period": 0, "treatment": "capex"}],
                "insurance_policies": [{"policy_id": "ops", "category": "operating_property", "start_period": 1, "end_period": 10, "premium_basis": "fixed", "premium_amount": 5000, "frequency": "annual", "treatment": "expensed"}],
                "guarantees": [{"instrument_id": "pcg", "type": "partial_credit", "start_period": 0, "end_period": 0, "fee_amount": 2000, "treatment": "capitalized"}],
            },
        }
        result = economic_analysis(payload)
        self.assertEqual(result["risk_costs"]["capitalized_total"], 102000)
        self.assertEqual(result["cost_hierarchy"]["total_project_cost"], 102000)
        self.assertEqual(result["operating"]["risk_cost_opex_y"], 5000)
        self.assertEqual(result["operating"]["annual_opex_y"], 5000)

    def test_guarantee_fee_schedule_and_expiry(self):
        result = analyze_risk_costs({"guarantees": [{
            "instrument_id": "nhg", "type": "non_honoring_guarantee",
            "start_period": 1, "end_period": 4, "required_through_period": 6,
            "fee_amount": 2500, "frequency": "annual", "treatment": "expensed",
            "source": "lender_term_sheet", "reference": "TS-4",
        }]})
        self.assertEqual(result["schedules"]["guarantee_opex_by_period"], {1: 2500, 2: 2500, 3: 2500, 4: 2500})
        self.assertIn("expires in period 4", result["warnings"][0])
        self.assertEqual(result["guarantees"][0]["provenance"]["reference"], "TS-4")


if __name__ == "__main__":
    unittest.main()
