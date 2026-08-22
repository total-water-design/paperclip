"""Temperature/ionic-strength dependent osmotic coefficient model.

The phi(T, I) lookup surface was supplied by the user from prior engineering work.
The raw table contains two I=0.2 rows; both are retained and collapsed by averaging
before interpolation so the interpolation grid is strictly monotonic.

For the present SWRO model, TDS is converted to a NaCl-equivalent ionic strength:
    I ~= (TDS g/L) / MW_NaCl
and osmotic pressure is calculated from a van't Hoff form:
    pi = phi * nu * C * R * T
with nu=2 for NaCl and C in mol/L.

This is a NaCl-equivalent engineering model, not a full multi-ion activity model.
"""
from bisect import bisect_right

R_L_BAR_MOL_K = 0.08314462618
MW_NACL_G_MOL = 58.44277
VANT_HOFF_NACL = 2.0

X_DATA = [
    273.15, 278.15, 283.15, 288.15, 293.15, 298.15, 303.15, 308.15, 313.15, 318.15,
    323.15, 328.15, 333.15, 338.15, 343.15, 348.15, 353.15, 358.15, 363.15, 368.15, 373.15
]
Y_RAW = [0.2,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.2,1.4,1.5,1.6,1.8,2.0,2.5,3.0,3.5,4.0,4.5,5.0,5.5,6.0]
Z_RAW = [
[0.921,0.9219,0.9227,0.9234,0.9239,0.9242,0.9244,0.9244,0.9242,0.9239,0.9235,0.9228,0.9221,0.9211,0.920,0.9187,0.9173,0.9157,0.914,0.9121,0.910],
[0.921,0.922,0.923,0.924,0.924,0.924,0.925,0.924,0.924,0.924,0.924,0.923,0.922,0.921,0.920,0.919,0.917,0.916,0.914,0.912,0.910],
[0.916,0.918,0.919,0.920,0.921,0.922,0.922,0.923,0.923,0.923,0.922,0.922,0.921,0.920,0.919,0.917,0.916,0.914,0.912,0.909,0.907],
[0.914,0.916,0.918,0.920,0.921,0.922,0.923,0.924,0.924,0.924,0.924,0.923,0.922,0.921,0.920,0.918,0.917,0.914,0.912,0.909,0.906],
[0.913,0.915,0.918,0.920,0.922,0.924,0.925,0.926,0.926,0.927,0.927,0.926,0.925,0.924,0.923,0.921,0.919,0.917,0.914,0.911,0.907],
[0.912,0.916,0.919,0.922,0.924,0.926,0.928,0.929,0.930,0.930,0.930,0.930,0.929,0.928,0.927,0.925,0.922,0.920,0.917,0.913,0.910],
[0.913,0.917,0.921,0.924,0.927,0.929,0.931,0.933,0.934,0.934,0.934,0.934,0.933,0.932,0.931,0.929,0.926,0.924,0.920,0.916,0.912],
[0.914,0.919,0.923,0.926,0.930,0.932,0.935,0.937,0.938,0.939,0.939,0.939,0.938,0.937,0.935,0.933,0.931,0.928,0.924,0.920,0.916],
[0.915,0.921,0.925,0.929,0.933,0.936,0.939,0.941,0.942,0.943,0.944,0.944,0.943,0.942,0.940,0.938,0.935,0.932,0.928,0.924,0.919],
[0.917,0.923,0.928,0.933,0.937,0.940,0.943,0.945,0.947,0.948,0.949,0.949,0.948,0.947,0.946,0.943,0.940,0.937,0.933,0.928,0.923],
[0.921,0.928,0.934,0.940,0.945,0.949,0.952,0.955,0.957,0.959,0.960,0.960,0.959,0.958,0.956,0.954,0.951,0.947,0.942,0.937,0.931],
[0.927,0.935,0.942,0.948,0.953,0.958,0.962,0.965,0.968,0.970,0.971,0.971,0.971,0.969,0.967,0.965,0.961,0.957,0.952,0.946,0.940],
[0.930,0.938,0.945,0.952,0.958,0.963,0.967,0.971,0.973,0.975,0.976,0.977,0.976,0.975,0.973,0.970,0.967,0.962,0.957,0.951,0.945],
[0.933,0.942,0.949,0.956,0.963,0.968,0.972,0.976,0.979,0.981,0.982,0.982,0.982,0.981,0.979,0.976,0.972,0.968,0.962,0.956,0.949],
[0.940,0.950,0.958,0.966,0.972,0.978,0.983,0.987,0.990,0.992,0.994,0.994,0.994,0.993,0.990,0.987,0.983,0.979,0.973,0.966,0.959],
[0.948,0.958,0.967,0.975,0.982,0.989,0.994,0.998,1.002,1.004,1.006,1.006,1.006,1.004,1.002,0.999,0.995,0.990,0.984,0.977,0.969],
[0.972,0.983,0.993,1.002,1.010,1.017,1.023,1.027,1.031,1.034,1.036,1.036,1.036,1.034,1.032,1.028,1.024,1.018,1.011,1.004,0.995],
[0.999,1.011,1.022,1.031,1.039,1.047,1.053,1.058,1.062,1.065,1.067,1.067,1.067,1.065,1.062,1.058,1.053,1.047,1.040,1.032,1.022],
[1.031,1.043,1.054,1.063,1.072,1.079,1.085,1.090,1.094,1.096,1.098,1.098,1.098,1.096,1.093,1.089,1.083,1.077,1.069,1.061,1.051],
[1.067,1.079,1.089,1.098,1.106,1.113,1.118,1.123,1.126,1.129,1.130,1.130,1.129,1.127,1.124,1.119,1.114,1.107,1.099,1.091,1.081],
[1.109,1.119,1.128,1.136,1.143,1.149,1.154,1.157,1.160,1.162,1.163,1.162,1.161,1.158,1.155,1.150,1.145,1.138,1.130,1.121,1.112],
[1.154,1.162,1.170,1.176,1.182,1.186,1.190,1.193,1.195,1.196,1.196,1.195,1.193,1.190,1.186,1.181,1.176,1.169,1.162,1.153,1.144],
[1.204,1.210,1.215,1.219,1.223,1.226,1.228,1.230,1.230,1.230,1.229,1.228,1.225,1.222,1.218,1.213,1.207,1.201,1.194,1.186,1.177],
[1.258,1.261,1.263,1.265,1.267,1.268,1.268,1.268,1.267,1.265,1.263,1.261,1.258,1.254,1.250,1.245,1.239,1.233,1.227,1.220,1.212]
]

# Collapse duplicate ionic-strength rows by arithmetic mean.
_unique = {}
for y, row in zip(Y_RAW, Z_RAW):
    _unique.setdefault(y, []).append(row)
Y_DATA = sorted(_unique)
Z_DATA = []
for y in Y_DATA:
    rows = _unique[y]
    Z_DATA.append([sum(vals)/len(vals) for vals in zip(*rows)])


def _linear(x, x0, x1, y0, y1):
    if x1 == x0:
        return y0
    return y0 + (x-x0)*(y1-y0)/(x1-x0)


def _bracket(grid, value):
    if value <= grid[0]:
        return 0, 0
    if value >= grid[-1]:
        return len(grid)-1, len(grid)-1
    hi = bisect_right(grid, value)
    return hi-1, hi


def osmotic_coefficient(temp_k, ionic_strength):
    """Bilinear interpolation of phi(T,I).

    For 0 <= I < 0.2, phi is linearly bridged to the thermodynamic dilute
    limit phi=1 at I=0. Above I=6 or outside the temperature table, the edge
    value is used rather than uncontrolled extrapolation.
    """
    t = float(temp_k)
    i = max(0.0, float(ionic_strength))
    t = min(max(t, X_DATA[0]), X_DATA[-1])

    def phi_at_row(row):
        j0, j1 = _bracket(X_DATA, t)
        if j0 == j1:
            return Z_DATA[row][j0]
        return _linear(t, X_DATA[j0], X_DATA[j1], Z_DATA[row][j0], Z_DATA[row][j1])

    if i < Y_DATA[0]:
        phi02 = phi_at_row(0)
        return _linear(i, 0.0, Y_DATA[0], 1.0, phi02)
    i = min(i, Y_DATA[-1])
    k0, k1 = _bracket(Y_DATA, i)
    p0 = phi_at_row(k0)
    if k0 == k1:
        return p0
    p1 = phi_at_row(k1)
    return _linear(i, Y_DATA[k0], Y_DATA[k1], p0, p1)


def nacl_equivalent_ionic_strength(tds_ppm):
    """Approximate ionic strength (mol/L) treating TDS as NaCl equivalent."""
    g_l = max(0.0, float(tds_ppm)) / 1000.0
    return g_l / MW_NACL_G_MOL


def osmotic_state(tds_ppm, temp_c=25.0, ionic_strength=None):
    """Return NaCl-equivalent osmotic pressure state for TDS and temperature."""
    t_k = float(temp_c) + 273.15
    c = nacl_equivalent_ionic_strength(tds_ppm)
    i = c if ionic_strength is None else max(0.0, float(ionic_strength))
    phi = osmotic_coefficient(t_k, i)
    pi_bar = phi * VANT_HOFF_NACL * c * R_L_BAR_MOL_K * t_k
    return {"osmotic_bar": pi_bar, "phi": phi, "ionic_strength": i, "temp_k": t_k}
