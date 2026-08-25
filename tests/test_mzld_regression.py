import json
from pathlib import Path
import pytest
from total_zld_design import calculate_thermal_legacy

ROOT = Path(__file__).resolve().parents[1]


def test_saved_mzld_case_matches_workbook():
    exp = json.loads((ROOT / "fixtures/mzld_saved_case.json").read_text())["expected"]
    r = calculate_thermal_legacy()
    assert r.modules["brine_concentrator"]["distillate_m3_h"] == pytest.approx(exp["bc_distillate_m3_h"], rel=1e-12)
    assert r.modules["brine_concentrator"]["concentrate_m3_h"] == pytest.approx(exp["bc_concentrate_m3_h"], rel=1e-12)
    assert r.modules["brine_concentrator"]["total_power_kw"] == pytest.approx(exp["bc_power_kw"], rel=1e-12)
    assert r.modules["vffe"]["distillate_m3_h"] == pytest.approx(exp["vffe_distillate_m3_h"], rel=1e-12)
    assert r.modules["vffe"]["concentrate_m3_h"] == pytest.approx(exp["vffe_concentrate_m3_h"], rel=1e-12)
    assert r.modules["vffe"]["film_reynolds"] == pytest.approx(exp["vffe_film_re"], rel=1e-12)
    assert r.modules["vffe"]["film_htc_w_m2_k"] == pytest.approx(exp["vffe_film_htc_w_m2_k"], rel=1e-12)
    assert r.modules["vffe"]["live_steam_t_h"] == pytest.approx(exp["vffe_live_steam_t_h"], rel=1e-12)
    assert r.modules["fcc"]["relative_supersaturation"] == pytest.approx(exp["fcc_supersaturation"], rel=1e-12)
    assert r.modules["fcc"]["dominant_crystal_size_mm"] == pytest.approx(exp["fcc_dominant_crystal_mm"], rel=1e-12)
    assert r.modules["fcc"]["dry_salt_t_h"] == pytest.approx(exp["fcc_dry_salt_t_h"], rel=1e-12)
    assert r.modules["fcc"]["mother_liquor_m3_h"] == pytest.approx(exp["fcc_mother_liquor_m3_h"], rel=1e-12)
    assert r.summary["overall_recovery"] == pytest.approx(exp["overall_recovery"], rel=1e-12)
    assert r.summary["total_electrical_power_kw"] == pytest.approx(exp["total_power_kw"], rel=1e-12)
    assert r.summary["total_live_steam_t_h"] == pytest.approx(exp["total_live_steam_t_h"], rel=1e-12)
    assert r.summary["screening_capex_usd"] == pytest.approx(exp["screening_capex_usd"], rel=1e-12)


def test_known_critical_gaps_are_visible_not_hidden():
    r = calculate_thermal_legacy()
    codes = {w.code for w in r.warnings}
    assert "VFFE-T-001" in codes
    assert "FCC-RECYCLE-001" in codes
    assert "THERMO-001" in codes
    assert "screening" in r.model_status
