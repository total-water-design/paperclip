import json
from pathlib import Path
import pytest
from total_zld_design import calculate_fo_regression

ROOT = Path(__file__).resolve().parents[1]


def test_saved_fo_case_matches_workbook():
    exp = json.loads((ROOT / "fixtures/fo_saved_case.json").read_text())["expected"]
    r = calculate_fo_regression()
    flux = [x["water_flux_lmh"] for x in r.modules["stages"]]
    assert flux == pytest.approx(exp["stage_flux_lmh"], rel=1e-12, abs=1e-12)
    s = r.summary
    assert s["total_water_recovered_m3_h"] == pytest.approx(exp["total_water_recovered_m3_h"], rel=1e-12)
    assert s["feed_water_recovery"] == pytest.approx(exp["feed_water_recovery"], rel=1e-12)
    assert s["final_bulk_concentration_factor"] == pytest.approx(exp["final_bulk_cf"], rel=1e-12)
    assert s["final_feed_osmotic_pressure_bar"] == pytest.approx(exp["final_feed_osmotic_pressure_bar"], rel=1e-12)
    assert s["average_water_flux_lmh"] == pytest.approx(exp["average_flux_lmh"], rel=1e-12)
    assert s["maximum_cp_modulus"] == pytest.approx(exp["max_cp_modulus"], rel=1e-12)
    assert s["maximum_wall_concentration_factor"] == pytest.approx(exp["max_wall_cf"], rel=1e-12)
    assert s["wall_equivalent_recovery"] == pytest.approx(exp["wall_equivalent_recovery"], rel=1e-12)
    assert s["total_draw_solute_lost_kg_h"] == pytest.approx(exp["total_draw_solute_lost_kg_h"], rel=1e-12)
    assert s["diluted_draw_molality"] == pytest.approx(exp["diluted_draw_molality"], rel=1e-12)
    assert s["diluted_draw_osmotic_pressure_bar"] == pytest.approx(exp["diluted_draw_osmotic_pressure_bar"], rel=1e-12)
    assert s["specific_area_m2_per_m3_h_product"] == pytest.approx(exp["specific_area"], rel=1e-12)
    assert s["reverse_draw_solute_added_mg_l"] == pytest.approx(exp["reverse_draw_solute_added_mg_l"], rel=1e-12)


def test_bulk_and_wall_states_are_separate():
    r = calculate_fo_regression()
    h = r.modules["handoff"]
    assert h["bulk_outlet"]["bulk_concentration_factor"] < h["wall_diagnostic"]["maximum_wall_concentration_factor"]
    assert "Do not use" in h["wall_diagnostic"]["note"]
