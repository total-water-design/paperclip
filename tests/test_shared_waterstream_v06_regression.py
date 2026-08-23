from __future__ import annotations

import json
import unittest
from dataclasses import replace

import shared_waterstream as sw

MW = sw.H2O_MOLAR_MASS_G_MOL


def raw(name="s", *, flow=1.0, water_kg_s=1000.0, na=1.0, cl=1.0,
        toth=0.0, temp=25.0, pressure=2.0, tracked=None, extensions=None,
        policy=None):
    components = {
        "h2o": water_kg_s * 1000.0 / MW,
        "sodium": na,
        "chloride": cl,
    }
    return sw.WaterStream(
        name, temp, pressure, sw.FrozenDict(components), toth,
        chemistry_policy=sw.FrozenDict(policy or {}),
        tracked_quantities=sw.FrozenDict({k: v.to_dict() for k, v in (tracked or {}).items()}),
        extensions=sw.FrozenDict({k: v.to_dict() for k, v in (extensions or {}).items()}),
        aqueous_volume_flow_m3_s=flow,
    )


def certificate(stream, *, engine="good", ionic=0.01, residual=None, density=1000.0):
    return sw.ChemistryCertificate(
        stream.state_hash,
        stream.fixed_charge_residual_eq_s if residual is None else residual,
        ionic,
        stream.solvent_water_kg_s_from_components,
        density,
        engine,
        density * stream.flow_m3_s,
    )


def certified(**kwargs):
    stream = raw(**kwargs)
    return stream.with_chemistry_certificate(certificate(stream))


class GoodIssuer:
    engine_version = "good"
    declared_tolerance = 1e-12
    def issue(self, stream, *, warm_start=None):
        return certificate(stream, engine=self.engine_version)


class ShiftedWarmIssuer(GoodIssuer):
    def issue(self, stream, *, warm_start=None):
        cert = certificate(stream, engine=self.engine_version)
        return cert if warm_start is None else replace(cert, ionic_strength_mol_kg=cert.ionic_strength_mol_kg + 2e-12)


class SharedWaterStreamV06RegressionTests(unittest.TestCase):
    def test_raw_analysis_subschema_roundtrip_remains_supported(self):
        analysis = sw.RawWaterAnalysis(
            "lab",
            (sw.RawMeasurement("m", "Na", 100.0, "mg/L"),),
            3.7,
            0.12,
            sw.ReconciliationDecision("adjusted", "chloride"),
        )
        payload = analysis.to_dict()
        self.assertEqual(sw.RawWaterAnalysis.from_dict(payload).to_dict(), payload)
        self.assertEqual(payload["version"], sw.RAW_ANALYSIS_SCHEMA_VERSION)

    def test_charge_policy_uses_absolute_plus_relative_throughput(self):
        # The certificate residual must match the stream's independently
        # recomputable charge. Put the 2e-9 eq/s imbalance in the analytical
        # totals rather than lying in the certificate fixture.
        stream = raw(na=8.0 + 2e-9, cl=8.0)
        stream = stream.with_chemistry_certificate(certificate(stream))
        self.assertAlmostEqual(stream.fixed_charge_residual_eq_s, 2e-9, places=15)
        tolerance = sw.ChargeValidationPolicy(1e-9, 1e-8).validate(stream)
        self.assertGreaterEqual(tolerance, 1.6e-7)

    def test_na8_cl7_false_zero_residual_is_rejected(self):
        stream = raw(na=8.0, cl=7.0)
        with self.assertRaises(sw.ChemistryCertificateError):
            stream.with_chemistry_certificate(certificate(stream, residual=0.0))

    def test_high_i_certificate_exposes_derived_chemistry_without_owning_it(self):
        stream = raw(na=8.0, cl=8.0)
        stream = stream.with_chemistry_certificate(certificate(stream, ionic=8.0, density=1250.0))
        self.assertEqual(stream.ionic_strength_mol_kg, 8.0)
        self.assertEqual(stream.flow_m3_s, 1.0)
        self.assertEqual(stream.chemistry_certificate.engine_version, "good")

    def test_chemistry_policy_participates_in_hash_and_mismatch_refuses_mix(self):
        a = raw("a", policy={"gas_boundary": "closed"})
        b = raw("b", policy={"gas_boundary": "open"})
        self.assertNotEqual(a.state_hash, b.state_hash)
        with self.assertRaises(sw.WaterStreamError):
            sw.mix_water_streams([a, b], stream_id="m")

    def test_phase_inventory_over_and_under_claims_refused(self):
        aqueous = {"h2o": 1000.0, "sodium": 1.0, "chloride": 1.0}
        total = {**aqueous, "calcium": 1.0, "total_inorganic_carbon": 1.0}
        for calcium in (2.0, 0.5):
            inventory = (
                sw.PhaseInventoryItem(sw.StreamPhase.AQUEOUS, None, sw.FrozenDict(aqueous)),
                sw.PhaseInventoryItem(
                    sw.StreamPhase.SOLID, "calcite",
                    sw.FrozenDict({"calcium": calcium, "total_inorganic_carbon": 1.0}),
                ),
            )
            with self.assertRaises(sw.WaterStreamError):
                sw.WaterStream("bad", 60.0, 2.0, sw.FrozenDict(total), 0.0,
                               sw.StreamPhase.MIXED, inventory)

    def test_solid_and_gas_flow_are_explicitly_unavailable(self):
        solid_comp = {"calcium": 1.0, "total_inorganic_carbon": 1.0}
        solid = sw.WaterStream(
            "solid", 60.0, 2.0, sw.FrozenDict(solid_comp), 0.0,
            sw.StreamPhase.SOLID,
            (sw.PhaseInventoryItem(sw.StreamPhase.SOLID, "calcite", sw.FrozenDict(solid_comp)),),
        )
        with self.assertRaises(sw.NonVolumetricFlowError):
            _ = solid.flow_m3_s
        gas_comp = {"total_inorganic_carbon": 1.0}
        gas = sw.WaterStream(
            "gas", 30.0, 1.0, sw.FrozenDict(gas_comp), 0.0,
            sw.StreamPhase.GAS,
            (sw.PhaseInventoryItem(sw.StreamPhase.GAS, "CO2-rich gas", sw.FrozenDict(gas_comp)),),
        )
        with self.assertRaises(sw.NonVolumetricFlowError):
            _ = gas.flow_m3_s

    def test_mixed_phase_temperature_requires_owner_value(self):
        solid_comp = {"calcium": 1.0, "total_inorganic_carbon": 1.0}
        solid = sw.WaterStream(
            "solid", 90.0, 2.0, sw.FrozenDict(solid_comp), 0.0,
            sw.StreamPhase.SOLID,
            (sw.PhaseInventoryItem(sw.StreamPhase.SOLID, "calcite", sw.FrozenDict(solid_comp)),),
        )
        with self.assertRaises(sw.MixedPhaseThermalError):
            sw.mix_water_streams([raw(), solid], stream_id="m")
        mixed = sw.mix_water_streams([raw(), solid], stream_id="m", output_temperature_c=55.0)
        self.assertEqual(mixed.temperature_c, 55.0)
        self.assertIn("calcite", {item.identity for item in mixed.phase_inventory})

    def test_shared_component_phase_selective_split_refuses(self):
        aqueous = {"h2o": 1000.0, "sodium": 1.0, "chloride": 1.0}
        calcite = {"calcium": 0.5, "total_inorganic_carbon": 0.5}
        gypsum = {"calcium": 0.5, "sulfate": 0.5}
        total = {**aqueous, "calcium": 1.0, "total_inorganic_carbon": 0.5, "sulfate": 0.5}
        stream = sw.WaterStream(
            "mixed", 60.0, 2.0, sw.FrozenDict(total), 0.0,
            sw.StreamPhase.MIXED,
            (
                sw.PhaseInventoryItem(sw.StreamPhase.AQUEOUS, None, sw.FrozenDict(aqueous)),
                sw.PhaseInventoryItem(sw.StreamPhase.SOLID, "calcite", sw.FrozenDict(calcite)),
                sw.PhaseInventoryItem(sw.StreamPhase.SOLID, "gypsum", sw.FrozenDict(gypsum)),
            ),
        )
        fractions = {
            "light": {"h2o": 0.9, "sodium": 0.9, "chloride": 0.9, "calcium": 0.2,
                      "total_inorganic_carbon": 0.1, "sulfate": 0.9},
            "heavy": {"h2o": 0.1, "sodium": 0.1, "chloride": 0.1, "calcium": 0.8,
                      "total_inorganic_carbon": 0.9, "sulfate": 0.1},
        }
        with self.assertRaises(sw.SelectiveSplitError):
            sw.split_water_stream(stream, fractions, composition_preserving=False)

    def test_sdi_not_mixable_becomes_unavailable(self):
        q1 = sw.TrackedQuantity(2.0, "index", "sdi", sw.MixingRule.NOT_MIXABLE)
        q2 = sw.TrackedQuantity(5.0, "index", "sdi", sw.MixingRule.NOT_MIXABLE)
        mixed = sw.mix_water_streams(
            [raw("a", tracked={"sdi": q1}), raw("b", tracked={"sdi": q2})], stream_id="m"
        )
        sdi = mixed.tracked("sdi")
        self.assertFalse(sdi.available)
        self.assertIsNone(sdi.value)

    def test_undefined_outside_mixer_becomes_unavailable_on_split(self):
        quantity = sw.TrackedQuantity(
            10.0, "mg/L", "cod", sw.MixingRule.FLOW_WEIGHTED,
            sw.TrackedTransportPolicy.UNDEFINED_OUTSIDE_MIXER,
        )
        daughter = sw.split_water_stream(
            raw(tracked={"cod": quantity}), {"a": 1.0}, composition_preserving=True
        )["a"]
        self.assertFalse(daughter.tracked("cod").available)

    def test_owner_extension_split_fails_closed(self):
        extension = sw.ExtensionState(
            sw.ExtensionSpec("bio:asm", "total-bio-design",
                             sw.ExtensionTransportPolicy.OWNER_MUST_TRANSFORM),
            sw.FrozenDict({"x": 1}),
        )
        with self.assertRaises(sw.ExtensionTransportError):
            sw.split_water_stream(raw(extensions={"bio:asm": extension}),
                                  {"a": 0.5, "b": 0.5}, composition_preserving=True)

    def test_double_counted_explicit_solid_outlet_refused(self):
        entry = sw.MassLedgerEntry(
            "calcium", component_in_kg_s=1.0, component_out_kg_s=1.0,
            transferred_to_solid_kg_s=0.1, explicit_solid_outlet=True,
        )
        with self.assertRaises(sw.LedgerConventionError):
            entry.assert_convention()

    def test_good_issuer_conforms(self):
        result = sw.assert_issuer_conformant(GoodIssuer())
        self.assertTrue(result["cold_warm_equivalent"])
        self.assertTrue(result["deterministic_identical_inputs"])

    def test_warm_start_shift_above_tolerance_fails(self):
        with self.assertRaises(AssertionError):
            sw.assert_issuer_conformant(ShiftedWarmIssuer())

    def test_issuer_engine_mismatch_fails(self):
        class BadIssuer(GoodIssuer):
            engine_version = "declared-A"
            def issue(self, stream, *, warm_start=None):
                return certificate(stream, engine="certificate-B")
        with self.assertRaises(AssertionError):
            sw.assert_issuer_conformant(BadIssuer())
        with self.assertRaises(sw.ChemistryCertificateError):
            sw.certify_stream(raw(), BadIssuer())

    def test_mixing_associativity_for_authoritative_extensives(self):
        a = raw("a", flow=0.2, water_kg_s=200.0, na=0.2, cl=0.2, toth=0.2)
        b = raw("b", flow=0.3, water_kg_s=300.0, na=0.3, cl=0.3, toth=0.3)
        c = raw("c", flow=0.5, water_kg_s=500.0, na=0.5, cl=0.5, toth=0.5)
        left = sw.mix_water_streams([sw.mix_water_streams([a, b], stream_id="ab"), c], stream_id="left")
        right = sw.mix_water_streams([a, sw.mix_water_streams([b, c], stream_id="bc")], stream_id="right")
        self.assertEqual(left.component_totals_mol_s.to_dict(), right.component_totals_mol_s.to_dict())
        self.assertAlmostEqual(left.toth_eq_s, right.toth_eq_s, places=15)
        self.assertAlmostEqual(left.flow_m3_s, right.flow_m3_s, places=15)

    def test_idempotent_one_split_and_reserialize(self):
        stream = raw(policy={"gas_boundary": "closed"})
        daughter = sw.split_water_stream(stream, {"same": 1.0}, composition_preserving=True)["same"]
        self.assertEqual(daughter.component_totals_mol_s, stream.component_totals_mol_s)
        self.assertEqual(daughter.toth_eq_s, stream.toth_eq_s)
        self.assertEqual(daughter.flow_m3_s, stream.flow_m3_s)
        self.assertEqual(daughter.temperature_c, stream.temperature_c)
        self.assertEqual(daughter.pressure_bar, stream.pressure_bar)
        restored = sw.WaterStream.from_dict(json.loads(sw.canonical_json(stream.to_dict())))
        self.assertEqual(restored.to_dict(), stream.to_dict())

    def test_scalar_split_rebinds_certificate_only_when_preserving(self):
        stream = certified()
        yes = sw.split_water_stream(stream, {"a": 0.7, "b": 0.3}, composition_preserving=True)
        no = sw.split_water_stream(stream, {"a": 0.7, "b": 0.3}, composition_preserving=False)
        self.assertIsNotNone(yes["a"].chemistry_certificate)
        self.assertIsNone(no["a"].chemistry_certificate)

    def test_unitop_conformance_positive_adapter(self):
        class Good:
            def solve(self, feed, *, tracked_transformers=None, extension_transformers=None):
                for key in feed.tracked_quantities:
                    q = feed.tracked(key)
                    if q.transport_policy is sw.TrackedTransportPolicy.OWNER_MUST_TRANSFORM:
                        raise sw.TrackedQuantityTransportError("owner required")
                for ns in feed.extensions:
                    if feed.extension(ns).spec.policy_for("unitop") is sw.ExtensionTransportPolicy.OWNER_MUST_TRANSFORM:
                        raise sw.ExtensionTransportError("owner required")
                out = replace(feed, stream_id="out", chemistry_certificate=None)
                return sw.UnitOpConformanceResult(
                    {"out": out}, sw.MassLedger.from_streams("l", "good", [feed], [out]), 0.0
                )
            def solve_selective_split(self, feed, fractions, *, composition_preserving,
                                      daughter_aqueous_volume_flow_m3_s):
                daughters = sw.split_water_stream(
                    feed, fractions, composition_preserving=composition_preserving,
                    daughter_aqueous_volume_flow_m3_s=daughter_aqueous_volume_flow_m3_s,
                )
                return sw.UnitOpConformanceResult(
                    daughters, sw.MassLedger.from_streams("s", "split", [feed], list(daughters.values())), 0.0
                )
        self.assertTrue(all(sw.assert_unitop_fail_closed(Good()).values()))

    def test_unitop_conformance_rejects_h2o_loss_only(self):
        class Bad:
            def solve(self, feed, *, tracked_transformers=None, extension_transformers=None):
                for key in feed.tracked_quantities:
                    if feed.tracked(key).transport_policy is sw.TrackedTransportPolicy.OWNER_MUST_TRANSFORM:
                        raise sw.TrackedQuantityTransportError("owner required")
                for ns in feed.extensions:
                    if feed.extension(ns).spec.policy_for("unitop") is sw.ExtensionTransportPolicy.OWNER_MUST_TRANSFORM:
                        raise sw.ExtensionTransportError("owner required")
                components = feed.component_totals_mol_s.to_dict(); components["h2o"] *= 0.9
                out = sw.WaterStream("out", feed.temperature_c, feed.pressure_bar,
                                     sw.FrozenDict(components), feed.toth_eq_s,
                                     tracked_quantities=feed.tracked_quantities,
                                     aqueous_volume_flow_m3_s=feed.flow_m3_s)
                return sw.UnitOpConformanceResult(
                    {"out": out}, sw.MassLedger.from_streams("reported", "reported", [feed], [feed]), 0.0
                )
            def solve_selective_split(self, feed, fractions, *, composition_preserving,
                                      daughter_aqueous_volume_flow_m3_s):
                daughters = sw.split_water_stream(
                    feed, fractions, composition_preserving=composition_preserving,
                    daughter_aqueous_volume_flow_m3_s=daughter_aqueous_volume_flow_m3_s,
                )
                return sw.UnitOpConformanceResult(
                    daughters, sw.MassLedger.from_streams("s", "s", [feed], list(daughters.values())), 0.0
                )
        with self.assertRaises(sw.MassLedgerClosureError) as caught:
            sw.assert_unitop_fail_closed(Bad())
        self.assertIn("h2o", str(caught.exception))

    def test_unitop_conformance_rejects_toth_drift_only(self):
        class Bad:
            def solve(self, feed, *, tracked_transformers=None, extension_transformers=None):
                for key in feed.tracked_quantities:
                    if feed.tracked(key).transport_policy is sw.TrackedTransportPolicy.OWNER_MUST_TRANSFORM:
                        raise sw.TrackedQuantityTransportError("owner required")
                for ns in feed.extensions:
                    if feed.extension(ns).spec.policy_for("unitop") is sw.ExtensionTransportPolicy.OWNER_MUST_TRANSFORM:
                        raise sw.ExtensionTransportError("owner required")
                out = replace(feed, stream_id="out", toth_eq_s=feed.toth_eq_s + 0.25,
                              chemistry_certificate=None)
                return sw.UnitOpConformanceResult(
                    {"out": out}, sw.MassLedger.from_streams("reported", "reported", [feed], [feed]), 0.0
                )
            def solve_selective_split(self, feed, fractions, *, composition_preserving,
                                      daughter_aqueous_volume_flow_m3_s):
                daughters = sw.split_water_stream(
                    feed, fractions, composition_preserving=composition_preserving,
                    daughter_aqueous_volume_flow_m3_s=daughter_aqueous_volume_flow_m3_s,
                )
                return sw.UnitOpConformanceResult(
                    daughters, sw.MassLedger.from_streams("s", "s", [feed], list(daughters.values())), 0.0
                )
        with self.assertRaises(sw.MassLedgerClosureError) as caught:
            sw.assert_unitop_fail_closed(Bad())
        self.assertIn("TOTH residual", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
