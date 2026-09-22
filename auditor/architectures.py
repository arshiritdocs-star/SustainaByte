"""Deterministic architecture presets for the lifecycle calculator.

The values are illustrative demo profiles, not benchmark measurements.
Accuracy is represented as a fraction.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Final, Optional, Tuple


def _finite_non_negative(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        raise ValueError(f"{field_name} must be a finite non-negative number.")


@dataclass(frozen=True, slots=True)
class Architecture:
    """Immutable model profile used by deterministic lifecycle calculations."""

    name: str
    model_type: str
    parameter_count: int
    model_size_mb: float
    estimated_accuracy: float
    estimated_latency_ms: float
    training_compute: float
    inference_compute: float
    memory_requirement_mb: float
    retraining_frequency: int
    hardware_requirement: str

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (self.name, self.model_type, self.hardware_requirement)):
            raise ValueError("name, model_type, and hardware_requirement must be non-empty strings.")
        if isinstance(self.parameter_count, bool) or not isinstance(self.parameter_count, int) or self.parameter_count < 0:
            raise ValueError("parameter_count must be a non-negative integer.")
        if isinstance(self.retraining_frequency, bool) or not isinstance(self.retraining_frequency, int) or self.retraining_frequency < 0:
            raise ValueError("retraining_frequency must be a non-negative integer.")
        for field_name in ("model_size_mb", "estimated_accuracy", "estimated_latency_ms", "training_compute", "inference_compute", "memory_requirement_mb"):
            _finite_non_negative(getattr(self, field_name), field_name)
        if self.estimated_accuracy > 1:
            raise ValueError("estimated_accuracy must be a fraction in [0, 1].")

    @property
    def retraining_frequency_per_year(self) -> int:
        """Alias which makes the cadence's time basis explicit."""
        return self.retraining_frequency


LOGISTIC_REGRESSION: Final = Architecture("Logistic Regression / Linear Model", "linear", 1_000, 0.05, 0.78, 2.0, 1.0, 1.0, 16.0, 12, "cpu")
SMALL_RANDOM_FOREST: Final = Architecture("Small Random Forest", "tree_ensemble", 50_000, 5.0, 0.85, 8.0, 5.0, 3.0, 128.0, 6, "cpu")
SMALL_CNN: Final = Architecture("Small CNN", "cnn", 2_000_000, 8.0, 0.91, 25.0, 50.0, 15.0, 512.0, 4, "small_gpu")
SMALL_TRANSFORMER: Final = Architecture("Small Transformer", "transformer", 25_000_000, 100.0, 0.94, 60.0, 400.0, 80.0, 4_096.0, 2, "large_gpu")

ARCHITECTURES: Final[Tuple[Architecture, ...]] = (LOGISTIC_REGRESSION, SMALL_RANDOM_FOREST, SMALL_CNN, SMALL_TRANSFORMER)


def get_architectures() -> Tuple[Architecture, ...]:
    """Return exactly four presets in deterministic comparison order."""
    return ARCHITECTURES


def get_architecture_by_name(name: str) -> Optional[Architecture]:
    """Return a preset by case-insensitive name, or ``None`` if absent."""
    if not isinstance(name, str):
        return None
    normalized_name = name.strip().casefold()
    return next((item for item in ARCHITECTURES if item.name.casefold() == normalized_name), None)


def get_architectures():
    """Return all available architecture presets."""
    return ARCHITECTURES
