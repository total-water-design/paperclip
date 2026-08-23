"""Public calculation API."""

from .thermal_legacy import calculate_thermal_legacy
from .fo_regression import calculate_fo_regression


def calculate(mode: str, inputs=None):
    mode = (mode or "").strip().lower()
    if mode in {"thermal", "thermal_legacy", "mzld", "legacy"}:
        return calculate_thermal_legacy(inputs)
    if mode in {"fo", "fo_regression", "forward_osmosis"}:
        return calculate_fo_regression(inputs)
    raise ValueError(f"Unsupported Total ZLD Design mode: {mode!r}")
