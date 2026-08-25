import pytest

from total_zld_design import calculate, shahzad_horizontal_saline_ffe_htc, size_falling_film_evaporator
from total_zld_design.falling_film_evaporator import falling_film_defaults


def test_published_correlation_default_seed_is_inside_source_range():
    d = falling_film_defaults()
    r = shahzad_horizontal_saline_ffe_htc(
        viscosity_pa_s=d["liquid_viscosity_pa_s"],
        density_kg_m3=d["feed_density_kg_m3"],
        thermal_conductivity_w_m_k=d["liquid_thermal_conductivity_w_m_k"],
        cp_j_kg_k=d["solution_cp_kj_kg_k"] * 1000.0,
        film_reynolds=d["film_reynolds"],
        salinity_ppm=d["feed_tds_mg_l"],
        saturation_temperature_k=d["boiling_temperature_c"] + d["boiling_point_elevation_c"] + 273.15,
        heat_flux_w_m2=d["heat_flux_w_m2"],
        film_delta_t_k=d["film_delta_t_k"],
        vapor_specific_volume_m3_kg=d["vapor_specific_volume_m3_kg"],
    )
    assert r.in_published_range
    assert r.heat_transfer_coefficient_w_m2_k > 0
    assert r.bubble_assisted_term_w_m2_k > 0


def test_ffe_design_closes_nonvolatile_solute_mass_balance_and_sizes_area():
    result = size_falling_film_evaporator()
    s = result.summary
    m = result.modules["falling_film_evaporator"]
    assert result.mode == "falling_film_evaporator"
    assert s["evaporation_rate_kg_h"] > 0
    assert s["heat_duty_kw"] > 0
    assert s["required_heat_transfer_area_m2"] > 0
    assert s["required_tube_count"] >= 1
    assert m["installed_heat_transfer_area_m2"] >= m["required_heat_transfer_area_m2"]
    feed_solids = m["feed_mass_flow_kg_h"] * (result.inputs["feed_tds_mg_l"] / 1000.0) / result.inputs["feed_density_kg_m3"]
    assert m["solids_mass_flow_kg_h"] == pytest.approx(feed_solids, rel=1e-12)


def test_hypersaline_zld_condition_requires_validated_design_u():
    with pytest.raises(ValueError, match="outside its published range"):
        size_falling_film_evaporator({"feed_tds_mg_l": 150000.0, "target_concentrate_tds_mg_l": 220000.0})
    result = size_falling_film_evaporator({
        "feed_tds_mg_l": 150000.0,
        "target_concentrate_tds_mg_l": 220000.0,
        "feed_density_kg_m3": 1120.0,
        "concentrate_density_kg_m3": 1180.0,
        "design_overall_u_w_m2_k": 900.0,
    })
    assert any(w.code == "FFE-ZLD-001" for w in result.warnings)
    assert result.summary["overall_u_w_m2_k"] == pytest.approx(900.0)


def test_bpe_increases_required_temperature_and_changes_lmtd():
    base = size_falling_film_evaporator()
    raised = size_falling_film_evaporator({"boiling_point_elevation_c": 2.0})
    assert raised.modules["falling_film_evaporator"]["boiling_temperature_c_including_bpe"] == pytest.approx(27.0)
    assert raised.modules["falling_film_evaporator"]["lmtd_k"] < base.modules["falling_film_evaporator"]["lmtd_k"]


def test_engine_alias_exposes_ffe_without_replacing_thermal_regression():
    assert calculate("ffe").mode == "falling_film_evaporator"
    assert calculate("thermal").mode == "thermal_legacy"
