from __future__ import annotations
from dataclasses import FrozenInstanceError
import unittest
import shared_waterstream as sw
MW = sw.H2O_MOLAR_MASS_G_MOL

def solution_mass(stream):
    total=0.0
    for key, amount in stream.component_totals_mol_s.items():
        d=sw.DEFAULT_COMPONENT_REGISTRY.get(key)
        if d.molar_mass_g_mol is not None: total+=float(amount)*d.molar_mass_g_mol/1000.0
    return total

def ionic_strength(stream):
    water=stream.solvent_water_kg_s_from_components
    if water<=0:return 0.0
    q2=sum((sw.DEFAULT_COMPONENT_REGISTRY.get(k).charge or 0)**2*float(v) for k,v in stream.component_totals_mol_s.items())
    return 0.5*q2/water

def raw(name="s",*,water_kg_s=1000.0,na=1.0,cl=1.0,temp=25.0,pressure=2.0,toth=0.0,tracked=None,extensions=None):
    components={"h2o":water_kg_s*1000.0/MW,"sodium":na,"chloride":cl}
    return sw.WaterStream(name,temp,pressure,sw.FrozenDict(components),toth,
        tracked_quantities=sw.FrozenDict({k:v.to_dict() for k,v in (tracked or {}).items()}),
        extensions=sw.FrozenDict({k:v.to_dict() for k,v in (extensions or {}).items()}))

def certificate(stream,*,ionic=None,density=1000.0,solution_mass_kg_s=None,residual=None,engine="v04-audit"):
    return sw.ChemistryCertificate(stream.state_hash,stream.fixed_charge_residual_eq_s if residual is None else residual,
        ionic_strength(stream) if ionic is None else ionic,stream.solvent_water_kg_s_from_components,density,engine,
        solution_mass(stream) if solution_mass_kg_s is None else solution_mass_kg_s)

def certified(**kwargs):
    s=raw(**kwargs); return s.with_chemistry_certificate(certificate(s))

def calcite_solid(name="solid",*,ca=0.4,tic=0.4,temp=90.0):
    c={"calcium":ca,"total_inorganic_carbon":tic}; inv=(sw.PhaseInventoryItem(sw.StreamPhase.SOLID,"calcite",sw.FrozenDict(c)),)
    return sw.WaterStream(name,temp,2.0,sw.FrozenDict(c),0.0,sw.StreamPhase.SOLID,inv)

def mixed_calcite(name="mixed",*,certified_state=False):
    aq={"h2o":1000.0,"sodium":1.0,"chloride":1.0}; sol={"calcium":10.0,"total_inorganic_carbon":10.0}; total={**aq,**sol}
    inv=(sw.PhaseInventoryItem(sw.StreamPhase.AQUEOUS,None,sw.FrozenDict(aq)),sw.PhaseInventoryItem(sw.StreamPhase.SOLID,"calcite",sw.FrozenDict(sol)))
    s=sw.WaterStream(name,60.0,2.0,sw.FrozenDict(total),0.0,sw.StreamPhase.MIXED,inv)
    return s.with_chemistry_certificate(certificate(s,density=1150.0)) if certified_state else s

class SharedWaterStreamV04HistoricalInvariantPorts(unittest.TestCase):
    def test_aqueous_requires_h2o_component(self):
        with self.assertRaises(sw.WaterStreamError): sw.WaterStream("bad",25.0,1.0,sw.FrozenDict({"sodium":1.0,"chloride":1.0}),0.0)
    def test_ph_still_cannot_be_transported(self):
        p=raw().to_dict(); p["ph"]=7.0
        with self.assertRaises(sw.WaterStreamError): sw.WaterStream.from_dict(p)
    def test_waterstream_remains_immutable(self):
        s=raw()
        with self.assertRaises(FrozenInstanceError): s.temperature_c=30.0
    def test_charge_tolerance_removed_from_stream(self):
        s=raw(); self.assertFalse(hasattr(s,"charge_tolerance_eq_s")); p=s.to_dict(); p["charge_tolerance_eq_s"]=1e-9
        with self.assertRaises(sw.WaterStreamError): sw.WaterStream.from_dict(p)
    def test_charge_policy_uses_abs_plus_relative_throughput(self):
        s=raw(na=8.0,cl=8.0); s=s.with_chemistry_certificate(certificate(s)); tol=sw.ChargeValidationPolicy(1e-9,1e-8).validate(s); self.assertGreaterEqual(tol,1.6e-7)
    def test_na8_cl7_with_certified_residual_zero_fails(self):
        s=raw(na=8.0,cl=7.0)
        with self.assertRaises(sw.WaterStreamError): s.with_chemistry_certificate(certificate(s,residual=0.0))
    def test_certificate_carries_high_i_density_and_solvent_water(self):
        s=raw(water_kg_s=999.0,na=8.0,cl=8.0); s=s.with_chemistry_certificate(certificate(s,ionic=8.0,density=1250.0,solution_mass_kg_s=1250.0)); self.assertEqual(s.ionic_strength_mol_kg,8.0); self.assertAlmostEqual(s.flow_m3_s,1.0); self.assertAlmostEqual(s.chemistry_certificate.solvent_water_kg_s,999.0)
    def test_mixing_explicitly_invalidates_certificate(self):
        m=sw.mix_water_streams([certified(name="a"),certified(name="b")],stream_id="m"); self.assertIsNone(m.chemistry_certificate); self.assertTrue(any("invalidated" in w for w in m.diagnostics.warnings));
        with self.assertRaises(sw.UncertifiedChemistryError): _=m.flow_m3_s
    def test_tracked_undefined_outside_mixer_becomes_unavailable(self):
        q=sw.TrackedQuantity(10.0,"mg/L","mass_concentration",sw.MixingRule.FLOW_WEIGHTED,sw.TrackedTransportPolicy.UNDEFINED_OUTSIDE_MIXER); d=sw.split_water_stream(raw(tracked={"cod":q}),{"a":1.0},composition_preserving=True)["a"]; self.assertFalse(d.tracked("cod").available)
    def test_raw_analytical_charge_imbalance_preserved(self):
        a=sw.RawWaterAnalysis("lab",(sw.RawMeasurement("m","Na",100.0,"mg/L"),),3.7,0.12,sw.ReconciliationDecision("adjusted","chloride")); p=a.to_dict(); self.assertEqual(a.analytical_charge_imbalance_pct,3.7); self.assertEqual(a.analytical_charge_residual_meq_l,0.12); self.assertEqual(p["analytical_charge_imbalance_pct"],3.7); self.assertEqual(p["analytical_charge_residual_meq_l"],0.12)
    def test_solid_and_gas_flow_explicitly_unavailable(self):
        with self.assertRaises(sw.NonVolumetricFlowError): _=calcite_solid().flow_m3_s
        gc={"total_inorganic_carbon":1.0}; g=sw.WaterStream("gas",30.0,1.0,sw.FrozenDict(gc),0.0,sw.StreamPhase.GAS,(sw.PhaseInventoryItem(sw.StreamPhase.GAS,"CO2-rich gas",sw.FrozenDict(gc)),))
        with self.assertRaises(sw.NonVolumetricFlowError): _=g.flow_m3_s
    def test_mixed_phase_temperature_refuses_without_owner_value(self):
        with self.assertRaises(sw.MixedPhaseThermalError): sw.mix_water_streams([certified(),calcite_solid()],stream_id="mix")
    def test_solid_calcite_plus_aqueous_preserves_identity(self):
        m=sw.mix_water_streams([certified(),calcite_solid()],stream_id="mix",output_temperature_c=55.0); self.assertEqual(m.phase,sw.StreamPhase.MIXED); self.assertIn("calcite",{x.identity for x in m.phase_inventory}); self.assertIsNone(m.chemistry_certificate)
    def test_composition_preserving_flag_required(self):
        with self.assertRaises(TypeError): sw.split_water_stream(certified(),{"a":0.5,"b":0.5})
    def test_uniform_aqueous_rebind_only_explicit_preserving(self):
        s=certified(); yes=sw.split_water_stream(s,{"a":0.7,"b":0.3},composition_preserving=True); no=sw.split_water_stream(s,{"a":0.7,"b":0.3},composition_preserving=False); self.assertIsNotNone(yes["a"].chemistry_certificate); self.assertIsNone(no["a"].chemistry_certificate)
    def test_selective_mixed_80_water_20_ca_invalidates_and_partitions(self):
        s=mixed_calcite(certified_state=True); f={"light":{"h2o":0.8,"sodium":0.8,"chloride":0.8,"calcium":0.2,"total_inorganic_carbon":0.2},"heavy":{"h2o":0.2,"sodium":0.2,"chloride":0.2,"calcium":0.8,"total_inorganic_carbon":0.8}}; l=sw.split_water_stream(s,f,composition_preserving=False)["light"]; self.assertIsNone(l.chemistry_certificate); self.assertAlmostEqual(l.component_totals_mol_s["h2o"],800.0); self.assertAlmostEqual(l.component_totals_mol_s["calcium"],2.0)
    def test_selective_never_rebinds_even_if_flag_true(self):
        s=mixed_calcite(certified_state=True); f={"light":{"h2o":0.8,"sodium":0.8,"chloride":0.8,"calcium":0.2,"total_inorganic_carbon":0.2},"heavy":{"h2o":0.2,"sodium":0.2,"chloride":0.2,"calcium":0.8,"total_inorganic_carbon":0.8}}; self.assertIsNone(sw.split_water_stream(s,f,composition_preserving=True)["light"].chemistry_certificate)
    def test_mixed_uniform_split_does_not_rebind(self): self.assertIsNone(sw.split_water_stream(mixed_calcite(certified_state=True),{"a":0.7,"b":0.3},composition_preserving=True)["a"].chemistry_certificate)
    def test_sdi_not_mixable_is_unavailable_not_averaged(self):
        q1=sw.TrackedQuantity(2.0,"index","sdi",sw.MixingRule.NOT_MIXABLE); q2=sw.TrackedQuantity(5.0,"index","sdi",sw.MixingRule.NOT_MIXABLE); sdi=sw.mix_water_streams([certified(name="a",tracked={"sdi":q1}),certified(name="b",tracked={"sdi":q2})],stream_id="m").tracked("sdi"); self.assertFalse(sdi.available); self.assertIsNone(sdi.value); self.assertIn("NOT_MIXABLE",sdi.diagnostic_reason)
    def test_owner_extension_split_fails_closed(self):
        e=sw.ExtensionState(sw.ExtensionSpec("bio:asm","total-bio-design",sw.ExtensionTransportPolicy.OWNER_MUST_TRANSFORM),sw.FrozenDict({"x":1.0})); s=raw(extensions={"bio:asm":e})
        with self.assertRaises(sw.ExtensionTransportError): sw.split_water_stream(s,{"a":0.5,"b":0.5},composition_preserving=True)
    def test_certificate_cache_state_hash_and_warm_start(self):
        class Issuer:
            engine_version="audit-issuer"; declared_tolerance=1e-12
            def __init__(self):self.calls=0;self.warm=[]
            def issue(self,stream,*,warm_start=None):self.calls+=1;self.warm.append(warm_start);return certificate(stream,engine=self.engine_version)
        issuer=Issuer(); cache=sw.ChemistryCertificateCache(); first=sw.certify_stream(raw(name="s1"),issuer,cache=cache); second=sw.certify_stream(raw(name="s2"),issuer,cache=cache,warm_start=first.chemistry_certificate); self.assertEqual(issuer.calls,1); self.assertEqual(first.state_hash,second.state_hash); sw.certify_stream(raw(name="s3",temp=26.0),issuer,cache=cache,warm_start=first.chemistry_certificate); self.assertEqual(issuer.calls,2); self.assertIs(issuer.warm[-1],first.chemistry_certificate)

if __name__=="__main__":unittest.main()
