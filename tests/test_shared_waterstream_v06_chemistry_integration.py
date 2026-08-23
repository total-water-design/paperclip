from __future__ import annotations

import json
import unittest
from dataclasses import FrozenInstanceError

import shared_waterstream as sw
import shared_waterstream.v05 as v05

MW = sw.H2O_MOLAR_MASS_G_MOL


def provenance(app="total-water-balance", process="unit-test"):
    return (sw.ProvenanceRecord("application", "fixture", app, process, "test"),)


def raw(name="s", *, flow=1.0, water_kg_s=999.0, na=1.0, cl=1.0,
        tic=0.0, toth=0.0, temperature=25.0, pressure=2.0,
        policy=None, extra_components=None, with_provenance=True):
    components = {
        "h2o": water_kg_s * 1000.0 / MW,
        "sodium": na,
        "chloride": cl,
    }
    if tic:
        components["total_inorganic_carbon"] = tic
    components.update(extra_components or {})
    return sw.WaterStream(
        name,
        temperature,
        pressure,
        sw.FrozenDict(components),
        toth,
        chemistry_policy=sw.FrozenDict(policy or {}),
        provenance=provenance() if with_provenance else (),
        aqueous_volume_flow_m3_s=flow,
    )


def cert(stream, *, engine="chem-fixture", ionic=0.01, density=1000.0):
    return sw.ChemistryCertificate(
        stream.state_hash,
        stream.fixed_charge_residual_eq_s,
        ionic,
        stream.solvent_water_kg_s_from_components,
        density,
        engine,
        density * stream.flow_m3_s,
    )


class SharedWaterStreamV06ChemistryIntegrationTests(unittest.TestCase):
    def test_version_and_root(self):
        self.assertEqual(sw.SCHEMA_VERSION, "0.6.0")
        self.assertEqual(sw.WaterStream.__module__, "shared_waterstream.v06")

    def test_aqueous_flow_is_authoritative_before_chemistry_certificate(self):
        stream = raw(flow=1.23456789012345)
        self.assertIsNone(stream.chemistry_certificate)
        self.assertEqual(stream.flow_m3_s, 1.23456789012345)
        self.assertEqual(stream.to_dict()["aqueous_volume_flow_m3_s"], 1.23456789012345)

    def test_aqueous_flow_required(self):
        components = {"h2o": 1000.0 / MW, "sodium": 1.0, "chloride": 1.0}
        with self.assertRaises(sw.WaterStreamError):
            sw.WaterStream("bad", 25.0, 2.0, sw.FrozenDict(components), 0.0)

    def test_non_aqueous_rejects_aqueous_flow(self):
        components = {"calcium": 1.0, "total_inorganic_carbon": 1.0}
        inventory = (
            sw.PhaseInventoryItem(sw.StreamPhase.SOLID, "calcite", sw.FrozenDict(components)),
        )
        with self.assertRaises(sw.WaterStreamError):
            sw.WaterStream(
                "solid", 60.0, 2.0, sw.FrozenDict(components), 0.0,
                sw.StreamPhase.SOLID, inventory,
                aqueous_volume_flow_m3_s=1.0,
            )

    def test_component_mg_l_conversion_is_exact_transport_arithmetic(self):
        stream = raw(flow=1.0, na=1.0, cl=0.0)
        self.assertEqual(stream.component_mg_l("sodium"), 22.989769)

    def test_direct_waterstate_mapping_has_only_non_speciating_bases(self):
        mapping = sw.WATERSTATE_DIRECT_COMPOSITION_MAP.to_dict()
        self.assertEqual(mapping["sodium"], "sodium")
        self.assertEqual(mapping["total_boron"], "boron")
        self.assertEqual(mapping["total_silica"], "silica")
        self.assertNotIn("total_inorganic_carbon", mapping)
        self.assertNotIn("total_ammonia", mapping)
        self.assertNotIn("total_phosphate", mapping)
        self.assertNotIn("bicarbonate", mapping)
        self.assertNotIn("carbonate", mapping)

    def test_toth_is_total_alkalinity_basis(self):
        stream = raw(water_kg_s=1000.0, toth=2.5)
        self.assertAlmostEqual(stream.total_alkalinity_mol_kg_water, 0.0025, places=15)
        report = stream.chemistry_handoff_report()
        self.assertIn("total_alkalinity", report["toth_definition"])
        self.assertEqual(report["toth_unit"], "eq/s")

    def test_ct_is_reconstructed_from_conserved_tic_and_h2o(self):
        stream = raw(water_kg_s=1000.0, tic=2.4)
        self.assertAlmostEqual(stream.total_inorganic_carbon_mol_kg_water, 0.0024, places=15)

    def test_waterstate_outbound_basis_is_ta_plus_ct_without_ph(self):
        stream = raw(water_kg_s=1000.0, tic=2.4, toth=2.1)
        self.assertAlmostEqual(stream.total_alkalinity_mol_kg_water, 0.0021, places=15)
        self.assertAlmostEqual(stream.total_inorganic_carbon_mol_kg_water, 0.0024, places=15)
        self.assertNotIn("ph", stream.to_dict())

    def test_ph_remains_forbidden(self):
        payload = raw().to_dict()
        payload["ph"] = 8.2
        with self.assertRaises(sw.WaterStreamError):
            sw.WaterStream.from_dict(payload)

    def test_derived_equilibrium_species_remain_forbidden_as_components(self):
        components = {"h2o": 1000.0 * 1000.0 / MW, "bicarbonate": 1.0}
        with self.assertRaises(sw.WaterStreamError):
            sw.WaterStream("bad", 25.0, 2.0, sw.FrozenDict(components), 0.0,
                           aqueous_volume_flow_m3_s=1.0)

    def test_chemistry_owned_analytical_families_are_exposed_not_silently_dropped(self):
        stream = raw(extra_components={"total_ammonia": 0.5, "total_phosphate": 0.2})
        report = stream.chemistry_handoff_report()
        self.assertEqual(tuple(report["chemistry_owned_analytical_families_present"]),
                         ("total_ammonia", "total_phosphate"))

    def test_production_handoff_requires_provenance(self):
        stream = raw(with_provenance=False)
        with self.assertRaises(sw.WaterStreamError):
            stream.chemistry_handoff_report()
        report = stream.chemistry_handoff_report(require_provenance=False)
        self.assertIsNone(report["source_application"])

    def test_provenance_maps_source_application_and_process(self):
        report = raw().chemistry_handoff_report()
        self.assertEqual(report["source_application"], "total-water-balance")
        self.assertEqual(report["source_process"], "unit-test")

    def test_state_hash_includes_aqueous_flow_basis(self):
        self.assertNotEqual(raw(flow=1.0).state_hash, raw(flow=1.000000000001).state_hash)

    def test_serialization_roundtrip_preserves_full_precision(self):
        stream = raw(flow=0.987654321012345, water_kg_s=987.654321012345,
                     na=1.23456789012345, cl=1.23456789012345,
                     tic=2.34567890123456, toth=2.22222222222222,
                     temperature=31.1234567890123, pressure=4.56789012345678,
                     policy={"gas_boundary": "closed", "future": {"redox": "fixed"}})
        payload = json.loads(sw.canonical_json(stream.to_dict()))
        restored = sw.WaterStream.from_dict(payload)
        self.assertEqual(restored.to_dict(), stream.to_dict())
        self.assertEqual(restored.state_hash, stream.state_hash)

    def test_waterstream_is_immutable(self):
        stream = raw()
        with self.assertRaises(FrozenInstanceError):
            stream.aqueous_volume_flow_m3_s = 2.0

    def test_mixer_needs_no_input_chemistry_certificate(self):
        a = raw("a", flow=0.4, water_kg_s=400.0, na=0.4, cl=0.4, tic=0.4, toth=0.8)
        b = raw("b", flow=0.6, water_kg_s=600.0, na=0.6, cl=0.6, tic=0.6, toth=1.2)
        mixed = sw.mix_water_streams([a, b], stream_id="m", source_application="total-water-balance")
        self.assertEqual(mixed.flow_m3_s, 1.0)
        self.assertEqual(mixed.component_totals_mol_s["h2o"], a.component_totals_mol_s["h2o"] + b.component_totals_mol_s["h2o"])
        self.assertEqual(mixed.component_totals_mol_s["total_inorganic_carbon"], 1.0)
        self.assertEqual(mixed.toth_eq_s, 2.0)
        self.assertIsNone(mixed.chemistry_certificate)

    def test_mixer_preserves_ta_and_ct_conserved_rates(self):
        a = raw("a", flow=0.25, water_kg_s=250.0, tic=0.5, toth=0.75)
        b = raw("b", flow=0.75, water_kg_s=750.0, tic=1.5, toth=2.25)
        mixed = sw.mix_water_streams([a, b], stream_id="m")
        self.assertEqual(mixed.toth_eq_s, 3.0)
        self.assertEqual(mixed.component_totals_mol_s["total_inorganic_carbon"], 2.0)
        self.assertAlmostEqual(mixed.total_alkalinity_mol_kg_water, 0.003, places=15)
        self.assertAlmostEqual(mixed.total_inorganic_carbon_mol_kg_water, 0.002, places=15)

    def test_mixing_commutative_for_authoritative_chemistry_basis(self):
        a = raw("a", flow=0.4, water_kg_s=400.0, na=2.0, cl=1.0, tic=0.3, toth=0.4)
        b = raw("b", flow=0.6, water_kg_s=600.0, na=3.0, cl=2.0, tic=0.7, toth=0.6)
        ab = sw.mix_water_streams([a, b], stream_id="m")
        ba = sw.mix_water_streams([b, a], stream_id="m")
        self.assertEqual(ab.component_totals_mol_s.to_dict(), ba.component_totals_mol_s.to_dict())
        self.assertAlmostEqual(ab.toth_eq_s, ba.toth_eq_s, places=15)
        self.assertAlmostEqual(ab.flow_m3_s, ba.flow_m3_s, places=15)
        self.assertAlmostEqual(ab.temperature_c, ba.temperature_c, places=15)

    def test_scalar_split_scales_flow_components_and_toth(self):
        stream = raw(flow=2.0, water_kg_s=2000.0, na=4.0, cl=4.0, tic=2.0, toth=6.0)
        daughters = sw.split_water_stream(stream, {"a": 0.25, "b": 0.75}, composition_preserving=True)
        self.assertEqual(daughters["a"].flow_m3_s, 0.5)
        self.assertEqual(daughters["a"].component_totals_mol_s["total_inorganic_carbon"], 0.5)
        self.assertEqual(daughters["a"].toth_eq_s, 1.5)
        self.assertAlmostEqual(daughters["a"].total_alkalinity_mol_kg_water,
                               stream.total_alkalinity_mol_kg_water, places=15)
        self.assertAlmostEqual(daughters["a"].total_inorganic_carbon_mol_kg_water,
                               stream.total_inorganic_carbon_mol_kg_water, places=15)

    def _selective_fractions(self):
        return {"a": {"h2o": 0.8, "sodium": 0.7, "chloride": 0.7},
                "b": {"h2o": 0.2, "sodium": 0.3, "chloride": 0.3}}

    def test_selective_aqueous_split_requires_explicit_daughter_flows(self):
        with self.assertRaises(sw.SelectiveSplitError):
            sw.split_water_stream(raw(toth=0.0), self._selective_fractions(), composition_preserving=False)

    def test_selective_aqueous_split_rejects_nonconserved_daughter_flows(self):
        with self.assertRaises(sw.SelectiveSplitError):
            sw.split_water_stream(raw(flow=1.0), self._selective_fractions(), composition_preserving=False,
                                  daughter_aqueous_volume_flow_m3_s={"a": 0.7, "b": 0.2})

    def test_selective_aqueous_split_with_zero_toth_uses_owner_flows(self):
        daughters = sw.split_water_stream(raw(flow=1.0), self._selective_fractions(), composition_preserving=False,
                                          daughter_aqueous_volume_flow_m3_s={"a": 0.8, "b": 0.2})
        self.assertEqual(daughters["a"].flow_m3_s, 0.8)
        self.assertEqual(daughters["b"].flow_m3_s, 0.2)
        self.assertIsNone(daughters["a"].chemistry_certificate)

    def test_selective_nonzero_total_alkalinity_refuses(self):
        with self.assertRaises(sw.SelectiveSplitError):
            sw.split_water_stream(raw(flow=1.0, toth=1.0), self._selective_fractions(), composition_preserving=False,
                                  daughter_aqueous_volume_flow_m3_s={"a": 0.8, "b": 0.2})

    def test_certificate_can_be_attached_after_first_solve(self):
        stream = raw(flow=1.25)
        certified = stream.with_chemistry_certificate(cert(stream, density=1015.0))
        self.assertEqual(certified.flow_m3_s, 1.25)
        self.assertEqual(certified.ionic_strength_mol_kg, 0.01)

    def test_stale_certificate_rejected(self):
        certificate = cert(raw(flow=1.0))
        with self.assertRaises(sw.ChemistryCertificateError):
            raw(flow=1.1).with_chemistry_certificate(certificate)

    def test_certificate_serialization_is_v06(self):
        certificate = cert(raw())
        self.assertEqual(certificate.to_dict()["version"], "0.6.0")
        self.assertEqual(sw.ChemistryCertificate.from_dict(certificate.to_dict()).to_dict(), certificate.to_dict())

    def test_cache_isolated_by_engine(self):
        class Issuer:
            declared_tolerance = 1e-12
            def __init__(self, version, ionic): self.engine_version=version; self.ionic=ionic; self.calls=0
            def issue(self, stream, *, warm_start=None):
                self.calls += 1
                return sw.ChemistryCertificate(stream.state_hash, stream.fixed_charge_residual_eq_s,
                    self.ionic, stream.solvent_water_kg_s_from_components, 1000.0,
                    self.engine_version, 1000.0 * stream.flow_m3_s)
        stream=raw(); cache=sw.ChemistryCertificateCache(); a=Issuer("A",1.0); b=Issuer("B",2.0)
        ca=sw.certify_stream(stream,a,cache=cache); cb=sw.certify_stream(stream,b,cache=cache)
        self.assertEqual((a.calls,b.calls),(1,1)); self.assertEqual(ca.ionic_strength_mol_kg,1.0); self.assertEqual(cb.ionic_strength_mol_kg,2.0)

    def test_real_v05_payload_migration_requires_explicit_nonzero_toth_confirmation(self):
        old_components={"h2o":999.0*1000.0/MW,"sodium":1.0,"chloride":1.0,"total_inorganic_carbon":2.0}
        payload=v05.WaterStream("old",25.0,2.0,v05.FrozenDict(old_components),2.5).to_dict()
        with self.assertRaises(sw.WaterStreamError): sw.migrate_v05_payload(payload,aqueous_volume_flow_m3_s=1.0)
        migrated=sw.migrate_v05_payload(payload,aqueous_volume_flow_m3_s=1.0,confirm_toth_is_total_alkalinity=True)
        self.assertEqual(migrated.toth_eq_s,2.5); self.assertEqual(migrated.flow_m3_s,1.0); self.assertIsNone(migrated.chemistry_certificate)

    def test_v05_zero_toth_payload_can_migrate_without_semantic_confirmation(self):
        old_components={"h2o":999.0*1000.0/MW,"sodium":1.0,"chloride":1.0}
        migrated=sw.migrate_v05_payload(v05.WaterStream("old",25.0,2.0,v05.FrozenDict(old_components),0.0).to_dict(),aqueous_volume_flow_m3_s=1.0)
        self.assertEqual(migrated.toth_eq_s,0.0)

    def test_v05_migration_can_recover_flow_from_legacy_certificate(self):
        old_components={"h2o":999.0*1000.0/MW,"sodium":1.0,"chloride":1.0}
        old=v05.WaterStream("old",25.0,2.0,v05.FrozenDict(old_components),0.0)
        old=old.with_chemistry_certificate(v05.ChemistryCertificate(old.state_hash,old.fixed_charge_residual_eq_s,0.01,
            old.solvent_water_kg_s_from_components,1000.0,"legacy",1000.0))
        migrated=sw.migrate_v05_payload(old.to_dict())
        self.assertEqual(migrated.flow_m3_s,1.0); self.assertIsNone(migrated.chemistry_certificate)
        self.assertTrue(any("Migrated from WaterStream v0.5" in w for w in migrated.diagnostics.warnings))

    def test_migration_preserves_unknown_fields(self):
        old_components={"h2o":999.0*1000.0/MW,"sodium":1.0,"chloride":1.0}
        payload=v05.WaterStream("old",25.0,2.0,v05.FrozenDict(old_components),0.0).to_dict(); payload["future_extension"]={"opaque":[1,2,3]}
        migrated=sw.migrate_v05_payload(payload,aqueous_volume_flow_m3_s=1.0)
        self.assertEqual(migrated.to_dict()["future_extension"],{"opaque":[1,2,3]})

    def test_h2o_carbon_and_toth_massledger_closure(self):
        feed=raw(flow=1.0,water_kg_s=1000.0,tic=2.0,toth=3.0)
        daughters=sw.split_water_stream(feed,{"a":0.4,"b":0.6},composition_preserving=True)
        ledger=sw.MassLedger.from_streams("l","split",[feed],list(daughters.values()))
        self.assertTrue(ledger.assert_closed()); self.assertEqual(ledger.toth_residual_eq_s,0.0)


if __name__ == "__main__":
    unittest.main()
