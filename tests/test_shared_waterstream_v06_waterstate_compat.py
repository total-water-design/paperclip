from __future__ import annotations

from pathlib import Path
import unittest

import shared_waterstream as sw
import shared_water_chemistry
from shared_water_chemistry.engine import equilibrate
from shared_water_chemistry.water_state import SCHEMA_ID as WATERSTATE_SCHEMA_ID
from shared_water_chemistry.water_state import SCHEMA_VERSION as WATERSTATE_SCHEMA_VERSION
from shared_water_chemistry.water_state import WaterState

MW = sw.H2O_MOLAR_MASS_G_MOL
EXPECTED_CHEMISTRY_ROOT = Path("/tmp/shared-water-chemistry").resolve()


def stream_fixture():
    flow = 1.0
    water_kg_s = 1000.0
    components = {
        "h2o": water_kg_s * 1000.0 / MW,
        "sodium": 8.0,
        "chloride": 8.0,
        "calcium": 0.5,
        "magnesium": 0.6,
        "sulfate": 0.4,
        "total_boron": 0.01,
        "total_silica": 0.02,
        "total_inorganic_carbon": 2.4,
    }
    return sw.WaterStream(
        "compat", 25.0, 2.0, sw.FrozenDict(components), 2.1,
        chemistry_policy=sw.FrozenDict({"gas_boundary": "closed"}),
        provenance=(
            sw.ProvenanceRecord(
                "application", "compat-fixture", "total-water-balance",
                "waterstream-to-waterstate", "test",
            ),
        ),
        aqueous_volume_flow_m3_s=flow,
    )


def to_waterstate(stream: sw.WaterStream) -> WaterState:
    report = stream.chemistry_handoff_report()
    unsupported = tuple(report["chemistry_owned_analytical_families_present"])
    if unsupported:
        raise ValueError(
            f"Chemistry adapter must map analytical families before handoff: {unsupported}"
        )
    composition = {}
    for waterstream_key, waterstate_key in sw.WATERSTATE_DIRECT_COMPOSITION_MAP.items():
        if float(stream.component_totals_mol_s.get(waterstream_key, 0.0)) != 0.0:
            composition[waterstate_key] = stream.component_mg_l(waterstream_key)
    source = stream.latest_provenance
    return WaterState(
        composition_mg_l=composition,
        temperature_c=stream.temperature_c,
        pressure_bar=stream.pressure_bar,
        ph=None,
        total_alkalinity_mol_kg=stream.total_alkalinity_mol_kg_water,
        total_inorganic_carbon_mol_kg=stream.total_inorganic_carbon_mol_kg_water,
        source_application=None if source is None else source.application,
        source_process=None if source is None else source.process,
        equilibrium={},
        metadata={
            "waterstream_schema": sw.WATERSTREAM_SCHEMA_ID,
            "waterstream_version": sw.SCHEMA_VERSION,
            "waterstream_state_hash": stream.state_hash,
        },
    ).normalized()


class SharedWaterStreamV06WaterStateCompatibilityTests(unittest.TestCase):
    def test_imported_chemistry_package_is_exact_detached_worktree(self):
        module_path = Path(shared_water_chemistry.__file__).resolve()
        self.assertTrue(
            module_path.is_relative_to(EXPECTED_CHEMISTRY_ROOT),
            f"shared_water_chemistry imported from {module_path}, expected under {EXPECTED_CHEMISTRY_ROOT}",
        )

    def test_exact_chemistry_milestone_contract_is_the_expected_waterstate_schema(self):
        self.assertEqual(WATERSTATE_SCHEMA_ID, "twds.water-state")
        self.assertEqual(WATERSTATE_SCHEMA_VERSION, 1)

    def test_waterstream_constructs_actual_waterstate_without_upstream_ph(self):
        stream = stream_fixture()
        state = to_waterstate(stream)
        self.assertIsNone(state.ph)
        self.assertEqual(state.equilibrium_basis_count, 2)
        self.assertAlmostEqual(state.total_alkalinity_mol_kg,
                               stream.total_alkalinity_mol_kg_water, places=15)
        self.assertAlmostEqual(state.total_inorganic_carbon_mol_kg,
                               stream.total_inorganic_carbon_mol_kg_water, places=15)
        self.assertEqual(state.temperature_c, stream.temperature_c)
        self.assertEqual(state.pressure_bar, stream.pressure_bar)
        self.assertEqual(state.source_application, "total-water-balance")
        self.assertEqual(state.source_process, "waterstream-to-waterstate")
        self.assertEqual(state.metadata["waterstream_state_hash"], stream.state_hash)

    def test_direct_mg_l_basis_survives_waterstate_normalization(self):
        stream = stream_fixture()
        state = to_waterstate(stream)
        for ws_key, state_key in sw.WATERSTATE_DIRECT_COMPOSITION_MAP.items():
            if float(stream.component_totals_mol_s.get(ws_key, 0.0)) != 0.0:
                self.assertAlmostEqual(state.composition_mg_l[state_key],
                                       stream.component_mg_l(ws_key), places=12)
        # WaterStream did not supply carbonate species or TIC as composition.
        # WaterState.normalize_composition() intentionally materializes its full
        # canonical chemistry dictionary with zero placeholders.  Those zero
        # placeholders are chemistry-owned defaults, not transported conserved
        # quantities or upstream speciation claims.
        self.assertNotIn("total_inorganic_carbon", state.composition_mg_l)
        self.assertEqual(state.composition_mg_l["bicarbonate"], 0.0)
        self.assertEqual(state.composition_mg_l["carbonate"], 0.0)

    def test_waterstate_handoff_roundtrip_preserves_adapter_basis(self):
        state = to_waterstate(stream_fixture())
        payload = state.to_handoff()
        restored = WaterState.from_handoff(payload)
        self.assertEqual(restored.to_handoff(), payload)
        self.assertIsNone(restored.ph)
        self.assertEqual(restored.equilibrium_basis_count, 2)

    def test_exact_chemistry_engine_accepts_ta_plus_ct_and_solves_ph(self):
        state = to_waterstate(stream_fixture())
        solved = equilibrate(state)
        self.assertIsNotNone(solved.ph)
        self.assertEqual(solved.equilibrium["basis"], "TA+CT -> pH")
        self.assertAlmostEqual(solved.total_alkalinity_mol_kg,
                               state.total_alkalinity_mol_kg, places=10)
        self.assertAlmostEqual(solved.total_inorganic_carbon_mol_kg,
                               state.total_inorganic_carbon_mol_kg, places=10)

    def test_nonzero_unmapped_analytical_family_fails_closed_before_waterstate(self):
        stream = stream_fixture()
        components = stream.component_totals_mol_s.to_dict()
        components["total_ammonia"] = 0.1
        stream = sw.WaterStream(
            "unsupported-family", stream.temperature_c, stream.pressure_bar,
            sw.FrozenDict(components), stream.toth_eq_s,
            chemistry_policy=stream.chemistry_policy,
            provenance=stream.provenance,
            aqueous_volume_flow_m3_s=stream.flow_m3_s,
        )
        with self.assertRaises(ValueError):
            to_waterstate(stream)


if __name__ == "__main__":
    unittest.main()
