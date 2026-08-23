from __future__ import annotations

import unittest

from advanced_chemistry import equilibrium_charge_report, solve_carbonate_state
from shared_water_chemistry import (
    SCHEMA_ID,
    SCHEMA_VERSION,
    WaterState,
    equilibrate,
    prepare_handoff,
    receive_handoff,
)
from water_chemistry import charge_balance, ionic_strength_mol_kg


class WaterStateContractTests(unittest.TestCase):
    def test_handoff_preserves_ph_precision(self):
        state = WaterState(
            composition_mg_l={"sodium": 1000.0, "chloride": 1542.0},
            temperature_c=27.25,
            pressure_bar=3.2,
            ph=7.843672123,
            total_alkalinity_mol_kg=0.00231,
            total_inorganic_carbon_mol_kg=0.00257,
            source_application="total-pretreatment-design",
        )
        payload = state.to_handoff()
        restored = receive_handoff(payload)
        self.assertEqual(payload["schema"], SCHEMA_ID)
        self.assertEqual(payload["version"], SCHEMA_VERSION)
        self.assertEqual(restored.ph, 7.843672123)
        self.assertEqual(restored.total_alkalinity_mol_kg, 0.00231)
        self.assertEqual(restored.total_inorganic_carbon_mol_kg, 0.00257)
        self.assertEqual(restored.temperature_c, 27.25)
        self.assertEqual(restored.pressure_bar, 3.2)

    def test_unknown_components_do_not_cross_application_boundary(self):
        state = WaterState(
            composition_mg_l={
                "calcium": 125.0,
                "chloride": 240.0,
                "not_a_suite_species": 999.0,
            }
        ).normalized()
        self.assertEqual(state.composition_mg_l["calcium"], 125.0)
        self.assertNotIn("not_a_suite_species", state.composition_mg_l)

    def test_schema_rejects_wrong_version(self):
        payload = WaterState(composition_mg_l={}).to_handoff()
        payload["version"] = 999
        with self.assertRaises(ValueError):
            receive_handoff(payload)

    def test_balanced_nacl_charge_and_ionic_strength_regression(self):
        # Exactly 1 mmol/L NaCl on the Suite analytical mg/L basis.
        comp = {"sodium": 22.989769, "chloride": 35.453}
        charge = charge_balance(comp)
        self.assertAlmostEqual(charge["cations_meq_l"], 1.0, places=12)
        self.assertAlmostEqual(charge["anions_meq_l"], 1.0, places=12)
        self.assertAlmostEqual(charge["imbalance_pct"], 0.0, places=12)

        ionic_strength = ionic_strength_mol_kg(comp, 25.0)
        self.assertGreater(ionic_strength, 0.0)
        self.assertAlmostEqual(ionic_strength, 0.001, delta=5e-5)

    def test_ta_ct_equilibrium_roundtrip_overrides_stale_ph(self):
        comp = {
            "sodium": 230.0,
            "chloride": 180.0,
            "calcium": 40.0,
            "magnesium": 24.0,
            "boron": 1.0,
        }
        target_ph = 8.123456789
        ct = 0.0024
        reference = solve_carbonate_state(
            comp,
            25.0,
            ph=target_ph,
            total_inorganic_carbon_mol_kg=ct,
        )
        ta = float(reference["total_alkalinity_mol_kg"])

        # A stale/display-rounded upstream pH must not win over conserved TA+CT.
        state = WaterState(
            composition_mg_l=comp,
            temperature_c=25.0,
            pressure_bar=2.0,
            ph=6.5,
            total_alkalinity_mol_kg=ta,
            total_inorganic_carbon_mol_kg=ct,
        )
        solved = equilibrate(state)

        self.assertEqual(solved.equilibrium["basis"], "TA+CT -> pH")
        self.assertAlmostEqual(solved.ph, target_ph, delta=2e-8)
        self.assertAlmostEqual(solved.total_alkalinity_mol_kg, ta, delta=2e-10)
        self.assertAlmostEqual(solved.total_inorganic_carbon_mol_kg, ct, delta=2e-12)

        direct_charge = equilibrium_charge_report(
            solved.equilibrium["state"], solved.temperature_c
        )
        self.assertEqual(solved.equilibrium["charge_report"], direct_charge)

    def test_prepare_handoff_serializes_equilibrated_solver_precision(self):
        comp = {"sodium": 230.0, "chloride": 180.0, "calcium": 40.0}
        reference = solve_carbonate_state(
            comp,
            30.0,
            ph=7.987654321,
            total_inorganic_carbon_mol_kg=0.0021,
        )
        state = WaterState(
            composition_mg_l=comp,
            temperature_c=30.0,
            ph=7.0,
            total_alkalinity_mol_kg=float(reference["total_alkalinity_mol_kg"]),
            total_inorganic_carbon_mol_kg=0.0021,
        )
        payload = prepare_handoff(
            state,
            source_application="total-water-balance",
            destination_application="total-ro-design",
        )
        restored = receive_handoff(payload)

        self.assertAlmostEqual(restored.ph, 7.987654321, delta=2e-8)
        self.assertEqual(restored.source_application, "total-water-balance")
        self.assertEqual(
            restored.metadata["destination_application"], "total-ro-design"
        )
        self.assertEqual(restored.ph, payload["state"]["ph"])


if __name__ == "__main__":
    unittest.main()
