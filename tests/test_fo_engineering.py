import pytest

from total_zld_design import calculate, calculate_fo_engineering, fo_engineering_defaults


def test_industrial_fo_mode_is_available_without_replacing_workbook_regression():
    result = calculate("fo_engineering")
    assert result.mode == "fo_engineering"
    assert result.model_version == "0.3.0-phase1"
    assert calculate("fo_regression").mode == "fo_regression"


def test_fo_engineering_closes_water_and_total_solute_mass_balances():
    result = calculate_fo_engineering()
    mb = result.modules["mass_balance"]
    assert mb["water_balance_error_m3_h"] == pytest.approx(0.0, abs=1e-12)
    assert mb["solute_balance_error_kg_h"] == pytest.approx(0.0, abs=1e-9)
    assert result.summary["water_transferred_m3_h"] > 0.0
    assert result.summary["final_feed_total_solute_kg_m3"] > result.inputs["feed"]["total_solute_kg_m3"]
    assert result.summary["final_draw_total_solute_kg_m3"] < result.inputs["draw"]["total_solute_kg_m3"]


def test_pafo_assistance_increases_water_transfer_and_energy():
    base = calculate_fo_engineering()
    assisted = calculate_fo_engineering({"operation": {"feed_applied_pressure_bar": 4.0}})
    assert assisted.summary["water_transferred_m3_h"] > base.summary["water_transferred_m3_h"]
    assert assisted.summary["circulation_power_kw"] > base.summary["circulation_power_kw"]
    assert any(w.code == "FO-PAFO-001" for w in assisted.warnings)


def test_higher_water_permeability_increases_transfer_at_fixed_system_basis():
    low = calculate_fo_engineering({"membrane": {"water_permeability_lmh_bar": 1.0}})
    high = calculate_fo_engineering({"membrane": {"water_permeability_lmh_bar": 4.0}})
    assert high.summary["water_transferred_m3_h"] > low.summary["water_transferred_m3_h"]


def test_orientation_is_an_explicit_engineering_variable():
    al_fs = calculate_fo_engineering({"membrane": {"orientation": "AL-FS"}})
    al_ds = calculate_fo_engineering({"membrane": {"orientation": "AL-DS"}})
    assert al_fs.modules["membrane"]["orientation"] == "AL-FS"
    assert al_ds.modules["membrane"]["orientation"] == "AL-DS"
    assert al_fs.summary["water_transferred_m3_h"] != pytest.approx(al_ds.summary["water_transferred_m3_h"], rel=1e-8)


def test_reverse_solute_flux_is_nonnegative_and_accumulates_in_feed():
    result = calculate_fo_engineering()
    segments = result.modules["segments"]
    assert segments
    assert all(row["reverse_solute_flux_g_m2_h"] >= 0.0 for row in segments)
    assert result.summary["total_reverse_draw_solute_kg_h"] >= 0.0


def test_pafo_rejects_pressure_above_membrane_tmp_limit():
    with pytest.raises(ValueError, match="maximum TMP"):
        calculate_fo_engineering({
            "membrane": {"maximum_tmp_bar": 5.0},
            "operation": {"feed_applied_pressure_bar": 6.0},
        })


def test_phase1_explicitly_discloses_external_thermodynamics_dependency():
    result = calculate_fo_engineering()
    assert any(w.code == "FO-THERMO-001" for w in result.warnings)
    assert "Shared Water Chemistry" in next(w.detail for w in result.warnings if w.code == "FO-THERMO-001")
    assert "external thermodynamics" in result.model_status


def test_defaults_retain_porifera_scale_membrane_parameters_as_engineering_seed():
    defaults = fo_engineering_defaults()
    assert defaults["membrane"]["water_permeability_lmh_bar"] == pytest.approx(2.2)
    assert defaults["membrane"]["structural_parameter_um"] == pytest.approx(215.0)
    assert defaults["operation"]["segments"] >= 10
