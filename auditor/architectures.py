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


CLOUD_MONOLITH: Final = Architecture(
    name="Cloud Monolith 70B FP16", 
    model_type="transformer", 
    parameter_count=70_000_000_000, 
    model_size_mb=140_000.0, 
    estimated_accuracy=0.942, 
    estimated_latency_ms=185.0, 
    training_compute=10000.0, 
    inference_compute=500.0, 
    memory_requirement_mb=160_000.0, 
    retraining_frequency=12, 
    hardware_requirement="multi_gpu"
)

QUANTIZED_LORA: Final = Architecture(
    name="Quantized Core 8B INT4 + LoRA", 
    model_type="transformer_lora", 
    parameter_count=8_000_000_000, 
    model_size_mb=5_000.0, 
    estimated_accuracy=0.911, 
    estimated_latency_ms=42.0, 
    training_compute=50.0,       # Significantly lower due to LoRA
    inference_compute=80.0, 
    memory_requirement_mb=8_192.0, 
    retraining_frequency=12, 
    hardware_requirement="single_gpu"
)

DISTILLED_CORE: Final = Architecture(
    name="Distilled 1.5B INT8", 
    model_type="transformer", 
    parameter_count=1_500_000_000, 
    model_size_mb=2_000.0, 
    estimated_accuracy=0.84, 
    estimated_latency_ms=22.0, 
    training_compute=20.0, 
    inference_compute=25.0, 
    memory_requirement_mb=4_096.0, 
    retraining_frequency=4, 
    hardware_requirement="small_gpu"
)

EDGE_MICRO: Final = Architecture(
    name="Edge Micro 0.5B ONNX", 
    model_type="tiny_transformer", 
    parameter_count=500_000_000, 
    model_size_mb=500.0, 
    estimated_accuracy=0.785, 
    estimated_latency_ms=12.0, 
    training_compute=10.0, 
    inference_compute=5.0, 
    memory_requirement_mb=1_024.0, 
    retraining_frequency=2, 
    hardware_requirement="npu"
)

ARCHITECTURES: Final[Tuple[Architecture, ...]] = (CLOUD_MONOLITH, QUANTIZED_LORA, DISTILLED_CORE, EDGE_MICRO)


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
