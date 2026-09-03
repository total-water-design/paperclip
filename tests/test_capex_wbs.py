import json
import unittest

from capex_wbs import analyze_capex_wbs
from economics import economic_analysis


def sample_nodes():
    return [
        {"wbs_id": "1", "name": "Plant", "scope": "process"},
        {"wbs_id": "1.1", "parent_wbs_id": "1", "name": "RO package", "scope": "process", "sourcing": "foreign", "native_amount": 100,
         "currency": "EUR", "fx_rate": 1.2, "fx_source": "Treasury", "fx_snapshot_id": "FX-01", "cpi_index": "CEPCI", "cpi_base": 800, "cpi_current": 840,
         "source_type": "vendor_quote", "source_reference": "Quote Q-7", "source_lineage": {"summary_id": "RO:E7"},
         "procurement": {"rfq_date": "2027-01-01", "po_date": "2027-02-01", "required_on_site_date": "2027-06-01"},
         "logistics": {"incoterm": "CIF", "origin": "Rotterdam", "destination": "Perth", "ship_date": "2027-03-01", "arrival_date": "2027-04-01"},
         "schedule": {"start_date": "2027-05-15", "duration_days": 40}},
        {"wbs_id": "1.2", "parent_wbs_id": "1", "name": "Local civil", "scope": "balance_of_plant", "sourcing": "local", "native_amount": 60,
         "currency": "USD", "source_type": "quantity_takeoff", "source_reference": "MTO-2", "schedule": {"start_date": "2027-05-01", "duration_days": 31}},
        {"wbs_id": "9", "name": "Excluded intake", "scope": "excluded", "sourcing": "local", "native_amount": 25, "currency": "USD"},
    ]


class CapexWbsTests(unittest.TestCase):
    def test_hierarchical_rollup_scope_sourcing_currency_cpi_and_schedule(self):
        result = analyze_capex_wbs({"nodes": sample_nodes()}, reporting_currency="USD")
        # 100 EUR * 1.05 CPI * 1.2 FX + 60 + 25 excluded.
        self.assertAlmostEqual(result["total"], 211)
        self.assertAlmostEqual(result["included_total"], 186)
        self.assertAlmostEqual(next(x for x in result["rollups"] if x["wbs_id"] == "1")["amount"], 186)
        self.assertAlmostEqual(result["by_scope"]["process"], 126)
        self.assertEqual(result["by_sourcing"]["local"], 85)
        self.assertEqual(result["leaf_ids"], ["1.1", "1.2", "9"])
        self.assertEqual([x["month"] for x in result["construction_schedule"]["monthly_spend"]], ["2027-05", "2027-06"])
        self.assertAlmostEqual(result["construction_schedule"]["scheduled_total"], 186)
        self.assertAlmostEqual(sum(x["amount"] for x in result["construction_schedule"]["monthly_spend"]), 186)
        foreign = next(x for x in result["nodes"] if x["wbs_id"] == "1.1")
        self.assertEqual(foreign["source_lineage"], {"summary_id": "RO:E7"})
        self.assertEqual(foreign["procurement"]["po_date"], "2027-02-01")
        self.assertEqual(foreign["logistics"]["incoterm"], "CIF")

    def test_parent_cost_is_rejected_to_prevent_double_counting(self):
        nodes = sample_nodes()
        nodes[0]["native_amount"] = 999
        with self.assertRaisesRegex(ValueError, "prevent double counting"):
            analyze_capex_wbs({"nodes": nodes})

    def test_ids_are_stable_required_unique_and_acyclic(self):
        with self.assertRaisesRegex(ValueError, "stable IDs"):
            analyze_capex_wbs({"nodes": [{"name": "No ID"}]})
        with self.assertRaisesRegex(ValueError, "Duplicate WBS ID"):
            analyze_capex_wbs({"nodes": [{"wbs_id": "A"}, {"wbs_id": "A"}]})
        with self.assertRaisesRegex(ValueError, "cycle"):
            analyze_capex_wbs({"nodes": [{"wbs_id": "A", "parent_wbs_id": "B"}, {"wbs_id": "B", "parent_wbs_id": "A"}]})

    def test_non_reporting_currency_requires_explicit_fx_lineage(self):
        with self.assertRaisesRegex(ValueError, "requires a positive FX rate"):
            analyze_capex_wbs({"nodes": [{"wbs_id": "A", "native_amount": 3, "currency": "EUR"}]}, reporting_currency="USD")

    def test_runtime_economics_includes_only_leaf_non_excluded_cost_once(self):
        result = economic_analysis({
            "model": "total_economic_design", "project": {"currency": "USD"},
            "capex_wbs": {"nodes": sample_nodes()},
            "operating": {"capacity_m3d": 1, "availability": 1, "project_life_years": 25},
        })
        self.assertAlmostEqual(result["source_aggregation"]["capex_total"], 0)
        self.assertAlmostEqual(result["cost_hierarchy"]["total_project_cost"], 186)
        self.assertAlmostEqual(result["capex_wbs"]["total"], 211)
        self.assertAlmostEqual(result["capex_wbs"]["excluded_total"], 25)

    def test_snapshot_export_import_json_preserves_contract_and_lineage(self):
        original = {"model": "total_economic_design", "capex_wbs": {"nodes": sample_nodes()}}
        restored = json.loads(json.dumps({"economics": original}))["economics"]
        self.assertEqual(restored, original)
        self.assertEqual(restored["capex_wbs"]["nodes"][1]["source_lineage"]["summary_id"], "RO:E7")

    def test_http_response_exposes_wbs_rollup_and_schedule(self):
        from app import app

        app.config.update(
            TESTING=True,
            AUTH_ENABLED=False,
            DEPLOYMENT_MODE="desktop",
            WTF_CSRF_ENABLED=False,
        )
        response = app.test_client().post("/api/economics", json={
            "model": "total_economic_design", "project": {"currency": "USD"},
            "capex_wbs": {"nodes": sample_nodes()},
            "operating": {"capacity_m3d": 1, "availability": 1, "project_life_years": 25},
        })
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        body = response.get_json()
        self.assertAlmostEqual(body["capex_wbs"]["included_total"], 186)
        self.assertAlmostEqual(body["cost_hierarchy"]["total_project_cost"], 186)
        self.assertEqual(body["capex_wbs"]["construction_schedule"]["monthly_spend"][0]["month"], "2027-05")


if __name__ == "__main__":
    unittest.main()
