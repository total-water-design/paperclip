import math

import pytest

from total_zld_design.population_balance import (
    fit_msmpr,
    moment_mean_size,
    moments,
    msmpr_diagnostic,
    msmpr_population_density,
    msmpr_theoretical_moment,
    population_density_from_bins,
)


def test_population_density_reduction_matches_count_over_bin_width_and_volume():
    rows = population_density_from_bins([10, 14], [14, 20], [1000, 2000], sample_volume=0.001)
    assert rows[0]["population_density"] == pytest.approx(250_000.0)
    assert rows[1]["population_density"] == pytest.approx(333_333.3333333333)


def test_msmpr_fit_recovers_growth_and_nucleation_from_semilog_line():
    tau = 2.0
    growth = 5.0
    n0 = 1000.0
    sizes = [0, 10, 20, 30, 40]
    densities = [msmpr_population_density(L, n0, growth, tau) for L in sizes]
    fit = fit_msmpr(sizes, densities, tau)
    assert fit.growth_rate_size_per_time == pytest.approx(growth, rel=1e-12)
    assert fit.n0 == pytest.approx(n0, rel=1e-12)
    assert fit.nucleation_rate_number_per_volume_time == pytest.approx(n0 * growth, rel=1e-12)
    assert fit.r_squared == pytest.approx(1.0, abs=1e-12)


def test_ideal_msmpr_moments_have_factorial_relationship():
    n0, G, tau = 12.0, 3.0, 4.0
    scale = G * tau
    assert msmpr_theoretical_moment(0, n0, G, tau) == pytest.approx(n0 * scale)
    assert msmpr_theoretical_moment(1, n0, G, tau) == pytest.approx(n0 * scale**2)
    assert msmpr_theoretical_moment(3, n0, G, tau) == pytest.approx(math.factorial(3) * n0 * scale**4)


def test_binned_moments_support_mean_size_ratios():
    rows = population_density_from_bins([0, 10], [10, 20], [100, 100], sample_volume=1.0)
    m = moments(rows, maximum_order=4)
    assert m[0] == pytest.approx(200.0)
    assert moment_mean_size(m, 1, 0) > 0.0
    assert moment_mean_size(m, 4, 3) > moment_mean_size(m, 1, 0)


def test_curved_csd_is_not_silently_declared_ideal_msmpr():
    sizes = [10, 20, 30, 40, 50]
    densities = [1000, 600, 360, 250, 230]
    d = msmpr_diagnostic(sizes, densities, residence_time=1.0)
    assert not d["ideal_msmpr_consistent"]
    assert "agglomeration" in d["candidate_nonideal_mechanisms"]
