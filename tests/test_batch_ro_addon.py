import math

import pytest

from addons.batch_ro import engine


class _Membrane:
    def __init__(self):
        self.area_m2 = 40.0


def _record(_mid):
    return {
        "area_m2": 40.0,
        "length_m": 1.016,
        "max_operating_pressure_bar": 83.0,
        "model": "TEST-400",
        "manufacturer": "Test",
    }


def _fake_stage(q_feed, pressure, membrane_id, vessels, epv, feed_tds, **kwargs):
    # Smooth monotonic synthetic membrane used only to test the Batch RO layer.
    perm = max(0.0, min(q_feed * 0.60, (pressure - feed_tds / 1500.0) * 0.60))
    perm_tds = max(1.0, feed_tds * 0.003)
    reject = q_feed - perm
    conc = (q_feed * feed_tds - perm * perm_tds) / max(reject, 1e-9)
    return {
        "permeate_flow": perm,
        "reject_flow": reject,
        "recovery": perm / q_feed,
        "permeate_tds_ppm": perm_tds,
        "concentrate_tds_ppm": conc,
        "feed_tds_ppm": feed_tds,
        "feed_osmotic_bar": feed_tds / 1500.0,
        "concentrate_osmotic_bar": conc / 1500.0,
        "stage_dp_bar": 0.8,
        "reject_pressure_bar": pressure - 0.8,
        "ndp_bar": max(0.0, pressure - feed_tds / 1500.0),
        "flux_lmh": perm * 1000 / (vessels * epv * 40.0),
        "avg_polarization_factor": 1.08,
        "dp_limit_fraction": 0.5,
        "membrane_manufacturer": "Test",
        "membrane_model": "TEST-400",
        "membrane_total_area_m2": vessels * epv * 40.0,
        "a_app_lmh_bar": 1.0,
        "a_clean_lmh_bar": 1.0,
        "b_app_lmh": 0.1,
        "b_clean_lmh": 0.1,
        "a_datasheet_lmh_bar": 1.0,
        "b_datasheet_lmh": 0.1,
        "membrane_elements": vessels * epv,
        "pressure_vessels": vessels,
        "elements_per_vessel": epv,
        "element_results": [],
    }


def _attach(result, stage, prefix):
    result[prefix + "membrane_model"] = stage.get("membrane_model")


@pytest.fixture(autouse=True)
def patch_model(monkeypatch):
    monkeypatch.setattr(engine, "get_membrane", _record)
    monkeypatch.setattr(engine, "membrane_stage", _fake_stage)
    monkeypatch.setattr(engine, "_attach_membrane", _attach)


def base_payload(**extra):
    p = {
        "flow_unit": "m3/h",
        "pressure_unit": "bar",
        "water_mode": "tds",
        "feed_tds": 3000,
        "temperature_c": 25,
        "membrane_1": "test",
        "vessels_1": 8,
        "elements_per_vessel_1": 8,
        "batch_target_recovery": 50,
        "batch_average_product_flow": 15,
        "batch_reset_time_s": 10,
        "batch_time_steps": 12,
        "batch_system_pressure_limit": 80,
        "batch_recirculation_flow_per_vessel": 5,
        "pump_eff": .85,
        "motor_eff": .97,
        "vfd_eff": .97,
    }
    p.update(extra)
    return p


def test_batch_cycle_reaches_target_and_closes_salt_balance():
    r = engine.calculate_batch_ro(base_payload())
    assert r["batch_ro"] is True
    assert r["batch_ro_achieved_recovery_pct"] == pytest.approx(50.0, abs=0.3)
    assert r["batch_ro_productive_time_s"] > 0
    assert r["batch_ro_cycle_time_s"] > r["batch_ro_productive_time_s"]
    assert r["batch_ro_effective_flux_lmh"] < r["batch_ro_active_flux_lmh"]
    assert abs(r["batch_ro_salt_balance_residual_pct"]) < 0.1
    assert r["ro_sec"] > 0


def test_dual_compartment_has_no_productive_reset_downtime():
    r = engine.calculate_batch_ro(base_payload(batch_configuration="dual_compartment"))
    assert r["batch_ro_effective_reset_downtime_s"] == 0
    assert r["batch_ro_cycle_time_s"] == pytest.approx(r["batch_ro_productive_time_s"])
    assert r["batch_ro_duty_factor"] == pytest.approx(1.0)


def test_high_external_volume_is_flagged():
    r = engine.calculate_batch_ro(base_payload(batch_piping_volume_pct_elements=30))
    assert r["batch_ro_external_volume_pct_elements"] >= 30
    assert any("external liquid volume" in w for w in r["batch_ro_warnings"])


def test_pressure_limit_stops_recovery_before_target():
    r = engine.calculate_batch_ro(base_payload(batch_system_pressure_limit=12, batch_average_product_flow=5))
    assert r["batch_ro_achieved_recovery_pct"] < 50
    assert "Pressure" in r["batch_ro_recovery_limiter"]
