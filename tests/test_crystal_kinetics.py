import math
import pytest

from total_zld_design.crystal_kinetics import (
    arrhenius_rate_constant,
    power_law_growth_rate,
    power_law_nucleation_rate,
    heterogeneous_surface_energy_factor,
    classical_critical_radius_m,
    classical_homogeneous_barrier_j,
    classical_nucleation_rate,
    heterogeneous_nucleation_rate,
    combined_diffusion_surface_growth_coefficient,
    growth_control_regime,
    secondary_nucleation_risk,
)


def test_power_law_growth_and_nucleation_increase_with_supersaturation():
    g1 = power_law_growth_rate(0.05, 2.0e-7, 1.5).rate
    g2 = power_law_growth_rate(0.10, 2.0e-7, 1.5).rate
    b1 = power_law_nucleation_rate(0.05, 1.0e8, 2.0).rate
    b2 = power_law_nucleation_rate(0.10, 1.0e8, 2.0).rate
    assert g2 > g1 > 0
    assert b2 > b1 > 0


def test_arrhenius_rate_constant_increases_with_temperature():
    low = arrhenius_rate_constant(1.0e6, 45000.0, 298.15)
    high = arrhenius_rate_constant(1.0e6, 45000.0, 330.15)
    assert high > low > 0


def test_heterogeneous_surface_factor_has_expected_limits():
    assert heterogeneous_surface_energy_factor(0.0) == pytest.approx(0.0, abs=1e-15)
    assert heterogeneous_surface_energy_factor(90.0) == pytest.approx(0.5, rel=1e-12)
    assert heterogeneous_surface_energy_factor(180.0) == pytest.approx(1.0, rel=1e-12)


def test_classical_nucleation_barrier_and_radius_drop_with_supersaturation():
    sigma = 0.08
    v = 4.5e-29
    t = 298.15
    r_low = classical_critical_radius_m(sigma, v, t, 1.05)
    r_high = classical_critical_radius_m(sigma, v, t, 1.20)
    dg_low = classical_homogeneous_barrier_j(sigma, v, t, 1.05)
    dg_high = classical_homogeneous_barrier_j(sigma, v, t, 1.20)
    assert r_high < r_low
    assert dg_high < dg_low
    assert math.isinf(classical_critical_radius_m(sigma, v, t, 1.0))


def test_heterogeneous_nucleation_is_faster_for_partial_wetting_than_homogeneous():
    t = 298.15
    barrier = classical_homogeneous_barrier_j(0.03, 4.5e-29, t, 1.2)
    homogeneous = classical_nucleation_rate(1.0e30, barrier, t)
    heterogeneous = heterogeneous_nucleation_rate(1.0e30, barrier, t, 60.0)
    assert heterogeneous > homogeneous >= 0


def test_combined_growth_coefficient_behaves_as_resistances_in_series():
    kd, ki = 2.0, 5.0
    overall = combined_diffusion_surface_growth_coefficient(kd, ki)
    assert overall == pytest.approx(1.0 / (1.0 / kd + 1.0 / ki))
    assert overall < min(kd, ki)


def test_growth_control_regime_classification():
    assert growth_control_regime(1.0, 10.0) == "diffusion-controlled"
    assert growth_control_regime(10.0, 1.0) == "surface-integration-controlled"
    assert growth_control_regime(2.0, 1.0) == "mixed-control"


def test_secondary_nucleation_screen_does_not_fabricate_quantitative_rate():
    result = secondary_nucleation_risk(1.25, True, "high")
    assert result["risk"] == "high"
    assert "attrition" in result["candidate_mechanisms"]
    assert result["kinetic_rate_available"] is False
