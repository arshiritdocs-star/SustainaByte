"""
Lifecycle impact calculations for the Sustainable AI Lifecycle Auditor.

All values are estimates intended for scenario analysis.
They are not direct measurements of a production system.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class Workload:
    """
    Description of an AI workload.
    """

    training_hours: float = 0.0
    training_power_watts: float = 300.0

    inference_count: int = 0

    dataset_size_gb: float = 1.0

    network_transfer_gb: float = 0.0

    replication_factor: int = 2

    storage_duration_years: float = 1.0

    carbon_intensity_gco2_per_kwh: float = 450.0

    hardware_lifetime_hours: float = 4 * 365 * 24.0

    hardware_utilization: float = 0.5

    retraining_runs: Optional[int] = None

    retraining_training_hours: float = 0.0

    checkpoints_per_retraining_run: int = 1

    deployment_nodes: int = 1

    network_energy_kwh_per_gb: float = 0.05

    inference_payload_gb_per_request: float = 0.00005

    pue: float = 1.4


def _safe_positive(value: float) -> float:
    """
    Prevent negative values from entering calculations.
    """

    return max(0.0, float(value))


def calculate_training_energy(
    architecture,
    workload: Workload
) -> float:
    """
    Estimate training energy in kWh.
    """

    training_hours = _safe_positive(
        workload.training_hours
    )

    base_power_kw = (
        _safe_positive(workload.training_power_watts)
        / 1000.0
    )

    return (
        training_hours
        * base_power_kw
        * architecture.training_compute
        * workload.pue
    )


def calculate_inference_energy(
    architecture,
    workload: Workload
) -> float:
    """
    Estimate inference energy in kWh.

    The architecture's inference_compute value is
    treated as a relative compute multiplier.
    """

    requests = max(
        0,
        int(workload.inference_count)
    )

    # Base energy per request in kWh.
    base_energy_per_request = 0.000001

    return (
        requests
        * base_energy_per_request
        * architecture.inference_compute
        * workload.pue
    )


def calculate_storage_impact(
    architecture,
    workload: Workload
) -> float:
    """
    Estimate storage footprint in GB-hours.

    Storage includes the dataset and model replicas.
    """

    dataset_size = _safe_positive(
        workload.dataset_size_gb
    )

    model_size = _safe_positive(
        architecture.model_size_mb
    ) / 1024.0

    replication = max(
        1,
        int(workload.replication_factor)
    )

    storage_duration_hours = (
        _safe_positive(workload.storage_duration_years)
        * 365.0
        * 24.0
    )

    total_storage_gb = (
        dataset_size
        + model_size
    ) * replication

    return (
        total_storage_gb
        * storage_duration_hours
    )


def calculate_networking_energy(
    architecture,
    workload: Workload
) -> float:
    """
    Estimate networking energy in kWh.
    """

    requests = max(
        0,
        int(workload.inference_count)
    )

    payload_gb = _safe_positive(
        workload.inference_payload_gb_per_request
    )

    explicit_transfer = _safe_positive(
        workload.network_transfer_gb
    )

    inference_transfer = (
        requests
        * payload_gb
    )

    total_transfer_gb = (
        explicit_transfer
        + inference_transfer
    )

    return (
        total_transfer_gb
        * _safe_positive(
            workload.network_energy_kwh_per_gb
        )
    )


def calculate_hardware_impact(
    architecture,
    workload: Workload
) -> tuple:
    """
    Estimate hardware energy and carbon contribution.

    Returns:
        hardware_energy_kwh,
        hardware_carbon_kg
    """

    hardware_lifetime = max(
        1.0,
        _safe_positive(
            workload.hardware_lifetime_hours
        )
    )

    utilization = min(
        1.0,
        max(
            0.0,
            _safe_positive(
                workload.hardware_utilization
            )
        )
    )

    memory_gb = (
        _safe_positive(
            architecture.memory_requirement_mb
        ) / 1024.0
    )

    if architecture.hardware_requirement == "large_gpu":
        hardware_power_watts = 500.0

    elif architecture.hardware_requirement == "small_gpu":
        hardware_power_watts = 250.0

    else:
        hardware_power_watts = 100.0

    deployment_nodes = max(
        1,
        int(workload.deployment_nodes)
    )

    hardware_hours = (
        hardware_lifetime
        * utilization
    )

    hardware_energy_kwh = (
        hardware_power_watts
        / 1000.0
        * hardware_hours
        * deployment_nodes
    )

    # Approximate embodied hardware carbon factor.
    hardware_carbon_factor = (
        0.5
        + memory_gb * 0.02
    )

    hardware_carbon_kg = (
        hardware_energy_kwh
        * hardware_carbon_factor
    )

    return (
        hardware_energy_kwh,
        hardware_carbon_kg
    )


def calculate_retraining_energy(
    architecture,
    workload: Workload
) -> float:
    """
    Estimate energy consumed by retraining runs.
    """

    if workload.retraining_runs is None:
        retraining_runs = max(
            0,
            int(architecture.retraining_frequency)
        )
    else:
        retraining_runs = max(
            0,
            int(workload.retraining_runs)
        )

    training_hours = _safe_positive(
        workload.retraining_training_hours
    )

    base_power_kw = (
        _safe_positive(
            workload.training_power_watts
        )
        / 1000.0
    )

    checkpoints = max(
        1,
        int(workload.checkpoints_per_retraining_run)
    )

    return (
        retraining_runs
        * training_hours
        * base_power_kw
        * architecture.training_compute
        * workload.pue
        * checkpoints
    )


def calculate_lifecycle_impact(
    architecture,
    workload: Workload
) -> dict:
    """
    Calculate the estimated lifecycle impact of an architecture.

    Returns a dictionary containing energy, carbon,
    storage, networking, hardware and retraining metrics.
    """

    carbon_factor = (
        _safe_positive(
            workload.carbon_intensity_gco2_per_kwh
        )
        / 1000.0
    )

    training_energy = calculate_training_energy(
        architecture,
        workload
    )

    inference_energy = calculate_inference_energy(
        architecture,
        workload
    )

    networking_energy = calculate_networking_energy(
        architecture,
        workload
    )

    retraining_energy = calculate_retraining_energy(
        architecture,
        workload
    )

    hardware_energy, hardware_carbon = (
        calculate_hardware_impact(
            architecture,
            workload
        )
    )

    storage_impact = calculate_storage_impact(
        architecture,
        workload
    )

    training_carbon = (
        training_energy
        * carbon_factor
    )

    inference_carbon = (
        inference_energy
        * carbon_factor
    )

    networking_carbon = (
        networking_energy
        * carbon_factor
    )

    retraining_carbon = (
        retraining_energy
        * carbon_factor
    )

    total_energy = (
        training_energy
        + inference_energy
        + networking_energy
        + retraining_energy
        + hardware_energy
    )

    total_carbon = (
        training_carbon
        + inference_carbon
        + networking_carbon
        + retraining_carbon
        + hardware_carbon
    )

    return {
        "training_energy_kwh": training_energy,

        "training_carbon_kg": training_carbon,

        "inference_energy_kwh": inference_energy,

        "inference_carbon_kg": inference_carbon,

        "storage_impact_gb_hours": storage_impact,

        "networking_energy_kwh": networking_energy,

        "networking_carbon_kg": networking_carbon,

        "hardware_energy_kwh": hardware_energy,

        "hardware_carbon_kg": hardware_carbon,

        "retraining_energy_kwh": retraining_energy,

        "retraining_carbon_kg": retraining_carbon,

        "total_energy_kwh": total_energy,

        "total_carbon_kg": total_carbon,
    }


def compare_architectures(
    architectures,
    workload: Workload,
    minimum_accuracy: float,
    maximum_latency: float
) -> list:
    """
    Compare a supplied collection of architectures
    against accuracy and latency requirements.
    """

    results = []

    for architecture in architectures:

        impact = calculate_lifecycle_impact(
            architecture=architecture,
            workload=workload
        )

        accuracy_percent = (
            architecture.estimated_accuracy
            * 100.0
        )

        latency_ms = (
            architecture.estimated_latency_ms
        )

        eligible = (
            accuracy_percent >= minimum_accuracy
            and latency_ms <= maximum_latency
        )

        results.append({
            "architecture": architecture,
            "impact": impact,
            "accuracy": accuracy_percent,
            "latency": latency_ms,
            "eligible": eligible,
        })

    return results
