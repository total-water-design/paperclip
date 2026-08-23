import inspect
import unittest
from pathlib import Path

import calculations
import membrane_db


class SharedMembraneCatalogIntegrationTests(unittest.TestCase):
    def test_no_duplicate_canonical_identities(self):
        identities = [membrane_db._identity(row) for row in membrane_db.MEMBRANES]
        self.assertEqual(len(identities), len(set(identities)))

    def test_ro_and_nf_groups_exist(self):
        groups = membrane_db.grouped_membranes(suite_app='total-ro-design')
        self.assertIn('RO', groups)
        self.assertIn('NF', groups)
        self.assertGreater(len(groups['RO']), 0)
        self.assertGreater(len(groups['NF']), 0)

    def test_nanoh2o_display_and_all_legacy_lg_ids_resolve(self):
        sample = next(row for row in membrane_db.MEMBRANES if row.get('manufacturer') == 'NanoH2O' and row.get('calculation_enabled', True))
        self.assertEqual(sample['manufacturer'], 'NanoH2O')
        suffix = sample['record_id'].split('|',1)[1]
        for legacy in ('LG Water Solutions','LG NanoH2O','LG Chem Water Solutions'):
            resolved = membrane_db.get_membrane(f'{legacy}|{suffix}')
            self.assertEqual(resolved['record_id'], sample['record_id'])
            self.assertEqual(resolved['manufacturer'], 'NanoH2O')

    def test_trisep_ready_records_use_explicit_shared_A_B(self):
        ready = [r for r in membrane_db.MEMBRANES if r.get('manufacturer') == 'TRISEP' and r.get('calculation_enabled', True)]
        self.assertGreaterEqual(len(ready), 39)
        for row in ready:
            self.assertIsNotNone(row.get('specific_flux_A_app_lmh_bar'), row['record_id'])
            self.assertIsNotNone(row.get('salt_permeability_B_lmh'), row['record_id'])
            a, b = calculations._membrane_model_coefficients(membrane_db.get_membrane(row['record_id']))
            self.assertAlmostEqual(a, float(row['specific_flux_A_app_lmh_bar']), places=12)
            self.assertAlmostEqual(b, float(row['salt_permeability_B_lmh']), places=12)

    def test_catalog_only_upr_and_incomplete_ds_cannot_calculate(self):
        blocked = [r for r in membrane_db.MEMBRANES if r.get('manufacturer') == 'TRISEP' and (str(r.get('model','')).startswith('UPR ') or r.get('model') == 'DS TS40 8038-65')]
        self.assertTrue(blocked)
        for row in blocked:
            self.assertFalse(row.get('calculation_enabled', True), row['record_id'])
            with self.assertRaises(ValueError):
                membrane_db.get_membrane(row['record_id'])

    def test_hybrid_recipe_accepts_shared_catalog_records(self):
        ready = [r for r in membrane_db.MEMBRANES if r.get('calculation_enabled', True) and r.get('membrane_type','RO').upper() == 'RO']
        self.assertGreaterEqual(len(ready), 2)
        recipe = [ready[0]['record_id'], ready[1]['record_id']]
        normalized = calculations._normalize_membrane_recipe(recipe[0], 2, recipe)
        self.assertEqual(normalized, recipe)
        self.assertEqual(len([membrane_db.get_membrane(mid) for mid in normalized]), 2)

    def test_uniform_stage_result_carries_canonical_manufacturer_model(self):
        # Locate the existing stage transport solver without depending on a renamed private symbol.
        candidates=[]
        for name, fn in inspect.getmembers(calculations, inspect.isfunction):
            doc = (fn.__doc__ or '')
            if 'Element-to-element clean RO stage calculation' in doc:
                candidates.append((name,fn))
        self.assertEqual(len(candidates),1,candidates)
        name, fn = candidates[0]
        sig = inspect.signature(fn)
        sample = next(r for r in membrane_db.MEMBRANES if r.get('manufacturer') == 'NanoH2O' and r.get('calculation_enabled', True) and r.get('membrane_type','RO').upper() == 'RO')
        values = {
            'membrane_id': sample['record_id'], 'vessels': 10, 'elements_per_vessel': 2,
            'q_feed_m3h': 100.0, 'feed_flow_m3h': 100.0, 'feed_m3h': 100.0,
            'p_feed_bar': 20.0, 'feed_pressure_bar': 20.0, 'membrane_pressure_bar': 20.0,
            'feed_tds_ppm': 2000.0, 'target_recovery': 0.10, 'recovery': 0.10,
            'permeate_pressure_bar': 0.0, 'temperature_c': 25.0,
            'feed_ionic_strength': None, 'datasheet_max_dp_per_element_bar': 1.0,
            'feed_composition': None, 'feed_ph': 7.6, 'water_mode': 'tds',
            'fouling_factor': 1.0, 'salt_passage_factor': 1.0,
            'feed_carbonate_state': None, 'resolve_carbonate_streams': False,
            'membrane_recipe': None,
        }
        kwargs={}
        missing=[]
        for pname,param in sig.parameters.items():
            if pname in values:
                kwargs[pname]=values[pname]
            elif param.default is inspect._empty:
                missing.append(pname)
        self.assertFalse(missing, f'{name} required unmapped parameters {missing}; signature={sig}')
        result=fn(**kwargs)
        self.assertEqual(result['membrane_manufacturer'],'NanoH2O')
        self.assertEqual(result['membrane_model'],sample['model'])

    def test_menu_override_keeps_ro_nf_sections_and_disables_catalog_only(self):
        text = Path('static/membrane_catalog_ui.js').read_text(encoding='utf-8')
        self.assertIn("const order = ['RO', 'NF']", text)
        self.assertIn("Reverse Osmosis (RO)", text)
        self.assertIn("Nanofiltration (NF)", text)
        self.assertIn("catalog only", text)
        template = Path('templates/index.html').read_text(encoding='utf-8')
        self.assertIn("membrane_catalog_ui.js", template)


if __name__ == '__main__':
    unittest.main()
