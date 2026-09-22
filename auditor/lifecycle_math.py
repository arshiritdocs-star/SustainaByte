"""
Deterministic lifecycle calculations for the Sustainable AI Auditor.

The six lifecycle pillars are:

1. Energy
2. Carbon
3. Storage
4. Networking
5. Hardware
6. Retraining

All calculations are architecture-specific.
"""

from dataclasses import dataclass
from math import isfinite
from typing import Dict, List, Mapping, Optional

from auditor.architectures import Architecture, get_architectures


DEFAULT_CARBON_INTENSITY_GCO2_PER_KWH = 450.0
DEFAULT_HARDWARE_LIFETIME_HOURS = 4 * 365 * 24.0
DEFAULT_NETWORK_ENERGY_KWH_PER_GB = 0.05


@dataclass(frozen=True, slots=True)
class Workload:
    """Audited workload inputs."""

    training_hours: float = 0.0
    training_power_watts: float = 300.0

    inference_count: int = 0

    dataset_size_gb: float = 1.0

    network_transfer_gb: float = 0.0

    replication_factor: int = 2
    storage_duration_years: float = 1.0

    carbon_intensity_gco2_per_kwh: float = (
        DEFAULT_CARBON_INTENSITY_GCO2_PER_KWH
    )

    hardware_lifetime_hours: float = DEFAULT_HARDWARE_LIFETIME_HOURS
    hardware_utilization: float = 0.5

    retraining_runs: Optional[int] = None
    retraining_training_hours: float = 0.0
    checkpoints_per_retraining_run: int = 1

    deployment_nodes: int = 1

    network_energy_kwh_per_gb: float = DEFAULT_NETWORK_ENERGY_KWH_PER_GB

    # Data transferred per inference request.
    inference_payload_gb_per_request: float = 0.00005

    # Data-centre overhead.
    pue: float = 1.4


def _validate_workload(workload: Workload) -> None:

    if not isinstance(workload, Workload):
        raise TypeError("workload must be a Workload instance.")

    floats = (
        "training_hours",
        "training_power_watts",
        "dataset_size_gb",
        "network_transfer_gb",
        "storage_duration_years",
        "carbon_intensity_gco2_per_kwh",
        "hardware_lifetime_hours",
        "hardware_utilization",
        "retraining_training_hours",
        "network_energy_kwh_per_gb",
        "inference_payload_gb_per_request",
        "pue",
    )

    for name in floats:

        value = getattr(workload, name)

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a finite non-negative number."
            )

    for name in (
        "inference_count",
        "replication_factor",
        "checkpoints_per_retraining_run",
        "deployment_nodes",
    ):

        value = getattr(workload, name)

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a non-negative integer."
            )

    if workload.retraining_runs is not None:

        value = workload.retraining_runs

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                "retraining_runs must be a non-negative integer or None."
            )

    if workload.hardware_lifetime_hours <= 0:
        raise ValueError(
            "hardware_lifetime_hours must be greater than zero."
        )

    if not 0 < workload.hardware_utilization <= 1:
        raise ValueError(
            "hardware_utilization must be in (0, 1]."
        )

    if workload.pue < 1:
        raise ValueError("pue must be at least 1.0.")


def _runs(
    architecture: Architecture,
    workload: Workload
) -> int:

    if workload.retraining_runs is not None:
        return workload.retraining_runs

    return architecture.retraining_frequency


# ============================================================
# NETWORKING
# ============================================================

def calculate_networking(
    architecture: Architecture,
    workload: Workload
) -> Dict[str, float]:

    _validate_workload(workload)

    retraining_runs = _runs(architecture, workload)

    dataset_transfer = workload.dataset_size_gb

    retraining_transfer = (
        workload.dataset_size_gb
        * retraining_runs
    )

    model_distribution = (
        architecture.model_size_mb / 1024
        * workload.deployment_nodes
    )

    replication_network = (
        workload.dataset_size_gb
        * max(0, workload.replication_factor - 1)
    )

    inference_traffic = (
        workload.inference_count
        * workload.inference_payload_gb_per_request
    )

    other_network = workload.network_transfer_gb

    total_network_gb = (
        dataset_transfer
        + retraining_transfer
        + model_distribution
        + replication_network
        + inference_traffic
        + other_network
    )

    network_energy = (
        total_network_gb
        * workload.network_energy_kwh_per_gb
        * workload.pue
    )

    return {
        "dataset_transfer_gb": dataset_transfer,
        "retraining_dataset_transfer_gb": retraining_transfer,
        "model_distribution_gb": model_distribution,
        "replication_network_gb": replication_network,
        "inference_traffic_gb": inference_traffic,
        "other_network_gb": other_network,
        "total_network_gb": total_network_gb,
        "network_energy_kwh": network_energy,
    }


# ============================================================
# ENERGY
# ============================================================

def calculate_energy(
    architecture: Architecture,
    workload: Workload
) -> Dict[str, float]:

    _validate_workload(workload)

    # Training energy.
    training_energy = (
        workload.training_hours
        * workload.training_power_watts
        / 1000
        * workload.pue
    )

    # Architecture-specific inference energy.
    #
    # 1 compute unit = 0.02 Wh/request.
    # Therefore:
    #
    # Logistic Regression = 0.02 Wh/request
    # Random Forest       = 0.10 Wh/request
    # CNN                 = 0.30 Wh/request
    # Transformer         = 1.60 Wh/request
    #
    inference_energy_per_request_wh = (
        architecture.inference_compute * 0.02
    )

    inference_energy = (
        workload.inference_count
        * inference_energy_per_request_wh
        / 1000
        * workload.pue
    )

    # Architecture-specific retraining.
    retraining_runs = _runs(
        architecture,
        workload
    )

    retraining_energy = (
        retraining_runs
        * workload.retraining_training_hours
        * workload.training_power_watts
        / 1000
        * workload.pue
        * (architecture.training_compute / 10)
    )

    networking_energy = calculate_networking(
        architecture,
        workload
    )["network_energy_kwh"]

    total_energy = (
        training_energy
        + inference_energy
        + retraining_energy
        + networking_energy
    )

    return {
        "training_energy_kwh": training_energy,
        "inference_energy_kwh": inference_energy,
        "inference_energy_per_request_wh":
            inference_energy_per_request_wh,
        "retraining_energy_kwh": retraining_energy,
        "networking_energy_kwh": networking_energy,
        "total_energy_kwh": total_energy,
    }


# ============================================================
# HARDWARE
# ============================================================

def calculate_hardware(
    architecture: Architecture,
    workload: Workload
) -> Dict[str, float]:

    _validate_workload(workload)

    retraining_runs = _runs(
        architecture,
        workload
    )

    inference_hours = (
        workload.inference_count
        * architecture.estimated_latency_ms
        / 3_600_000
    )

    active_hours = (
        workload.training_hours
        + retraining_runs
        * workload.retraining_training_hours
        + inference_hours
    )

    lifetime_share = min(
        1.0,
        active_hours
        / (
            workload.hardware_lifetime_hours
            * workload.hardware_utilization
        )
    )

    # Architecture-specific hardware embodied carbon.
    #
    # Based on relative memory / hardware requirement.
    hardware_base_carbon = {
        "cpu": 80.0,
        "small_gpu": 300.0,
        "large_gpu": 700.0,
    }

    base_carbon = hardware_base_carbon.get(
        architecture.hardware_requirement,
        150.0
    )

    # Scale modestly with memory requirement.
    memory_scale = max(
        1.0,
        architecture.memory_requirement_mb / 256.0
    )

    architecture_embodied_carbon = (
        base_carbon
        * (0.5 + 0.5 * min(memory_scale, 4.0))
    )

    embodied_carbon = (
        architecture_embodied_carbon
        * lifetime_share
    )

    return {
        "active_hardware_hours": active_hours,
        "hardware_power_watts": (
            workload.training_power_watts
        ),
        "memory_requirement_mb": (
            architecture.memory_requirement_mb
        ),
        "lifetime_share": lifetime_share,
        "base_hardware_embodied_carbon_kg":
            architecture_embodied_carbon,
        "embodied_carbon_kg": embodied_carbon,
    }


# ============================================================
# CARBON
# ============================================================

def calculate_carbon(
    architecture: Architecture,
    workload: Workload,
    energy: Optional[Mapping[str, float]] = None
) -> Dict[str, float]:

    _validate_workload(workload)

    values = (
        calculate_energy(
            architecture,
            workload
        )
        if energy is None
        else energy
    )

    total_energy = values.get(
        "total_energy_kwh"
    )

    if (
        isinstance(total_energy, bool)
        or not isinstance(total_energy, (int, float))
        or not isfinite(total_energy)
        or total_energy < 0
    ):
        raise ValueError(
            "energy must contain finite, non-negative "
            "total_energy_kwh."
        )

    hardware = calculate_hardware(
        architecture,
        workload
    )

    operational_carbon = (
        total_energy
        * workload.carbon_intensity_gco2_per_kwh
        / 1000
    )

    embodied_carbon = (
        hardware["embodied_carbon_kg"]
    )

    return {
        "operational_carbon_kg": operational_carbon,
        "embodied_carbon_kg": embodied_carbon,
        "total_carbon_kg": (
            operational_carbon
            + embodied_carbon
        ),
        "lifetime_share": hardware["lifetime_share"],
    }


# ============================================================
# STORAGE
# ============================================================

def calculate_storage(
    architecture: Architecture,
    workload: Workload
) -> Dict[str, float]:

    _validate_workload(workload)

    model_gb = (
        architecture.model_size_mb / 1024
    )

    retraining_runs = _runs(
        architecture,
        workload
    )

    checkpoints = (
        retraining_runs
        * workload.checkpoints_per_retraining_run
    )

    dataset_storage = (
        workload.dataset_size_gb
        * workload.replication_factor
    )

    model_storage = (
        model_gb
        * workload.deployment_nodes
    )

    checkpoint_storage = (
        model_gb
        * checkpoints
    )

    total_storage = (
        dataset_storage
        + model_storage
        + checkpoint_storage
    )

    return {
        "dataset_storage_gb": dataset_storage,
        "model_storage_gb": model_storage,
        "checkpoint_storage_gb": checkpoint_storage,
        "number_of_checkpoints": float(checkpoints),
        "total_storage_gb": total_storage,
        "storage_duration_years":
            float(workload.storage_duration_years),
    }


# ============================================================
# RETRAINING
# ============================================================

def calculate_retraining(
    architecture: Architecture,
    workload: Workload
) -> Dict[str, float]:

    _validate_workload(workload)

    runs = _runs(
        architecture,
        workload
    )

    energy = calculate_energy(
        architecture,
        workload
    )

    network = calculate_networking(
        architecture,
        workload
    )

    retraining_carbon = (
        energy["retraining_energy_kwh"]
        * workload.carbon_intensity_gco2_per_kwh
        / 1000
    )

    checkpoint_storage = (
        architecture.model_size_mb / 1024
        * runs
        * workload.checkpoints_per_retraining_run
    )

    return {
        "retraining_runs": float(runs),
        "retraining_energy_kwh":
            energy["retraining_energy_kwh"],
        "retraining_carbon_kg":
            retraining_carbon,
        "retraining_storage_gb":
            checkpoint_storage,
        "retraining_network_gb":
            network["retraining_dataset_transfer_gb"],
    }


# ============================================================
# COMPLETE LIFECYCLE
# ============================================================

def calculate_lifecycle_impact(
    architecture: Architecture,
    workload: Workload
) -> Dict[str, object]:

    if not isinstance(
        architecture,
        Architecture
    ):
        raise TypeError(
            "architecture must be an Architecture instance."
        )

    energy = calculate_energy(
        architecture,
        workload
    )

    carbon = calculate_carbon(
        architecture,
        workload,
        energy
    )

    storage = calculate_storage(
        architecture,
        workload
    )

    networking = calculate_networking(
        architecture,
        workload
    )

    hardware = calculate_hardware(
        architecture,
        workload
    )

    retraining = calculate_retraining(
        architecture,
        workload
    )

    return {
        "architecture": architecture.name,
        "energy": energy,
        "carbon": carbon,
        "storage": storage,
        "networking": networking,
        "hardware": hardware,
        "retraining": retraining,
        "total_lifecycle_carbon_kg":
            carbon["total_carbon_kg"],
    }


# ============================================================
# ARCHITECTURE COMPARISON
# ============================================================

def compare_architectures(
    workload: Workload,
    minimum_accuracy: float = 0.0,
    maximum_latency_ms: Optional[float] = None
) -> List[Dict[str, object]]:

    if (
        isinstance(minimum_accuracy, bool)
        or not isinstance(
            minimum_accuracy,
            (int, float)
        )
        or not isfinite(minimum_accuracy)
        or not 0 <= minimum_accuracy <= 1
    ):
        raise ValueError(
            "minimum_accuracy must be finite "
            "and in [0, 1]."
        )

    if (
        maximum_latency_ms is not None
        and (
            isinstance(
                maximum_latency_ms,
                bool
            )
            or not isinstance(
                maximum_latency_ms,
                (int, float)
            )
            or not isfinite(
                maximum_latency_ms
            )
            or maximum_latency_ms < 0
        )
    ):
        raise ValueError(
            "maximum_latency_ms must be finite, "
            "non-negative, or None."
        )

    results = []

    for architecture in get_architectures():

        accuracy_ok = (
            architecture.estimated_accuracy
            >= minimum_accuracy
        )

        latency_ok = (
            maximum_latency_ms is None
            or architecture.estimated_latency_ms
            <= maximum_latency_ms
        )

        results.append(
            {
                "architecture": architecture,
                "feasible":
                    accuracy_ok and latency_ok,
                "accuracy_constraint_met":
                    accuracy_ok,
                "latency_constraint_met":
                    latency_ok,
                "impact":
                    calculate_lifecycle_impact(
                        architecture,
                        workload
                    ),
            }
        )

    return results
