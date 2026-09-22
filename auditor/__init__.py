
"""Public deterministic math-and-data API for the Sustainable AI auditor."""

from .architectures import (
    ARCHITECTURES, Architecture, LOGISTIC_REGRESSION, SMALL_CNN,
    SMALL_RANDOM_FOREST, SMALL_TRANSFORMER, get_architecture_by_name,
    get_architectures,
)
from .lifecycle_math import (
    DEFAULT_CARBON_INTENSITY_GCO2_PER_KWH,
    DEFAULT_HARDWARE_EMBODIED_CARBON_KG,
    DEFAULT_HARDWARE_LIFETIME_HOURS,
    DEFAULT_HARDWARE_UTILIZATION,
    DEFAULT_NETWORK_ENERGY_KWH_PER_GB,
    Workload,
    calculate_carbon,
    calculate_energy,
    calculate_hardware,
    calculate_lifecycle_impact,
    calculate_networking,
    calculate_retraining,
    calculate_storage,
    compare_architectures,
)

__all__ = [
    "ARCHITECTURES", "Architecture", "Workload", "LOGISTIC_REGRESSION",
    "SMALL_RANDOM_FOREST", "SMALL_CNN", "SMALL_TRANSFORMER",
    "DEFAULT_CARBON_INTENSITY_GCO2_PER_KWH",
    "DEFAULT_HARDWARE_EMBODIED_CARBON_KG", "DEFAULT_HARDWARE_LIFETIME_HOURS",
    "DEFAULT_HARDWARE_UTILIZATION", "DEFAULT_NETWORK_ENERGY_KWH_PER_GB",
    "calculate_carbon",
    "calculate_energy", "calculate_hardware", "calculate_lifecycle_impact",
    "calculate_networking", "calculate_retraining", "calculate_storage",
    "compare_architectures", "get_architecture_by_name", "get_architectures",
]
