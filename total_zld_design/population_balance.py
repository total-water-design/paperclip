"""Population-balance utilities for crystallizer analysis.

The functions here support measured crystal-size-distribution (CSD) reduction,
ideal MSMPR analysis, moment calculations and diagnostics for common departures
from ideal MSMPR behavior. They do not replace the existing FCC workbook
regression model.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import exp, factorial, log
from typing import Iterable, Sequence


@dataclass(frozen=True)
class MSMPRFit:
    intercept_ln_n0: float
    slope_per_size: float
    n0: float
    growth_rate_size_per_time: float
    nucleation_rate_number_per_volume_time: float
    characteristic_size: float
    r_squared: float

    def to_dict(self):
        return asdict(self)


def population_density_from_bins(
    lower_edges: Sequence[float],
    upper_edges: Sequence[float],
    particle_counts: Sequence[float],
    sample_volume: float = 1.0,
) -> list[dict[str, float]]:
    """Convert binned particle counts to population density n = dN/dL.

    Returned density has units of number / sample-volume / size-unit when the
    supplied counts are absolute particle numbers in ``sample_volume``.
    """
    if not (len(lower_edges) == len(upper_edges) == len(particle_counts)):
        raise ValueError("Population-density bin arrays must have equal length.")
    if sample_volume <= 0:
        raise ValueError("Sample volume must be positive.")
    rows = []
    for lo, hi, count in zip(lower_edges, upper_edges, particle_counts):
        width = float(hi) - float(lo)
        if width <= 0 or count < 0:
            raise ValueError("Each size bin must have positive width and nonnegative count.")
        rows.append({
            "lower_size": float(lo),
            "upper_size": float(hi),
            "representative_size": 0.5 * (float(lo) + float(hi)),
            "bin_width": width,
            "count": float(count),
            "population_density": float(count) / sample_volume / width,
        })
    return rows


def distribution_moment(rows: Sequence[dict[str, float]], order: int) -> float:
    """Numerically integrate the j-th CSD moment m_j = integral L^j n(L)dL."""
    if order < 0:
        raise ValueError("Moment order cannot be negative.")
    return sum(
        (r["representative_size"] ** order) * r["population_density"] * r["bin_width"]
        for r in rows
    )


def moments(rows: Sequence[dict[str, float]], maximum_order: int = 4) -> dict[int, float]:
    return {j: distribution_moment(rows, j) for j in range(maximum_order + 1)}


def moment_mean_size(moment_values: dict[int, float], numerator_order: int, denominator_order: int) -> float:
    """Return a moment-ratio mean size, e.g. L_43 = m4/m3."""
    den = moment_values[denominator_order]
    if den <= 0:
        return 0.0
    return moment_values[numerator_order] / den


def msmpr_population_density(size: float, n0: float, growth_rate: float, residence_time: float) -> float:
    """Ideal steady MSMPR CSD: n(L)=n0 exp[-L/(G tau)]."""
    if min(n0, growth_rate, residence_time) <= 0 or size < 0:
        raise ValueError("MSMPR n0, G and residence time must be positive and size nonnegative.")
    return n0 * exp(-size / (growth_rate * residence_time))


def msmpr_theoretical_moment(order: int, n0: float, growth_rate: float, residence_time: float) -> float:
    """Analytical ideal-MSMPR moment for size-independent growth."""
    if order < 0:
        raise ValueError("Moment order cannot be negative.")
    scale = growth_rate * residence_time
    return factorial(order) * n0 * (scale ** (order + 1))


def fit_msmpr(sizes: Sequence[float], densities: Sequence[float], residence_time: float) -> MSMPRFit:
    """Infer effective G and B0 from a semilog population-density plot.

    For the ideal mixed-suspension mixed-product-removal crystallizer,
    ln n = ln n0 - L/(G tau), so G follows from the slope and B0=n0*G.
    Curvature or poor R^2 should be treated as evidence that ideal MSMPR
    assumptions do not hold.
    """
    if len(sizes) != len(densities) or len(sizes) < 2:
        raise ValueError("At least two paired size/density points are required.")
    if residence_time <= 0 or any(d <= 0 for d in densities):
        raise ValueError("Residence time and population densities must be positive.")
    xs = [float(x) for x in sizes]
    ys = [log(float(y)) for y in densities]
    xbar = sum(xs) / len(xs)
    ybar = sum(ys) / len(ys)
    sxx = sum((x - xbar) ** 2 for x in xs)
    if sxx <= 0:
        raise ValueError("Size values must not all be identical.")
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sxx
    intercept = ybar - slope * xbar
    if slope >= 0:
        raise ValueError("Ideal MSMPR semilog slope must be negative.")
    predicted = [intercept + slope * x for x in xs]
    sse = sum((y - p) ** 2 for y, p in zip(ys, predicted))
    sst = sum((y - ybar) ** 2 for y in ys)
    r2 = 1.0 if sst == 0 else 1.0 - sse / sst
    growth = -1.0 / (slope * residence_time)
    n0 = exp(intercept)
    return MSMPRFit(
        intercept_ln_n0=intercept,
        slope_per_size=slope,
        n0=n0,
        growth_rate_size_per_time=growth,
        nucleation_rate_number_per_volume_time=n0 * growth,
        characteristic_size=growth * residence_time,
        r_squared=r2,
    )


def msmpr_diagnostic(sizes: Sequence[float], densities: Sequence[float], residence_time: float) -> dict[str, object]:
    """Screen whether a measured CSD behaves like a simple ideal MSMPR.

    A low linear-fit R² or strong local-slope variation is not assigned to one
    mechanism automatically. It flags candidate effects including size-dependent
    growth, growth-rate dispersion, agglomeration, breakage/classification,
    non-ideal mixing, and time variation.
    """
    fit = fit_msmpr(sizes, densities, residence_time)
    local_slopes = []
    for i in range(len(sizes) - 1):
        dx = float(sizes[i + 1]) - float(sizes[i])
        if dx == 0:
            continue
        local_slopes.append((log(float(densities[i + 1])) - log(float(densities[i]))) / dx)
    spread = 0.0
    if local_slopes:
        mean_abs = sum(abs(x) for x in local_slopes) / len(local_slopes)
        spread = 0.0 if mean_abs == 0 else (max(local_slopes) - min(local_slopes)) / mean_abs
    ideal = fit.r_squared >= 0.995 and abs(spread) <= 0.25
    return {
        "ideal_msmpr_consistent": ideal,
        "fit": fit.to_dict(),
        "local_slope_spread_index": spread,
        "candidate_nonideal_mechanisms": [] if ideal else [
            "size-dependent growth",
            "growth-rate dispersion",
            "agglomeration",
            "breakage or attrition",
            "classification or fines destruction",
            "non-ideal mixing or transient operation",
        ],
    }


def population_balance_capabilities() -> dict[str, object]:
    return {
        "status": "foundation / not yet coupled to FCC production calculation",
        "implemented": [
            "binned count to population-density conversion",
            "CSD moments and moment-ratio mean sizes",
            "ideal steady MSMPR population density",
            "MSMPR effective growth-rate and nucleation-rate inference",
            "ideal MSMPR analytical moments",
            "non-ideal CSD diagnostics",
        ],
        "reserved": [
            "size-dependent growth population balance",
            "growth-rate dispersion model",
            "agglomeration birth/death kernels",
            "breakage/disruption kernels",
            "classification and fines-destruction functions",
            "transient population balance",
            "multispecies/polymorph population balances",
            "coupling to antiscalant-modified nucleation/growth",
        ],
        "principle": "Do not force curved CSD data into a straight-line MSMPR fit and call it validated kinetics.",
    }
