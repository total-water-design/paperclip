"""Public calculation API."""

from .thermal_legacy import calculate_thermal_legacy
from .fo_regression import calculate_fo_regression
from .fo import calculate_fo_engineering
from .falling_film_evaporator import size_falling_film_evaporator


def calculate(mode: str, inputs=None):
    mode = (mode or "").strip().lower()
    if mode in {"thermal", "thermal_legacy", "mzld", "legacy"}:
        return calculate_thermal_legacy(inputs)
    if mode in {"fo", "fo_regression", "forward_osmosis"}:
        return calculate_fo_regression(inputs)
    if mode in {"fo_engineering", "industrial_fo", "pafo"}:
        return calculate_fo_engineering(inputs)
    if mode in {"falling_film", "falling_film_evaporator", "ffe", "vffe_design"}:
        return size_falling_film_evaporator(inputs)
    raise ValueError(f"Unsupported Total ZLD Design mode: {mode!r}")
