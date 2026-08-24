from __future__ import annotations
from dataclasses import dataclass, replace
import json
import unittest
import shared_waterstream as sw

MW=sw.H2O_MOLAR_MASS_G_MOL

def solution_mass(s):
    total=0.0
    for k,n in s.component_totals_mol_s.items():
        d=sw.DEFAULT_COMPONENT_REGISTRY.get(k)
        if d.molar_mass_g_mol is not None: total+=float(n)*d.molar_mass_g_mol/1000.0
    return total

def I(s):
    w=s.solvent_water_kg_s_from_components
    return 0 if w<=0 else .5*sum((sw.DEFAULT_COMPONENT_REGISTRY.get(k).charge or 0)**2*float(n) for k,n in s.component_totals_mol_s.items())/w

def raw(name='s',water_kg_s=1000,na=1,cl=1,*,toth=0,temp=25,pressure=2,policy=None,tracked=None,extensions=None,tic=0):
    c={'h2o':water_kg_s*1000/MW,'sodium':na,'chloride':cl}
    if tic:c['total_inorganic_carbon']=tic
    return sw.WaterStream(name,temp,pressure,sw.FrozenDict(c),toth,chemistry_policy=sw.FrozenDict(policy or {}),tracked_quantities=sw.FrozenDict({k:v.to_dict() for k,v in (tracked or {}).items()}),extensions=sw.FrozenDict({k:v.to_dict() for k,v in (extensions or {}).items()}))

def cert(s,*,ionic=None,density=1000,sm=None,engine='audit',residual=None,water=None):
    return sw.ChemistryCertificate(s.state_hash,s.fixed_charge_residual_eq_s if residual is None else residual,I(s) if ionic is None else ionic,s.solvent_water_kg_s_from_components if water is None else water,density,engine,solution_mass(s) if sm is None else sm)

def certified(**kw):
    s=raw(**kw); return s.with_chemistry_certificate(cert(s))

class GoodIssuer:
    engine_version='good-v1'; declared_tolerance=1e-12
    def issue(self,stream,*,warm_start=None):return cert(stream,engine=self.engine_version)

class WrongStableIssuer:
    engine_version='wrong-stable'; declared_tolerance=1e-12
    def issue(self,stream,*,warm_start=None):return cert(stream,ionic=123.456,density=777,sm=5000,engine=self.engine_version)

class ShiftedWarmIssuer(GoodIssuer):
    def issue(self,stream,*,warm_start=None):
        c=cert(stream,engine=self.engine_version)
        return c if warm_start is None else replace(c,ionic_strength_mol_kg=c.ionic_strength_mol_kg+2e-12)

class V05Audit(unittest.TestCase):
    def test_version_and_single_current_module(self):
        self.assertEqual(sw.SCHEMA_VERSION,'0.5.0')
        self.assertEqual(sw.WaterStream.__module__,'shared_waterstream.v05')
        self.assertEqual(sw.FrozenDict.__module__,'shared_waterstream.v05')
        self.assertEqual(sw.RawWaterAnalysis.__module__,'shared_waterstream.v05')
        self.assertEqual(sw.MassLedger.__module__,'shared_waterstream.v05')
        self.assertEqual(sw.assert_unitop_fail_closed.__module__,'shared_waterstream.v05')

    def test_roundtrip_lossless_unknown_and_policy(self):
        s=certified(policy={'gas_boundary':'closed','future':{'redox':'A'}})
        p=s.to_dict(); p['future_top']={'x':[1,2,3]}
        r=sw.WaterStream.from_dict(json.loads(sw.canonical_json(p)))
        self.assertEqual(r.to_dict(),p); self.assertEqual(r.state_hash,s.state_hash)

    def test_raw_analysis_roundtrip(self):
        a=sw.RawWaterAnalysis('lab',(sw.RawMeasurement('m','Na',100,'mg/L'),),3.7,.12,sw.ReconciliationDecision('adjusted','chloride'))
        r=sw.RawWaterAnalysis.from_dict(a.to_dict()); self.assertEqual(r.to_dict(),a.to_dict())

    def test_attachment_rejects_stale_charge_and_water(self):
        s=raw()
        with self.assertRaises(sw.ChemistryCertificateError):s.with_chemistry_certificate(cert(s,residual=1))
        bad=cert(s,water=s.solvent_water_kg_s_from_components+.1,sm=solution_mass(s)+1)
        with self.assertRaises(sw.ChemistryCertificateError):s.with_chemistry_certificate(bad)

    def test_attachment_trust_boundary_is_explicit(self):
        s=raw(); c=cert(s,ionic=123.456,density=777,sm=5000)
        accepted=s.with_chemistry_certificate(c)
        self.assertEqual(accepted.ionic_strength_mol_kg,123.456)
        result=sw.assert_issuer_conformant(WrongStableIssuer())
        self.assertEqual(result['trusted_not_independently_verified'],('ionic_strength_mol_kg','density_kg_m3','solution_mass_kg_s'))

    def test_empty_engine_version_rejected(self):
        s=raw()
        with self.assertRaises(sw.ChemistryCertificateError):sw.ChemistryCertificate(s.state_hash,0,I(s),s.solvent_water_kg_s_from_components,1000,'',solution_mass(s))

    def test_issuer_warm_shift_fails(self):
        with self.assertRaises(AssertionError):sw.assert_issuer_conformant(ShiftedWarmIssuer())

    def test_issuer_engine_mismatch_fails(self):
        class Bad(GoodIssuer):
            engine_version='declared-A'
            def issue(self,stream,*,warm_start=None):return cert(stream,engine='certificate-B')
        with self.assertRaises(AssertionError):sw.assert_issuer_conformant(Bad())
        with self.assertRaises(sw.ChemistryCertificateError):sw.certify_stream(raw(),Bad())

    def test_cache_isolated_by_engine_version(self):
        class Issuer:
            declared_tolerance=1e-12
            def __init__(self,version,ionic):self.engine_version=version;self.ionic=ionic;self.calls=0
            def issue(self,stream,*,warm_start=None):self.calls+=1;return cert(stream,ionic=self.ionic,engine=self.engine_version)
        s=raw(); a=Issuer('A',1); b=Issuer('B',2); cache=sw.ChemistryCertificateCache()
        ca=sw.certify_stream(s,a,cache=cache); cb=sw.certify_stream(s,b,cache=cache)
        self.assertEqual(a.calls,1); self.assertEqual(b.calls,1); self.assertEqual(ca.chemistry_certificate.engine_version,'A'); self.assertEqual(cb.chemistry_certificate.engine_version,'B'); self.assertEqual(cb.ionic_strength_mol_kg,2)

    def test_policy_hash_and_mismatch_refuse(self):
        a=certified(name='a',policy={'gas_boundary':'closed'}); b=certified(name='b',policy={'gas_boundary':'open'})
        self.assertNotEqual(a.state_hash,b.state_hash)
        with self.assertRaises(sw.WaterStreamError):sw.mix_water_streams([a,b],stream_id='m')

    def test_phase_inventory_over_under_refused(self):
        aq={'h2o':1000,'sodium':1,'chloride':1}; total={**aq,'calcium':1,'total_inorganic_carbon':1}
        for ca in (2,.5):
            inv=(sw.PhaseInventoryItem(sw.StreamPhase.AQUEOUS,None,sw.FrozenDict(aq)),sw.PhaseInventoryItem(sw.StreamPhase.SOLID,'calcite',sw.FrozenDict({'calcium':ca,'total_inorganic_carbon':1})))
            with self.assertRaises(sw.WaterStreamError):sw.WaterStream('bad',60,2,sw.FrozenDict(total),0,sw.StreamPhase.MIXED,inv)

    def test_selective_nonzero_toth_refuses(self):
        s=raw(toth=1,tic=1)
        f={'light':{'h2o':.9,'sodium':.5,'chloride':.5,'total_inorganic_carbon':.1},'heavy':{'h2o':.1,'sodium':.5,'chloride':.5,'total_inorganic_carbon':.9}}
        with self.assertRaises(sw.SelectiveSplitError) as c:sw.split_water_stream(s,f,composition_preserving=False)
        self.assertIn('nonzero TOTH',str(c.exception))

    def test_selective_zero_toth_still_partitions(self):
        s=raw(toth=0,tic=1)
        f={'light':{'h2o':.9,'sodium':.5,'chloride':.5,'total_inorganic_carbon':.1},'heavy':{'h2o':.1,'sodium':.5,'chloride':.5,'total_inorganic_carbon':.9}}
        d=sw.split_water_stream(s,f,composition_preserving=False); self.assertAlmostEqual(d['light'].component_totals_mol_s['total_inorganic_carbon'],.1); self.assertEqual(d['light'].toth_eq_s,0)

    def test_h2o_ledger_closure(self):
        a=raw(water_kg_s=1000); b=raw(water_kg_s=900); L=sw.MassLedger.from_streams('l','loss',[a],[b])
        with self.assertRaises(sw.MassLedgerClosureError) as c:L.assert_closed()
        self.assertIn('h2o',str(c.exception))

    def test_toth_ledger_closure_and_declared_delta(self):
        a=raw(toth=0); b=raw(toth=.25); bad=sw.MassLedger.from_streams('l','t',[a],[b])
        with self.assertRaises(sw.MassLedgerClosureError) as c:bad.assert_closed()
        self.assertIn('TOTH residual',str(c.exception)); self.assertTrue(sw.MassLedger.from_streams('g','t',[a],[b],toth_delta_eq_s=.25).assert_closed())

    def test_double_counted_solid_refused(self):
        e=sw.MassLedgerEntry('calcium',component_in_kg_s=1,component_out_kg_s=1,transferred_to_solid_kg_s=.1,explicit_solid_outlet=True)
        with self.assertRaises(sw.LedgerConventionError):e.assert_convention()

    def test_mixing_commutative(self):
        qa=sw.TrackedQuantity(2,'kg/s','load',sw.MixingRule.EXTENSIVE_SUM); qb=sw.TrackedQuantity(3,'kg/s','load',sw.MixingRule.EXTENSIVE_SUM)
        a=certified(name='a',water_kg_s=800,tracked={'load':qa})
        solid_components={'calcium':0.4,'total_inorganic_carbon':0.4}
        b=sw.WaterStream('b',25,2,sw.FrozenDict(solid_components),0.03,sw.StreamPhase.SOLID,(sw.PhaseInventoryItem(sw.StreamPhase.SOLID,'calcite',sw.FrozenDict(solid_components)),),tracked_quantities=sw.FrozenDict({'load':qb.to_dict()}))
        ab=sw.mix_water_streams([a,b],stream_id='m',output_temperature_c=25.0); ba=sw.mix_water_streams([b,a],stream_id='m',output_temperature_c=25.0)
        self.assertEqual(ab.component_totals_mol_s.to_dict(),ba.component_totals_mol_s.to_dict()); self.assertAlmostEqual(ab.toth_eq_s,ba.toth_eq_s,15); self.assertAlmostEqual(ab.tracked('load').value,ba.tracked('load').value,15); self.assertEqual([x.to_dict() for x in ab.phase_inventory],[x.to_dict() for x in ba.phase_inventory])

    def test_mixing_associative_for_extensives(self):
        qs=[sw.TrackedQuantity(x,'kg/s','load',sw.MixingRule.EXTENSIVE_SUM) for x in (2,3,5)]
        a,b,c=[certified(name=n,water_kg_s=w,tracked={'load':q}) for n,w,q in zip('abc',(500,300,200),qs)]
        ab=sw.mix_water_streams([a,b],stream_id='ab'); ab=ab.with_chemistry_certificate(cert(ab,engine='re-cert'))
        bc=sw.mix_water_streams([b,c],stream_id='bc'); bc=bc.with_chemistry_certificate(cert(bc,engine='re-cert'))
        left=sw.mix_water_streams([ab,c],stream_id='x'); right=sw.mix_water_streams([a,bc],stream_id='y')
        self.assertEqual(left.component_totals_mol_s.to_dict(),right.component_totals_mol_s.to_dict()); self.assertAlmostEqual(left.tracked('load').value,right.tracked('load').value,15); self.assertAlmostEqual(left.toth_eq_s,right.toth_eq_s,15)

    def test_idempotent_one_split_and_reserialize(self):
        s=certified(policy={'gas_boundary':'closed'}); d=sw.split_water_stream(s,{'same':1.0},composition_preserving=True)['same']
        # stream_id is intentionally the operation-assigned daughter identity; all physical state and certificate values must be unchanged/scaled by 1.
        self.assertEqual(d.component_totals_mol_s,s.component_totals_mol_s); self.assertEqual(d.toth_eq_s,s.toth_eq_s); self.assertEqual(d.temperature_c,s.temperature_c); self.assertEqual(d.pressure_bar,s.pressure_bar); self.assertEqual(d.chemistry_policy,s.chemistry_policy); self.assertEqual(d.ionic_strength_mol_kg,s.ionic_strength_mol_kg)
        r=sw.WaterStream.from_dict(json.loads(sw.canonical_json(s.to_dict()))); self.assertEqual(r.to_dict(),s.to_dict())

    def test_nonvolumetric_and_mixed_thermal(self):
        sc={'calcium':1,'total_inorganic_carbon':1}; solid=sw.WaterStream('solid',90,2,sw.FrozenDict(sc),0,sw.StreamPhase.SOLID,(sw.PhaseInventoryItem(sw.StreamPhase.SOLID,'calcite',sw.FrozenDict(sc)),))
        with self.assertRaises(sw.NonVolumetricFlowError):_=solid.flow_m3_s
        with self.assertRaises(sw.MixedPhaseThermalError):sw.mix_water_streams([certified(),solid],stream_id='m')
        m=sw.mix_water_streams([certified(),solid],stream_id='m',output_temperature_c=55); self.assertIn('calcite',{x.identity for x in m.phase_inventory})

    def test_unitop_conformance_rejects_h2o_loss_only(self):
        class Bad:
            def solve(self,feed,*,tracked_transformers=None,extension_transformers=None):
                for key in feed.tracked_quantities:
                    q=feed.tracked(key)
                    if q.transport_policy is sw.TrackedTransportPolicy.OWNER_MUST_TRANSFORM: raise sw.TrackedQuantityTransportError('owner required')
                for ns in feed.extensions:
                    if feed.extension(ns).spec.policy_for('unitop') is sw.ExtensionTransportPolicy.OWNER_MUST_TRANSFORM: raise sw.ExtensionTransportError('owner required')
                comps=feed.component_totals_mol_s.to_dict(); comps['h2o']*=.9
                out=sw.WaterStream('out',feed.temperature_c,feed.pressure_bar,sw.FrozenDict(comps),feed.toth_eq_s,tracked_quantities=feed.tracked_quantities)
                return sw.UnitOpConformanceResult({'out':out},sw.MassLedger.from_streams('reported-clean','reported-clean',[feed],[feed]),0.0)
            def solve_selective_split(self,feed,fractions,*,composition_preserving):
                d=sw.split_water_stream(feed,fractions,composition_preserving=composition_preserving)
                return sw.UnitOpConformanceResult(d,sw.MassLedger.from_streams('s','s',[feed],list(d.values())),0.0)
        with self.assertRaises(sw.MassLedgerClosureError) as caught: sw.assert_unitop_fail_closed(Bad())
        self.assertIn('h2o',str(caught.exception)); self.assertNotIn('TOTH residual',str(caught.exception))

    def test_unitop_conformance_rejects_toth_drift_only(self):
        class Bad:
            def solve(self,feed,*,tracked_transformers=None,extension_transformers=None):
                for key in feed.tracked_quantities:
                    q=feed.tracked(key)
                    if q.transport_policy is sw.TrackedTransportPolicy.OWNER_MUST_TRANSFORM: raise sw.TrackedQuantityTransportError('owner required')
                for ns in feed.extensions:
                    if feed.extension(ns).spec.policy_for('unitop') is sw.ExtensionTransportPolicy.OWNER_MUST_TRANSFORM: raise sw.ExtensionTransportError('owner required')
                out=sw.WaterStream('out',feed.temperature_c,feed.pressure_bar,feed.component_totals_mol_s,feed.toth_eq_s+.25,tracked_quantities=feed.tracked_quantities)
                return sw.UnitOpConformanceResult({'out':out},sw.MassLedger.from_streams('reported-clean','reported-clean',[feed],[feed]),0.0)
            def solve_selective_split(self,feed,fractions,*,composition_preserving):
                d=sw.split_water_stream(feed,fractions,composition_preserving=composition_preserving)
                return sw.UnitOpConformanceResult(d,sw.MassLedger.from_streams('s','s',[feed],list(d.values())),0.0)
        with self.assertRaises(sw.MassLedgerClosureError) as caught: sw.assert_unitop_fail_closed(Bad())
        self.assertIn('TOTH residual',str(caught.exception)); self.assertNotIn('h2o',str(caught.exception).lower())

    def test_unitop_conformance_rejects_dropped_conserved_tracked(self):
        class Bad:
            def solve(self,feed,*,tracked_transformers=None,extension_transformers=None):
                for key in feed.tracked_quantities:
                    q=feed.tracked(key)
                    if q.transport_policy is sw.TrackedTransportPolicy.OWNER_MUST_TRANSFORM: raise sw.TrackedQuantityTransportError('owner required')
                for ns in feed.extensions:
                    if feed.extension(ns).spec.policy_for('unitop') is sw.ExtensionTransportPolicy.OWNER_MUST_TRANSFORM: raise sw.ExtensionTransportError('owner required')
                out=sw.WaterStream('out',feed.temperature_c,feed.pressure_bar,feed.component_totals_mol_s,feed.toth_eq_s)
                return sw.UnitOpConformanceResult({'out':out},sw.MassLedger.from_streams('bad','bad',[feed],[out]),0.0)
            def solve_selective_split(self,feed,fractions,*,composition_preserving):
                d=sw.split_water_stream(feed,fractions,composition_preserving=composition_preserving)
                return sw.UnitOpConformanceResult(d,sw.MassLedger.from_streams('s','s',[feed],list(d.values())),0.0)
        with self.assertRaises(AssertionError) as caught: sw.assert_unitop_fail_closed(Bad())
        self.assertIn('dropped or reclassified',str(caught.exception))

    def test_unitop_conformance_positive_adapter(self):
        class Good:
            def solve(self,feed,*,tracked_transformers=None,extension_transformers=None):
                for key in feed.tracked_quantities:
                    q=feed.tracked(key)
                    if q.transport_policy is sw.TrackedTransportPolicy.OWNER_MUST_TRANSFORM and not tracked_transformers: raise sw.TrackedQuantityTransportError('owner required')
                for ns in feed.extensions:
                    if feed.extension(ns).spec.policy_for('unitop') is sw.ExtensionTransportPolicy.OWNER_MUST_TRANSFORM and not extension_transformers: raise sw.ExtensionTransportError('owner required')
                out=sw.WaterStream('out',feed.temperature_c,feed.pressure_bar,feed.component_totals_mol_s,feed.toth_eq_s,tracked_quantities=feed.tracked_quantities,extensions=feed.extensions)
                return sw.UnitOpConformanceResult({'out':out},sw.MassLedger.from_streams('good','good',[feed],[out]),0.0)
            def solve_selective_split(self,feed,fractions,*,composition_preserving):
                d=sw.split_water_stream(feed,fractions,composition_preserving=composition_preserving)
                return sw.UnitOpConformanceResult(d,sw.MassLedger.from_streams('s','s',[feed],list(d.values())),0.0)
        self.assertTrue(all(sw.assert_unitop_fail_closed(Good()).values()))

    def test_shared_component_phase_selective_refuses(self):
        aq={'h2o':1000,'sodium':1,'chloride':1}; c={'calcium':.5,'total_inorganic_carbon':.5}; g={'calcium':.5,'sulfate':.5}; total={**aq,'calcium':1,'total_inorganic_carbon':.5,'sulfate':.5}; inv=(sw.PhaseInventoryItem(sw.StreamPhase.AQUEOUS,None,sw.FrozenDict(aq)),sw.PhaseInventoryItem(sw.StreamPhase.SOLID,'calcite',sw.FrozenDict(c)),sw.PhaseInventoryItem(sw.StreamPhase.SOLID,'gypsum',sw.FrozenDict(g))); s=sw.WaterStream('m',60,2,sw.FrozenDict(total),0,sw.StreamPhase.MIXED,inv)
        f={'a':{'h2o':.8,'sodium':.8,'chloride':.8,'calcium':.2,'total_inorganic_carbon':.2,'sulfate':.8},'b':{'h2o':.2,'sodium':.2,'chloride':.2,'calcium':.8,'total_inorganic_carbon':.8,'sulfate':.2}}
        with self.assertRaises(sw.SelectiveSplitError):sw.split_water_stream(s,f,composition_preserving=False)

if __name__=='__main__':unittest.main()
