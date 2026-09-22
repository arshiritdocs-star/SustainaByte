"""
Architecture definitions for the Sustainable AI Auditor.
"""

from dataclasses import dataclass
from typing import Final, Tuple


@dataclass(frozen=True, slots=True)
class Architecture:
    name: str
    model_type: str
    parameter_count: int
    model_size_mb: float
    estimated_accuracy: float
    estimated_latency_ms: float

    # Relative compute units.
    training_compute: float
    inference_compute: float

    memory_requirement_mb: float
    retraining_frequency: int
    hardware_requirement: str


LOGISTIC_REGRESSION = Architecture(
    name="Logistic Regression / Linear Model",
    model_type="linear",
    parameter_count=1_000,
    model_size_mb=0.05,
    estimated_accuracy=0.78,
    estimated_latency_ms=2.0,
    training_compute=1.0,
    inference_compute=1.0,
    memory_requirement_mb=16.0,
    retraining_frequency=12,
    hardware_requirement="cpu",
)


SMALL_RANDOM_FOREST = Architecture(
    name="Small Random Forest",
    model_type="tree_ensemble",
    parameter_count=50_000,
    model_size_mb=5.0,
    estimated_accuracy=0.85,
    estimated_latency_ms=8.0,
    training_compute=5.0,
    inference_compute=5.0,
    memory_requirement_mb=128.0,
    retraining_frequency=6,
    hardware_requirement="cpu",
)


SMALL_CNN = Architecture(
    name="Small CNN",
    model_type="cnn",
    parameter_count=2_000_000,
    model_size_mb=8.0,
    estimated_accuracy=0.91,
    estimated_latency_ms=25.0,
    training_compute=50.0,
    inference_compute=15.0,
    memory_requirement_mb=512.0,
    retraining_frequency=4,
    hardware_requirement="small_gpu",
)


SMALL_TRANSFORMER = Architecture(
    name="Small Transformer",
    model_type="transformer",
    parameter_count=25_000_000,
    model_size_mb=100.0,
    estimated_accuracy=0.94,
    estimated_latency_ms=60.0,
    training_compute=400.0,
    inference_compute=80.0,
    memory_requirement_mb=4_096.0,
    retraining_frequency=2,
    hardware_requirement="large_gpu",
)


ARCHITECTURES: Final[Tuple[Architecture, ...]] = (
    LOGISTIC_REGRESSION,
    SMALL_RANDOM_FOREST,
    SMALL_CNN,
    SMALL_TRANSFORMER,
)


def get_architectures() -> Tuple[Architecture, ...]:
    """Return all four architecture presets."""
    return ARCHITECTURES


def get_architecture_by_name(name: str) -> Architecture:
    """Return an architecture by its display name."""
    for architecture in ARCHITECTURES:
        if architecture.name == name:
            return architecture

    raise ValueError(f"Unknown architecture: {name}")
