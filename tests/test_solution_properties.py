import pytest

from total_zld_design.solution_properties import (
    additive_volume_density_kg_m3,
    g_per_kg_solvent_to_mass_fraction,
    ideal_mixture_heat_capacity_kj_kg_k,
    mass_fraction_to_g_per_kg_solvent,
    saturation_state,
    watson_latent_heat_kj_kg,
)


def test_concentration_basis_round_trip():
    x = 0.2
    assert g_per_kg_solvent_to_mass_fraction(mass_fraction_to_g_per_kg_solvent(x)) == pytest.approx(x, rel=1e-12)


def test_saturation_bookkeeping_distinguishes_under_saturated_and_super():
    assert saturation_state(90.0, 100.0).state == "undersaturated"
    sat = saturation_state(100.0, 100.0)
    assert sat.state == "saturated"
    sup = saturation_state(120.0, 100.0)
    assert sup.state == "supersaturated"
    assert sup.saturation_ratio == pytest.approx(1.2)
    assert sup.relative_supersaturation == pytest.approx(0.2)
    assert sup.absolute_supersaturation == pytest.approx(20.0)


def test_additive_volume_density_is_bounded_by_component_densities():
    rho = additive_volume_density_kg_m3(0.20, 2160.0, 998.0)
    assert 998.0 < rho < 2160.0


def test_ideal_heat_capacity_mixing_uses_mass_fraction_weighting():
    cp = ideal_mixture_heat_capacity_kj_kg_k([0.8, 0.2], [4.18, 0.85])
    assert cp == pytest.approx(3.514)


def test_watson_latent_heat_decreases_as_temperature_approaches_critical():
    h1 = watson_latent_heat_kj_kg(2257.0, 373.15, 393.15, 647.096)
    h2 = watson_latent_heat_kj_kg(2257.0, 373.15, 423.15, 647.096)
    assert 0 < h2 < h1 < 2257.0
