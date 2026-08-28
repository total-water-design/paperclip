import pytest

from addons.batch_ro.engine import calculate_batch_ro


MEMBRANE = "DuPont FilmTec|SW30HR-380|A / standard"


def payload(target):
    return {
        "flow_unit": "m3/h",
        "pressure_unit": "bar",
        "water_mode": "tds",
        "feed_tds": 35000,
        "temperature_c": 25,
        "membrane_1": MEMBRANE,
        "vessels_1": 8,
        "elements_per_vessel_1": 8,
        "batch_target_recovery": target,
        "batch_average_product_flow": 15,
        "batch_reset_time_s": 10,
        "batch_time_steps": 20,
        "batch_system_pressure_limit": 80,
        "batch_recirculation_flow_per_vessel": 5,
        "pump_eff": 0.85,
        "motor_eff": 0.97,
        "vfd_eff": 0.97,
        "suction_pressure": 2.0,
        "permeate_pressure_1": 0.0,
    }


def test_real_swro_40_percent_reaches_target():
    r = calculate_batch_ro(payload(40))

    assert r["batch_ro_achieved_recovery_pct"] == pytest.approx(40, abs=0.3)
    assert r["batch_ro_peak_pressure_bar"] <= 80
    assert abs(r["batch_ro_salt_balance_residual_pct"]) < 0.1
    assert "Target recovery reached" in r["batch_ro_recovery_limiter"]


@pytest.mark.parametrize("target", [45, 50])
def test_real_swro_high_request_stops_at_pressure_limit(target):
    r = calculate_batch_ro(payload(target))

    assert r["batch_ro_achieved_recovery_pct"] < target
    assert r["batch_ro_pressure_limit_bar"] == pytest.approx(80)
    assert r["batch_ro_peak_pressure_bar"] <= 80
    assert abs(r["batch_ro_salt_balance_residual_pct"]) < 0.1
    assert "Pressure" in r["batch_ro_recovery_limiter"]
    assert "80.00 bar" in r["batch_ro_recovery_limiter_detail"]
