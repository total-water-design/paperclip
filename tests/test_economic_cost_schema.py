import unittest

from economic_cost_schema import (
    COST_BREAKDOWN_STRUCTURE,
    SCHEMA_ID,
    SCHEMA_VERSION,
    canonicalize_cost_item,
    canonicalize_cost_items,
)


class EconomicCostSchemaTests(unittest.TestCase):
    def test_basic_cost_is_normalized_to_formal_cbs(self):
        item = canonicalize_cost_item({
            "item_id": "P-101",
            "description": "High pressure pump",
            "bucket": "equipment_purchase",
            "quantity": 2,
            "unit": "ea",
            "unit_cost": 500000,
            "source_type": "vendor_quote",
            "source_reference": "Vendor proposal VP-22",
            "vendor": "Pump Vendor",
            "quote_date": "2026-08-01",
        })
        self.assertEqual(item["schema_id"], SCHEMA_ID)
        self.assertEqual(item["schema_version"], SCHEMA_VERSION)
        self.assertEqual(item["cbs_code"], COST_BREAKDOWN_STRUCTURE["equipment_purchase"]["code"])
        self.assertEqual(item["native_amount"], 1_000_000)
        self.assertEqual(item["amount"], 1_000_000)
        self.assertEqual(item["fx_rate"], 1.0)
        self.assertTrue(item["provenance"]["is_complete"])

    def test_missing_vendor_quote_metadata_is_visible_not_silently_accepted(self):
        item = canonicalize_cost_item({
            "item_id": "P-102",
            "bucket": "equipment_purchase",
            "amount": 100,
            "source_type": "vendor_quote",
        })
        self.assertFalse(item["provenance"]["is_complete"])
        self.assertIn("source_reference", item["provenance"]["missing_fields"])
        self.assertIn("vendor", item["provenance"]["missing_fields"])
        self.assertGreater(len(item["provenance"]["warnings"]), 0)

    def test_cross_currency_requires_explicit_rate_and_source(self):
        with self.assertRaisesRegex(ValueError, "fx_rate"):
            canonicalize_cost_item({
                "bucket": "equipment_purchase",
                "amount": 100,
                "native_currency": "EUR",
                "reporting_currency": "USD",
            })

        with self.assertRaisesRegex(ValueError, "fx_source"):
            canonicalize_cost_item({
                "bucket": "equipment_purchase",
                "amount": 100,
                "native_currency": "EUR",
                "reporting_currency": "USD",
                "fx_rate": 1.1,
            })

        item = canonicalize_cost_item({
            "bucket": "equipment_purchase",
            "amount": 100,
            "native_currency": "EUR",
            "reporting_currency": "USD",
            "fx_rate": 1.1,
            "fx_source": "Treasury snapshot",
            "fx_snapshot_id": "FX-2026-08-23",
        })
        self.assertAlmostEqual(item["amount"], 110.0)
        self.assertEqual(item["currency"], "USD")
        self.assertEqual(item["native_currency"], "EUR")

    def test_lineage_and_estimate_context_are_preserved(self):
        item = canonicalize_cost_item(
            {
                "item_id": "RO-SKID-1",
                "bucket": "equipment_purchase",
                "amount": 5_000_000,
                "source_type": "database",
                "source_reference": "Shared equipment database",
                "price_date": "2026-07-01",
            },
            project_context={
                "currency": "USD",
                "project_id": "TROD-25-0",
                "project_revision": "0",
                "scenario_id": "base",
                "calculation_revision": "calc-17",
                "summary_id": "RO-BASE",
                "source_application": "Total RO Design",
                "estimate_id": "E03",
                "estimate_revision": "3",
                "estimate_class": "Class 3",
            },
        )
        self.assertEqual(item["source_application"], "Total RO Design")
        self.assertEqual(item["source_project_id"], "TROD-25-0")
        self.assertEqual(item["source_summary_id"], "RO-BASE")
        self.assertEqual(item["estimate_id"], "E03")
        self.assertEqual(item["estimate_class_context"], "Class 3")

    def test_custom_cbs_system_may_use_owner_codes(self):
        item = canonicalize_cost_item({
            "bucket": "owner_cost",
            "cbs_system": "OWNER-WBS",
            "cbs_code": "OC-17",
            "amount": 100,
            "source_type": "allowance",
            "source_reference": "Owner estimate basis",
        })
        self.assertEqual(item["cbs_system"], "OWNER-WBS")
        self.assertEqual(item["cbs_code"], "OC-17")

    def test_twds_cbs_code_must_match_bucket_family(self):
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            canonicalize_cost_item({
                "bucket": "contingency",
                "cbs_code": "1000",
                "amount": 100,
            })

    def test_duplicate_item_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            canonicalize_cost_items([
                {"item_id": "X", "bucket": "equipment_purchase", "amount": 1},
                {"item_id": "X", "bucket": "direct_installation", "amount": 2},
            ])


if __name__ == "__main__":
    unittest.main()
