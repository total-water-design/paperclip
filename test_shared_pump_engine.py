import pump_db


def test_vcmp_legacy_api_still_selects():
    result = pump_db.select_vcmp(55.0, 18.0, density_kg_m3=998.0, top_n=1)
    assert result["ok"]
    assert result["selected"]["technology"] == "VCMP"
    assert result["selected"]["wire_kw"] > 0


def test_hhecp_exact_curve_recovers_known_duty():
    model = pump_db.HHECP_BY_CODE["HHECP-4022"]
    result = pump_db.evaluate_hhecp(model, 37.2, 61.6, density_kg_m3=1029.0, min_vfd_hz=30.0, max_vfd_hz=60.0)
    assert result is not None
    assert abs(result["speed_rpm"] - 3386.0) < 1e-6
    assert abs(result["pump_efficiency"] - 0.798) < 1e-6
    assert abs(result["shaft_kw"] - 79.8) < 1e-6
    assert abs(result["npshr_m"] - 3.0) < 1e-6


def test_hhecp_stage_expansion_reaches_82_bar_for_every_family():
    families = {}
    for model in pump_db.HHECP_MODELS:
        families.setdefault(int(model["nominal_flow_m3h"]), []).append(model)
    assert len(families) == 9
    for models in families.values():
        assert max(float(m["reference_dp_bar"]) for m in models) >= 82.0


def test_positive_displacement_parallel_selection():
    result = pump_db.select_pump(55.0, 18.0, available_inlet_bar=2.0, technologies=("pd",), max_duty_units=10)
    assert result["ok"]
    assert result["selected"]["technology"] == "PD"
    assert result["selected"]["duty_units"] >= 1
    assert result["selected"]["wire_kw"] > 0


def test_shared_selector_handles_large_hhecp_duty():
    result = pump_db.select_pump(600.0, 50.0, density_kg_m3=998.0, technologies=("hhecp",), max_duty_units=10)
    assert result["ok"]
    assert result["selected"]["technology"] == "HHECP"
    assert result["selected"]["wire_kw"] > 0


def test_hhecp_curve_points_are_available_for_existing_chart_api():
    result = pump_db.select_pump(600.0, 50.0, technologies=("hhecp",), top_n=1)
    assert result["ok"]
    selected = result["selected"]
    points = pump_db.curve_points(selected["source_id"], selected["speed_ratio"])
    assert len(points) == 25
    assert all(point["flow_m3h"] >= 0 for point in points)
