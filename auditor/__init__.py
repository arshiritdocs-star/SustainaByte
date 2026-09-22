"""
Public API for the Sustainable AI Lifecycle Auditor.
"""

from .architectures import (
    ARCHITECTURES,
    Architecture,
    LOGISTIC_REGRESSION,
    SMALL_CNN,
    SMALL_RANDOM_FOREST,
    SMALL_TRANSFORMER,
    get_architecture_by_name,
    get_architectures,
    get_candidate_architectures,
)

from .lifecycle_math import (
    Workload,
    calculate_lifecycle_impact,
    compare_architectures,
)


__all__ = [
    "ARCHITECTURES",
    "Architecture",
    "Workload",

    "LOGISTIC_REGRESSION",
    "SMALL_RANDOM_FOREST",
    "SMALL_CNN",
    "SMALL_TRANSFORMER",

    "calculate_lifecycle_impact",
    "compare_architectures",

    "get_architecture_by_name",
    "get_architectures",
    "get_candidate_architectures",
]
