import unittest

from ro_economic_pump_adapter import scenario_aware_pump_duties


class PumpAdapterTests(unittest.TestCase):
    def total(self, duties):
        return sum(value for _, value in duties)

    def by_kind(self, duties, kind):
        return sum(value for name, value in duties if name == kind)

    def test_multistage_does_not_double_count_aggregate(self):
        duties = scenario_aware_pump_duties(
            {"hpp_kw": 100, "booster_kw": 20, "electric_kw": 120}, 2400
        )
        self.assertEqual(self.total(duties), 120)
        self.assertEqual(self.by_kind(duties, "high_pressure_pump"), 100)
        self.assertEqual(self.by_kind(duties, "interstage_booster"), 20)

    def test_px_electric_is_hpp_and_circ_is_separate(self):
        duties = scenario_aware_pump_duties(
            {"electric_kw": 100, "circ_kw": 15, "ro_electric_kw": 116}, 2400
        )
        self.assertEqual(self.total(duties), 115)

    def test_interstage_px_splits_inclusive_booster(self):
        duties = scenario_aware_pump_duties(
            {"hpp_kw": 90, "booster_kw": 30, "circ_kw": 10, "electric_kw": 120}, 2400
        )
        self.assertEqual(self.total(duties), 120)
        self.assertEqual(self.by_kind(duties, "interstage_booster"), 20)
        self.assertEqual(self.by_kind(duties, "circulation_booster"), 10)

    def test_dweer_prefers_explicit_components(self):
        result = {
            "dweer_hpp_electric_kw": 70,
            "dweer_booster_electric_kw": 10,
            "dweer_lp_increment_electric_kw": 3,
            "dweer_inherited_interstage_booster_kw": 7,
            "electric_kw": 90,
        }
        self.assertEqual(self.total(scenario_aware_pump_duties(result, 2400)), 90)

    def test_pelton_avoids_aggregate_reuse(self):
        duties = scenario_aware_pump_duties(
            {
                "pelton_motor_electric_kw": 80,
                "pelton_inherited_interstage_booster_kw": 5,
                "electric_kw": 85,
            },
            2400,
        )
        self.assertEqual(self.total(duties), 85)

    def test_ccro_uses_peak_component_duties_for_capex(self):
        duties = scenario_aware_pump_duties(
            {
                "ccro_pressure_margin_bar": 5,
                "hpp_kw": 120,
                "circ_kw": 40,
                "electric_kw": 95,
            },
            2400,
        )
        self.assertEqual(self.total(duties), 160)

    def test_six_pd_pump_bank_preserves_six_physical_units(self):
        result = {
            "hpp_kw": 600,
            "electric_kw": 600,
            "pump_database_top_options": [
                {
                    "technology": "PD",
                    "installed_units": 6,
                    "duty_units": 6,
                    "wire_kw": 600,
                    "wire_kw_per_pump": 100,
                }
            ],
        }
        duties = scenario_aware_pump_duties(result, 2400)
        hpp = [item for item in duties if item[0] == "high_pressure_pump"]
        self.assertEqual(len(hpp), 6)
        self.assertEqual(sum(value for _, value in hpp), 600)
        self.assertTrue(all(abs(value - 100) < 1e-9 for _, value in hpp))

    def test_missing_electric_kw_uses_explicit_hpp_and_booster_components(self):
        duties = scenario_aware_pump_duties(
            {"hpp_kw": 100, "booster_kw": 20}, 2400
        )
        self.assertEqual(self.total(duties), 120)
        self.assertEqual(self.by_kind(duties, "high_pressure_pump"), 100)
        self.assertEqual(self.by_kind(duties, "interstage_booster"), 20)

    def test_missing_electric_kw_falls_back_to_ro_sec_when_no_component_power_exists(self):
        duties = scenario_aware_pump_duties({"ro_sec": 2.4}, 2400)
        self.assertEqual(duties, [("ro_pumping", 240.0)])

    def _assert_parallel_bank(self, technology, total_kw, units, *, use_installed=True):
        option = {
            "technology": technology,
            "wire_kw": total_kw,
            "wire_kw_per_pump": total_kw / units,
        }
        if use_installed:
            option["installed_units"] = units
        else:
            option["duty_units"] = units
        result = {
            "hpp_kw": total_kw,
            "electric_kw": total_kw,
            "pump_database_top_options": [option],
        }
        duties = scenario_aware_pump_duties(result, 2400)
        hpp = [value for kind, value in duties if kind == "high_pressure_pump"]
        self.assertEqual(len(hpp), units)
        self.assertAlmostEqual(sum(hpp), total_kw)
        self.assertTrue(all(abs(value - total_kw / units) < 1e-9 for value in hpp))

    def test_parallel_vcmp_bank_preserves_physical_units(self):
        self._assert_parallel_bank("VCMP", 400, 4)

    def test_parallel_hhecp_bank_preserves_physical_units_from_duty_units(self):
        self._assert_parallel_bank("HHECP", 360, 3, use_installed=False)


if __name__ == "__main__":
    unittest.main()
