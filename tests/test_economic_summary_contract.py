import unittest

from economic_summary_contract import (
    CONTRACT_ID,
    CONTRACT_VERSION,
    aggregate_summaries,
    normalize_summary,
)


class EconomicSummaryContractTests(unittest.TestCase):
    @staticmethod
    def canonical(**overrides):
        summary = {
            "contract_id": CONTRACT_ID,
            "contract_version": CONTRACT_VERSION,
            "summary_id": "ro:TROD-1-0:base",
            "source": {
                "application_id": "ro",
                "application_name": "Total RO Design",
                "project_id": "TROD-1-0",
                "project_revision": "0",
                "scenario_id": "base",
                "calculation_revision": "calc-7",
            },
            "basis": {
                "currency": "USD",
                "capacity_m3d": 10000,
                "availability": 0.95,
            },
            "capex": {
                "cost_items": [{
                    "item_id": "ro:TROD-1-0:base:pump:hpp",
                    "scope_key": "ro.TROD-1-0.base.pump.hpp",
                    "description": "High pressure pump",
                    "bucket": "equipment_purchase",
                    "quantity": 1,
                    "unit": "LS",
                    "unit_cost": 1000000,
                    "amount": 1000000,
                    "currency": "USD",
                    "source_type": "user_entered_estimate",
                    "source_reference": "RO economic assumption",
                }]
            },
            "opex_annual": {
                "fixed": 0,
                "variable": 0,
                "energy": 400000,
                "chemicals": 100000,
                "labor": 0,
                "maintenance": 50000,
                "replacement": 50000,
                "disposal": 0,
                "other": 0,
                "total": 600000,
            },
            "details": {
                "opex_items": [{
                    "item_id": "ro:TROD-1-0:base:opex:energy",
                    "scope_key": "ro.TROD-1-0.base.opex.energy",
                    "description": "RO electricity",
                    "category": "energy",
                    "amount_annual": 400000,
                    "currency": "USD",
                }]
            },
        }
        summary.update(overrides)
        return summary

    def test_prompt_style_opex_annual_is_accepted(self):
        normalized = normalize_summary(self.canonical(), project_currency="USD")
        self.assertEqual(normalized["opex"]["energy"], 400000)
        self.assertEqual(normalized["opex"]["chemicals"], 100000)
        self.assertEqual(normalized["opex"]["total"], 600000)

    def test_declared_wrong_contract_is_rejected(self):
        bad = self.canonical(contract_id="other.contract")
        with self.assertRaisesRegex(ValueError, "Unsupported economic-summary contract"):
            normalize_summary(bad, project_currency="USD")

    def test_declared_wrong_version_is_rejected(self):
        bad = self.canonical(contract_version="2.0")
        with self.assertRaisesRegex(ValueError, "Unsupported twds.economic_summary version"):
            normalize_summary(bad, project_currency="USD")

    def test_legacy_undeclared_contract_remains_supported(self):
        legacy = {
            "summary_id": "legacy-ro",
            "source": {"application_id": "ro"},
            "currency": "USD",
            "capex_usd": 1000,
            "annual_opex_usd": 100,
        }
        aggregate = aggregate_summaries([legacy], project_currency="USD")
        self.assertEqual(aggregate["capex_total"], 1000)
        self.assertEqual(aggregate["annual_opex_total"], 100)
        self.assertTrue(aggregate["warnings"])

    def test_source_revision_metadata_is_preserved(self):
        normalized = normalize_summary(self.canonical(), project_currency="USD")
        self.assertEqual(normalized["source"]["project_revision"], "0")
        self.assertEqual(normalized["source"]["calculation_revision"], "calc-7")
        self.assertEqual(normalized["capacity_m3d"], 10000)

    def test_ro_namespaced_item_id_is_not_double_prefixed(self):
        normalized = normalize_summary(self.canonical(), project_currency="USD")
        item = normalized["cost_items"][0]
        self.assertEqual(item["item_id"], "ro:TROD-1-0:base:pump:hpp")
        self.assertEqual(item["source_type"], "user")
        self.assertEqual(item["source_type_original"], "user_entered_estimate")

    def test_scope_keys_are_inferred_from_detailed_items(self):
        normalized = normalize_summary(self.canonical(), project_currency="USD")
        self.assertIn("ro.TROD-1-0.base.pump.hpp", normalized["scope_keys"])
        self.assertIn("ro.TROD-1-0.base.opex.energy", normalized["scope_keys"])

    def test_same_currency_gets_identity_fx_metadata(self):
        normalized = normalize_summary(self.canonical(), project_currency="USD")
        item = normalized["cost_items"][0]
        self.assertEqual(normalized["reporting_currency"], "USD")
        self.assertEqual(normalized["native_currencies"], ["USD"])
        self.assertEqual(normalized["fx"]["status"], "identity")
        self.assertEqual(item["fx_rate"], 1.0)
        self.assertEqual(item["fx_source"], "identity")
        self.assertEqual(item["converted_amount"], item["amount"])

    def test_mixed_native_currency_is_rejected_until_shared_fx_exists(self):
        mixed = self.canonical()
        mixed["capex"]["cost_items"][0]["currency"] = "EUR"
        mixed["capex"]["cost_items"][0]["native_currency"] = "EUR"
        with self.assertRaisesRegex(ValueError, "shared FX service is not active yet"):
            normalize_summary(mixed, project_currency="USD")


if __name__ == "__main__":
    unittest.main()
