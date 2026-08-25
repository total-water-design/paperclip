import unittest

from economic_guardrails import prepare_source_summaries, validate_project_cost_currencies


class GuardrailTests(unittest.TestCase):
    def test_specialist_project_level_contingency_is_rejected(self):
        bad = {
            "source": {"application_id": "ro"},
            "capex": {"buckets": {"equipment_purchase": 1, "contingency": 2}},
        }
        with self.assertRaisesRegex(ValueError, "project-level CAPEX bucket"):
            prepare_source_summaries([bad])

    def test_excluded_summary_does_not_trigger_ownership_or_duplicate_guardrails(self):
        excluded = {
            "included": False,
            "source": {"application_id": "ro"},
            "capex": {"buckets": {"equipment_purchase": 1, "contingency": 2}},
            "details": {"opex_items": [{"item_id": "shared", "category": "energy", "amount_annual": 10}]},
        }
        included = {
            "source": {"application_id": "bio"},
            "details": {"opex_items": [{"item_id": "shared", "category": "energy", "amount_annual": 20}]},
        }
        prepared, warnings = prepare_source_summaries([excluded, included])
        self.assertEqual(len(prepared), 2)
        self.assertFalse(prepared[0]["included"])
        self.assertIsInstance(warnings, list)

    def test_manual_mixed_currency_requires_provenance_backed_conversion(self):
        base = {
            "item_id": "civil",
            "description": "Local civil work",
            "bucket": "direct_installation",
            "amount": 100,
            "currency": "CLP",
            "source_type": "user",
            "source_reference": "Local estimate",
        }
        with self.assertRaisesRegex(ValueError, "Explicit fx_rate is required"):
            validate_project_cost_currencies([base], "USD")
        with self.assertRaisesRegex(ValueError, "fx_source is required"):
            validate_project_cost_currencies([{**base, "fx_rate": 0.0011}], "USD")
        validate_project_cost_currencies(
            [{
                **base,
                "fx_rate": 0.0011,
                "fx_source": "explicit_test_rate",
                "converted_amount": 0.11,
                "reporting_currency": "USD",
            }],
            "USD",
        )

    def test_duplicate_opex_ids_across_sources_are_rejected(self):
        a = {
            "source": {"application_id": "ro"},
            "details": {"opex_items": [{"item_id": "shared", "category": "energy", "amount_annual": 10}]},
        }
        b = {
            "source": {"application_id": "bio"},
            "details": {"opex_items": [{"item_id": "shared", "category": "energy", "amount_annual": 20}]},
        }
        with self.assertRaisesRegex(ValueError, "Duplicate OPEX economic item"):
            prepare_source_summaries([a, b])

    def test_opex_detail_mismatch_generates_warning(self):
        a = {
            "source": {"application_id": "ro"},
            "opex": {"annual": {"energy": 100}},
            "details": {"opex_items": [{"item_id": "e1", "category": "energy", "amount_annual": 90}]},
        }
        _, warnings = prepare_source_summaries([a])
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
