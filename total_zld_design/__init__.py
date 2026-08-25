"""Total ZLD Design commercial-shell engineering preview."""

from .engine import calculate_thermal_legacy, calculate_fo_regression, calculate
from .fo import calculate_fo_engineering, fo_engineering_defaults
from .falling_film_evaporator import (
    falling_film_capabilities,
    falling_film_defaults,
    shahzad_horizontal_saline_ffe_htc,
    size_falling_film_evaporator,
)
from .process_train import (
    add_unit,
    default_process_train,
    move_unit,
    normalize_process_train,
    process_train_advisories,
    process_train_capabilities,
    remove_unit,
)
from .defaults import thermal_defaults, fo_defaults
from .snapshot import build_snapshot
from .solution_properties import saturation_state, solution_property_capabilities
from .crystal_kinetics import crystal_kinetics_capabilities
from .crystallization_inhibitors import crystallizer_inhibitor_capabilities
from .population_balance import population_balance_capabilities
from .crystallizer_design import (
    crystallizer_design_capabilities,
    ideal_msmpr_residence_time_h,
    recommend_crystallizer_types,
    size_ideal_msmpr,
)

__all__ = [
    "calculate",
    "calculate_thermal_legacy",
    "calculate_fo_regression",
    "calculate_fo_engineering",
    "size_falling_film_evaporator",
    "shahzad_horizontal_saline_ffe_htc",
    "falling_film_defaults",
    "falling_film_capabilities",
    "thermal_defaults",
    "fo_defaults",
    "fo_engineering_defaults",
    "build_snapshot",
    "saturation_state",
    "solution_property_capabilities",
    "crystal_kinetics_capabilities",
    "crystallizer_inhibitor_capabilities",
    "population_balance_capabilities",
    "crystallizer_design_capabilities",
    "ideal_msmpr_residence_time_h",
    "size_ideal_msmpr",
    "recommend_crystallizer_types",
    "default_process_train",
    "normalize_process_train",
    "add_unit",
    "remove_unit",
    "move_unit",
    "process_train_advisories",
    "process_train_capabilities",
]

__version__ = "0.2.0"
