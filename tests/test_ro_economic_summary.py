import json
import unittest

from ro_economic_summary_v1 import (
    OPEX_CATEGORIES,
    build_ro_economic_summary,
    validate_twds_economic_summary,
)


class RoEconomicSummaryTests(unittest.TestCase):
    def base(self, scenario="conventional", **overrides):
        result = {
            "product_flow_m3h": 100,
            "flow_unit": "m3/h",
            "recovery": 0.5,
            "ro_sec": 2.5,
            "total_pressure_vessels": 10,
            "total_membrane_elements": 70,
            "electric_kw": 250,
            "technology": scenario,
        }
        result.update(overrides)
        return {
            "result": result,
            "source": {
                "project_id": "TROD-1-0",
                "scenario_id": scenario,
                "calculation_revision": "calc-1",
            },
            "assumptions": {},
        }

    def test_conventional_ro(self):
        summary = build_ro_economic_summary(self.base())
        self.assertGreater(summary["capex"]["ro_scope_installed_cost"], 0)
        self.assertGreater(summary["opex"]["annual"]["energy"], 0)

    def test_isobaric_erd(self):
        summary = build_ro_economic_summary(self.base("px"))
        self.assertTrue(any("erd:px" in item["item_id"] for item in summary["capex"]["cost_items"]))

    def test_turbocharger(self):
        summary = build_ro_economic_summary(self.base("single"))
        self.assertTrue(any("erd:turbo" in item["item_id"] for item in summary["capex"]["cost_items"]))

    def test_multistage_membrane_inventory(self):
        payload = self.base(
            total_pressure_vessels=None,
            total_membrane_elements=None,
            stage1_pressure_vessels=8,
            elements_per_vessel_1=7,
            stage2_pressure_vessels=4,
            elements_per_vessel_2=7,
        )
        summary = build_ro_economic_summary(payload)
        membrane = next(item for item in summary["capex"]["cost_items"] if item["description"] == "RO/NF membrane elements")
        self.assertEqual(membrane["quantity"], 84)

    def test_different_pump_duties_change_capex(self):
        low = build_ro_economic_summary(self.base(electric_kw=200))
        high = build_ro_economic_summary(self.base(electric_kw=400))
        self.assertGreater(high["capex"]["equipment_purchase"], low["capex"]["equipment_purchase"])

    def test_electricity_price_changes_energy_opex(self):
        low = self.base(); low["assumptions"]["electricity_price_kwh"] = 0.05
        high = self.base(); high["assumptions"]["electricity_price_kwh"] = 0.15
        self.assertAlmostEqual(
            build_ro_economic_summary(high)["opex"]["annual"]["energy"],
            3 * build_ro_economic_summary(low)["opex"]["annual"]["energy"],
        )

    def test_membrane_replacement_interval(self):
        short = self.base(); short["assumptions"]["membrane_replacement_interval_years"] = 2
        long = self.base(); long["assumptions"]["membrane_replacement_interval_years"] = 10
        self.assertGreater(
            build_ro_economic_summary(short)["opex"]["annual"]["replacement"],
            build_ro_economic_summary(long)["opex"]["annual"]["replacement"],
        )

    def test_zero_chemical_consumption(self):
        summary = build_ro_economic_summary(self.base())
        names = [item["description"] for item in summary["opex"]["opex_items"]]
        self.assertNotIn("Antiscalant", names)
        self.assertNotIn("Acid", names)

    def test_chemical_dosing_enabled(self):
        summary = build_ro_economic_summary(self.base(antiscalant_dose_mg_l=3, acid_dose_mg_l=10))
        names = [item["description"] for item in summary["opex"]["opex_items"]]
        self.assertIn("Antiscalant", names)
        self.assertIn("Acid", names)

    def test_serialization_deserialization(self):
        summary = build_ro_economic_summary(self.base())
        self.assertTrue(validate_twds_economic_summary(json.loads(json.dumps(summary))))

    def test_no_duplicate_cost_items(self):
        summary = build_ro_economic_summary(self.base("biturbo"))
        items = summary["capex"]["cost_items"] + summary["opex"]["opex_items"]
        ids = [item["item_id"] for item in items]
        self.assertEqual(len(ids), len(set(ids)))

    def test_contract_v1_and_no_variable_double_count(self):
        summary = build_ro_economic_summary(self.base())
        self.assertEqual(summary["contract"], "twds.economic_summary")
        self.assertEqual(summary["version"], "1.0")
        self.assertEqual(summary["opex"]["annual"]["variable"], 0.0)
        self.assertAlmostEqual(
            sum(summary["opex"]["annual"][key] for key in OPEX_CATEGORIES),
            summary["opex"]["total_annual"],
        )

    def test_pretreatment_energy_is_explicit_only(self):
        payload = self.base(pretreatment_sec=0.5)
        excluded = build_ro_economic_summary(payload)
        payload["assumptions"]["include_pretreatment_energy"] = True
        included = build_ro_economic_summary(payload)
        self.assertGreater(included["opex"]["energy_kwh_y"], excluded["opex"]["energy_kwh_y"])


if __name__ == "__main__":
    unittest.main()
