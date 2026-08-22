import math

from addons.ccro.engine import ccro, _ccro_pressure_limit_bar, _ccro_membrane_pressure_limit_bar


def ccro_case(*, full=False, recovery=80, system_volume=5.0):
    data = {
        'flow_unit': 'm3/h', 'pressure_unit': 'bar', 'water_mode': 'full' if full else 'tds',
        'feed_tds': 5000, 'analysis_tds': 5000, 'temperature_c': 25, 'feed_ph': 7.8,
        'membrane_1': 'DuPont FilmTec|SW30HRLE-400|A / standard',
        'vessels_1': 20, 'elements_per_vessel_1': 7, 'permeate_pressure_1': 0,
        'ccro_target_average_recovery': recovery,
        'ccro_closed_circuit_permeate_flow': 60,
        'ccro_concentrate_recycle_per_vessel': 4.54,
        'ccro_pf_feed_ratio': 1.20, 'ccro_pf_recovery': 20,
        'ccro_system_volume_m3': system_volume,
        'ccro_loop_extra_dp': 0.4,
        'suction_pressure': 2,
        'pump_eff': .85, 'motor_eff': .97, 'vfd_eff': .97,
        'ccro_circulation_pump_eff': .82,
        'ccro_circulation_motor_eff': .96,
        'ccro_circulation_vfd_eff': .97,
        'pretreatment_discharge_pressure': 6, 'pretreatment_recovery': .85,
        'pretreatment_pump_eff': .82, 'pretreatment_motor_eff': .95,
        'pretreatment_vfd_eff': .97,
        'fouling_factor': .90, 'salt_passage_factor': 1.0,
    }
    if full:
        data.update({
            'ion_sodium': 1350, 'ion_calcium': 120, 'ion_magnesium': 80,
            'ion_potassium': 20, 'ion_chloride': 2050, 'ion_sulfate': 900,
            'ion_bicarbonate': 250, 'ion_nitrate': 20, 'ion_boron': 2,
            'ion_silica': 40, 'ion_ammonium': 0, 'ion_strontium': 0,
            'ion_barium': 0, 'ion_fluoride': 1, 'ion_bromide': 0,
            'ion_phosphate': 0,
        })
    return data


def test_ccro_addon_mass_balance_pressure_and_energy():
    result = ccro(ccro_case(recovery=80, system_volume=5.0))
    assert result['ccro'] is True
    assert result['process_type'] == 'CCRO'
    assert abs(result['recovery'] - 0.80) < 1e-10
    assert abs(result['ccro_permeate_volume_per_batch_m3'] - 20.0) < 1e-9
    assert abs(result['ccro_brine_flush_volume_m3'] - 5.0) < 1e-12
    assert result['ccro_cc_cycles'] > 1
    assert len(result['ccro_cycle_profile']) == math.ceil(result['ccro_cc_cycles'] - 1e-12)
    assert result['ccro_final_cycle_pressure_bar'] > result['ccro_first_cycle_pressure_bar'] > 0
    assert result['ccro_final_loop_feed_tds_mg_l'] > result['ccro_initial_feed_tds_mg_l']
    assert result['ro_sec'] > 0
    assert abs(result['total_sec'] - (result['ro_sec'] + result['pretreatment_sec'])) < 1e-12


def test_ccro_addon_full_chemistry_scaling_state():
    result = ccro(ccro_case(full=True, recovery=75, system_volume=4.0))
    assert result['composite_permeate_composition_mg_l']
    assert result['ccro_final_loop_composition_mg_l']
    assert 2.0 < float(result['composite_permeate_ph']) < 12.0
    assert result['ccro_highest_mineral_saturation_pct'] is not None
    assert result['ccro_limiting_mineral']
    assert result['ccro_recovery_limiter']


def test_ccro_addon_pressure_envelope_uses_membrane_and_optional_equipment_rating():
    sw = ccro_case(recovery=75)
    assert abs(_ccro_membrane_pressure_limit_bar(sw) - 83.0) < 1e-12
    assert abs(_ccro_pressure_limit_bar(sw) - 83.0) < 1e-12
    sw['ccro_system_pressure_limit'] = 75
    assert abs(_ccro_pressure_limit_bar(sw) - 75.0) < 1e-12

    uhp = ccro_case(recovery=75)
    uhp['membrane_1'] = 'DuPont FilmTec|XUS180804|Transport scaled from XUS180808 historical PDS'
    assert abs(_ccro_membrane_pressure_limit_bar(uhp) - 120.0) < 1e-12
    assert abs(_ccro_pressure_limit_bar(uhp) - 120.0) < 1e-12


def test_ccro_addon_has_no_fixed_ccro_pressure_ceiling():
    result = ccro(ccro_case(recovery=80))
    joined = ' '.join(result['ccro_warnings']).lower()
    assert '41 bar' not in joined
    assert '75–98' not in joined
    assert abs(result['ccro_membrane_pressure_limit_bar'] - 83.0) < 1e-12
    assert abs(result['ccro_system_pressure_limit_bar'] - 83.0) < 1e-12
    assert result['ccro_pressure_margin_bar'] > 0


def test_ccro_runtime_registration_is_additive_and_available_all_tiers(monkeypatch):
    import sys
    import types
    from addons.ccro import register_ccro

    fake_flask = types.ModuleType('flask')
    fake_flask.jsonify = lambda payload: payload
    monkeypatch.setitem(sys.modules, 'flask', fake_flask)

    class DummyApp:
        def __init__(self):
            self.routes = {}
        def get(self, path):
            def deco(fn):
                self.routes[path] = fn
                return fn
            return deco

    gated = []
    app = DummyApp()
    registry = {'multistage': object()}
    register_ccro(app, registry, lambda feature: gated.append(feature))

    assert 'multistage' in registry
    assert registry['ccro'] is ccro
    assert gated == []
    status = app.routes['/api/addons/ccro/status']()
    assert status['addon'] == 'totalrodesign.ccro'
    assert status['minimum_tier'] == 'entry'
    assert status['available_all_tiers'] is True
