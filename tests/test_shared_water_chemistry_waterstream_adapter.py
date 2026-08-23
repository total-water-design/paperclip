from __future__ import annotations

import math
import unittest

import shared_waterstream as sw

from shared_water_chemistry import (
    CHEMISTRY_REFERENCE_SHA,
    WATERSTREAM_REFERENCE_SHA,
    WATERSTREAM_SCHEMA_VERSION,
    SharedChemistryCertificateIssuer,
    WaterStreamAdapterError,
    certify_waterstream,
    equilibrate_waterstream,
    waterstream_to_waterstate,
)

MW = sw.H2O_MOLAR_MASS_G_MOL


def stream_fixture(
    *,
    unsupported_family: str | None = None,
    flow_m3_s: float = 1.0,
    water_kg_s: float = 990.0,
):
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
    if unsupported_family is not None:
        components[unsupported_family] = 0.1
    return sw.WaterStream(
        "production-adapter-fixture",
        25.0,
        2.0,
        sw.FrozenDict(components),
        2.1,
        chemistry_policy=sw.FrozenDict({"gas_boundary": "closed"}),
        provenance=(
            sw.ProvenanceRecord(
                "application",
                "fixture-1",
                "total-water-balance",
                "waterstream-to-shared-chemistry",
                "test",
            ),
        ),
        aqueous_volume_flow_m3_s=flow_m3_s,
    )


def solid_stream_fixture():
    components = {"calcium": 1.0, "total_inorganic_carbon": 1.0}
    inventory = (
        sw.PhaseInventoryItem(
            sw.StreamPhase.SOLID,
            "calcite",
            sw.FrozenDict(components),
        ),
    )
    return sw.WaterStream(
        "production-adapter-solid-fixture",
        25.0,
        2.0,
        sw.FrozenDict(components),
        0.0,
        phase=sw.StreamPhase.SOLID,
        phase_inventory=inventory,
        chemistry_policy=sw.FrozenDict({"gas_boundary": "closed"}),
        provenance=(
            sw.ProvenanceRecord(
                "application",
                "solid-fixture-1",
                "total-water-balance",
                "waterstream-to-shared-chemistry",
                "test",
            ),
        ),
        aqueous_volume_flow_m3_s=None,
    )


class SharedWaterChemistryWaterStreamAdapterTests(unittest.TestCase):
    def test_pinned_contract_versions(self):
        self.assertEqual(sw.SCHEMA_VERSION, "0.6.0")
        self.assertEqual(WATERSTREAM_SCHEMA_VERSION, "0.6.0")
        self.assertEqual(WATERSTREAM_REFERENCE_SHA, "e43bd4e1f86f657528e83dc9e185970443d30f4b")
        self.assertEqual(CHEMISTRY_REFERENCE_SHA, "6fdbb11e025130162f749a7b77191e108f183d15")

    def test_exact_waterstream_aqueous_enum_is_accepted(self):
        stream = stream_fixture()
        self.assertIs(stream.phase, sw.StreamPhase.AQUEOUS)
        self.assertEqual(stream.phase.value, "AQUEOUS")
        state = waterstream_to_waterstate(stream)
        self.assertEqual(state.metadata["waterstream_stream_id"], stream.stream_id)

    def test_non_aqueous_stream_fails_closed(self):
        stream = solid_stream_fixture()
        self.assertIs(stream.phase, sw.StreamPhase.SOLID)
        with self.assertRaises(WaterStreamAdapterError):
            waterstream_to_waterstate(stream)

    def test_conversion_uses_conserved_ta_tic_and_never_upstream_ph(self):
        stream = stream_fixture()
        state = waterstream_to_waterstate(stream)
        self.assertIsNone(state.ph)
        self.assertEqual(state.equilibrium_basis_count, 2)
        self.assertAlmostEqual(state.total_alkalinity_mol_kg, stream.total_alkalinity_mol_kg_water, places=15)
        self.assertAlmostEqual(state.total_inorganic_carbon_mol_kg, stream.total_inorganic_carbon_mol_kg_water, places=15)
        self.assertEqual(state.metadata["waterstream_state_hash"], stream.state_hash)
        self.assertEqual(state.metadata["waterstream_stream_id"], stream.stream_id)
        self.assertEqual(state.source_application, "total-water-balance")
        self.assertEqual(state.source_process, "waterstream-to-shared-chemistry")

    def test_direct_component_conversion_preserves_full_precision(self):
        stream = stream_fixture()
        state = waterstream_to_waterstate(stream)
        for ws_key, waterstate_key in sw.WATERSTATE_DIRECT_COMPOSITION_MAP.items():
            if float(stream.component_totals_mol_s.get(ws_key, 0.0)) != 0.0:
                self.assertEqual(state.composition_mg_l[waterstate_key], stream.component_mg_l(ws_key))

    def test_equilibrium_is_reconstructed_from_ta_and_tic(self):
        stream = stream_fixture()
        solved = equilibrate_waterstream(stream)
        self.assertIsNotNone(solved.ph)
        self.assertTrue(math.isfinite(float(solved.ph)))
        self.assertEqual(solved.equilibrium["basis"], "TA+CT -> pH")
        self.assertAlmostEqual(solved.total_alkalinity_mol_kg, stream.total_alkalinity_mol_kg_water, places=10)
        self.assertAlmostEqual(solved.total_inorganic_carbon_mol_kg, stream.total_inorganic_carbon_mol_kg_water, places=10)

    def test_nonzero_unmapped_family_fails_closed(self):
        for family in sw.CHEMISTRY_OWNED_ANALYTICAL_FAMILIES:
            with self.subTest(family=family):
                with self.assertRaises(WaterStreamAdapterError):
                    waterstream_to_waterstate(stream_fixture(unsupported_family=family))

    def test_issuer_produces_certificate_waterstream_accepts(self):
        stream = stream_fixture()
        cert = SharedChemistryCertificateIssuer().issue(stream)
        rebound = stream.with_chemistry_certificate(cert)
        self.assertIs(rebound.require_valid_chemistry_certificate(), cert)
        self.assertEqual(cert.state_hash, stream.state_hash)
        self.assertEqual(cert.residual_charge_eq_s, stream.fixed_charge_residual_eq_s)
        self.assertAlmostEqual(cert.solvent_water_kg_s, stream.solvent_water_kg_s_from_components, places=12)
        self.assertGreaterEqual(cert.ionic_strength_mol_kg, 0.0)
        self.assertGreater(cert.density_kg_m3, 0.0)
        self.assertGreaterEqual(cert.solution_mass_kg_s, cert.solvent_water_kg_s)
        self.assertIn("equilibrium_ph", cert.metadata)
        self.assertIn("equilibrium_charge_residual_eq_s", cert.metadata)

    def test_small_density_basis_mismatch_is_bounded_and_auditable(self):
        # Match the exact WaterStream v0.6 issuer-conformance hydraulic/H2O basis.
        stream = stream_fixture(water_kg_s=1000.0, flow_m3_s=1.0)
        cert = SharedChemistryCertificateIssuer().issue(stream)
        self.assertTrue(cert.metadata["density_reconciled_to_transport_minimum"])
        self.assertLessEqual(cert.metadata["density_relative_shortfall"], 0.01)
        self.assertEqual(cert.density_kg_m3, cert.metadata["transport_minimum_density_kg_m3"])
        stream.with_chemistry_certificate(cert).require_valid_chemistry_certificate()

    def test_certify_waterstream_cache_is_deterministic(self):
        stream = stream_fixture()
        cache = sw.ChemistryCertificateCache()
        issuer = SharedChemistryCertificateIssuer()
        first = certify_waterstream(stream, issuer=issuer, cache=cache)
        second = certify_waterstream(stream, issuer=issuer, cache=cache)
        self.assertEqual(first.chemistry_certificate.to_dict(), second.chemistry_certificate.to_dict())
        self.assertEqual(len(cache), 1)

    def test_waterstream_issuer_conformance_protocol(self):
        issuer = SharedChemistryCertificateIssuer(require_provenance=False)
        report = sw.assert_issuer_conformant(issuer)
        self.assertTrue(report["cold_warm_equivalent"])
        self.assertTrue(report["deterministic_identical_inputs"])
        self.assertTrue(report["residual_charge_verified"])
        self.assertTrue(report["solvent_water_verified"])

    def test_inconsistent_hydraulic_flow_and_h2o_inventory_fails_closed(self):
        stream = stream_fixture(flow_m3_s=0.5)
        with self.assertRaises(WaterStreamAdapterError):
            SharedChemistryCertificateIssuer().issue(stream)


if __name__ == "__main__":
    unittest.main()
