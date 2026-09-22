"""Deterministic, dependency-free six-pillar AI lifecycle calculations.

Operational energy contains training, inference, retraining, and networking
once each. Hardware power is descriptive; hardware's separate pillar amortizes
embodied carbon and is never added to operational energy a second time.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Dict, List, Mapping, Optional

from auditor.architectures import Architecture, get_architectures

DEFAULT_CARBON_INTENSITY_GCO2_PER_KWH = 450.0
DEFAULT_HARDWARE_EMBODIED_CARBON_KG = 150.0
DEFAULT_HARDWARE_LIFETIME_HOURS = 4 * 365 * 24.0
DEFAULT_HARDWARE_UTILIZATION = 0.5
DEFAULT_NETWORK_ENERGY_KWH_PER_GB = 0.05


@dataclass(frozen=True, slots=True)
class Workload:
    """Audited workload inputs. Units are encoded in every field name."""
    training_hours: float = 0.0
    training_power_watts: float = 300.0
    inference_count: int = 0
    inference_energy_per_request_wh: float = 1.0
    dataset_size_gb: float = 1.0
    network_transfer_gb: float = 0.0
    replication_factor: int = 2
    storage_duration_years: float = 1.0
    carbon_intensity_gco2_per_kwh: float = DEFAULT_CARBON_INTENSITY_GCO2_PER_KWH
    hardware_embodied_carbon_kg: float = DEFAULT_HARDWARE_EMBODIED_CARBON_KG
    hardware_lifetime_hours: float = DEFAULT_HARDWARE_LIFETIME_HOURS
    hardware_power_watts: float = 300.0
    hardware_utilization: float = DEFAULT_HARDWARE_UTILIZATION
    retraining_runs: Optional[int] = None
    retraining_training_hours: float = 0.0
    checkpoints_per_retraining_run: int = 1
    deployment_nodes: int = 1
    network_energy_kwh_per_gb: float = DEFAULT_NETWORK_ENERGY_KWH_PER_GB
    inference_payload_gb_per_request: float = 0.00005


def _validate_workload(workload: Workload) -> None:
    if not isinstance(workload, Workload):
        raise TypeError("workload must be a Workload instance.")
    floats = ("training_hours", "training_power_watts", "inference_energy_per_request_wh", "dataset_size_gb", "network_transfer_gb", "storage_duration_years", "carbon_intensity_gco2_per_kwh", "hardware_embodied_carbon_kg", "hardware_lifetime_hours", "hardware_power_watts", "hardware_utilization", "retraining_training_hours", "network_energy_kwh_per_gb", "inference_payload_gb_per_request")
    for name in floats:
        value = getattr(workload, name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a finite non-negative number.")
    for name in ("inference_count", "replication_factor", "checkpoints_per_retraining_run", "deployment_nodes"):
        value = getattr(workload, name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer.")
    value = workload.retraining_runs
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError("retraining_runs must be a non-negative integer or None.")
    if workload.hardware_lifetime_hours <= 0:
        raise ValueError("hardware_lifetime_hours must be greater than zero.")
    if not 0 < workload.hardware_utilization <= 1:
        raise ValueError("hardware_utilization must be in (0, 1].")


def _runs(architecture: Architecture, workload: Workload) -> int:
    return architecture.retraining_frequency if workload.retraining_runs is None else workload.retraining_runs


def calculate_networking(architecture: Architecture, workload: Workload) -> Dict[str, float]:
    """Calculate dataset, model, replica, retraining, and inference traffic."""
    _validate_workload(workload)
    values = {
        "dataset_transfer_gb": workload.dataset_size_gb,
        "retraining_dataset_transfer_gb": workload.dataset_size_gb * _runs(architecture, workload),
        "model_distribution_gb": architecture.model_size_mb / 1024 * workload.deployment_nodes,
        "replication_network_gb": workload.dataset_size_gb * max(0, workload.replication_factor - 1),
        "inference_traffic_gb": workload.inference_count * workload.inference_payload_gb_per_request,
        "other_network_gb": workload.network_transfer_gb,
    }
    total = sum(values.values())
    return {**values, "total_network_gb": total, "network_energy_kwh": total * workload.network_energy_kwh_per_gb}


def calculate_energy(architecture: Architecture, workload: Workload) -> Dict[str, float]:
    """Calculate kWh. Networking energy appears exactly once in the total."""
    _validate_workload(workload)
    training = workload.training_hours * workload.training_power_watts / 1000
    inference = workload.inference_count * workload.inference_energy_per_request_wh / 1000
    retraining = _runs(architecture, workload) * workload.retraining_training_hours * workload.training_power_watts / 1000
    networking = calculate_networking(architecture, workload)["network_energy_kwh"]
    return {"training_energy_kwh": training, "inference_energy_kwh": inference, "retraining_energy_kwh": retraining, "networking_energy_kwh": networking, "total_energy_kwh": training + inference + retraining + networking}


def calculate_hardware(architecture: Architecture, workload: Workload) -> Dict[str, float]:
    """Amortize embodied carbon by active share of available hardware life."""
    _validate_workload(workload)
    active_hours = workload.training_hours + _runs(architecture, workload) * workload.retraining_training_hours + workload.inference_count * architecture.estimated_latency_ms / 3_600_000
    share = min(1.0, active_hours / (workload.hardware_lifetime_hours * workload.hardware_utilization))
    return {"active_hardware_hours": active_hours, "hardware_power_watts": float(workload.hardware_power_watts), "memory_requirement_mb": architecture.memory_requirement_mb, "lifetime_share": share, "embodied_carbon_kg": workload.hardware_embodied_carbon_kg * share}


def calculate_carbon(architecture: Architecture, workload: Workload, energy: Optional[Mapping[str, float]] = None) -> Dict[str, float]:
    """Convert operational energy to kg CO2e, then add amortized embodied carbon."""
    _validate_workload(workload)
    values = calculate_energy(architecture, workload) if energy is None else energy
    total_energy = values.get("total_energy_kwh")
    if isinstance(total_energy, bool) or not isinstance(total_energy, (int, float)) or not isfinite(total_energy) or total_energy < 0:
        raise ValueError("energy must contain finite, non-negative total_energy_kwh.")
    hardware = calculate_hardware(architecture, workload)
    operational = total_energy * workload.carbon_intensity_gco2_per_kwh / 1000
    return {"operational_carbon_kg": operational, "embodied_carbon_kg": hardware["embodied_carbon_kg"], "total_carbon_kg": operational + hardware["embodied_carbon_kg"], "lifetime_share": hardware["lifetime_share"]}


def calculate_storage(architecture: Architecture, workload: Workload) -> Dict[str, float]:
    """Calculate physical dataset replicas, deployed model, and checkpoints."""
    _validate_workload(workload)
    model_gb = architecture.model_size_mb / 1024
    checkpoints = _runs(architecture, workload) * workload.checkpoints_per_retraining_run
    dataset = workload.dataset_size_gb * workload.replication_factor
    model = model_gb * workload.deployment_nodes
    checkpoint = model_gb * checkpoints
    return {"dataset_storage_gb": dataset, "model_storage_gb": model, "checkpoint_storage_gb": checkpoint, "number_of_checkpoints": float(checkpoints), "total_storage_gb": dataset + model + checkpoint, "storage_duration_years": float(workload.storage_duration_years)}


def calculate_retraining(architecture: Architecture, workload: Workload) -> Dict[str, float]:
    """Return only the retraining slice of the six-pillar inputs."""
    _validate_workload(workload)
    runs = _runs(architecture, workload)
    energy = calculate_energy(architecture, workload)
    network = calculate_networking(architecture, workload)
    checkpoint = architecture.model_size_mb / 1024 * runs * workload.checkpoints_per_retraining_run
    return {"retraining_runs": float(runs), "retraining_energy_kwh": energy["retraining_energy_kwh"], "retraining_carbon_kg": energy["retraining_energy_kwh"] * workload.carbon_intensity_gco2_per_kwh / 1000, "retraining_storage_gb": checkpoint, "retraining_network_gb": network["retraining_dataset_transfer_gb"]}


def calculate_lifecycle_impact(architecture: Architecture, workload: Workload) -> Dict[str, object]:
    """Return six named pillars and the total lifecycle carbon impact."""
    if not isinstance(architecture, Architecture):
        raise TypeError("architecture must be an Architecture instance.")
    energy = calculate_energy(architecture, workload)
    carbon = calculate_carbon(architecture, workload, energy)
    return {"architecture": architecture.name, "energy": energy, "carbon": carbon, "storage": calculate_storage(architecture, workload), "networking": calculate_networking(architecture, workload), "hardware": calculate_hardware(architecture, workload), "retraining": calculate_retraining(architecture, workload), "total_lifecycle_carbon_kg": carbon["total_carbon_kg"]}


def compare_architectures(workload: Workload, minimum_accuracy: float = 0.0, maximum_latency_ms: Optional[float] = None) -> List[Dict[str, object]]:
    """Compare all presets; accuracy/latency boundary values are feasible."""
    if isinstance(minimum_accuracy, bool) or not isinstance(minimum_accuracy, (int, float)) or not isfinite(minimum_accuracy) or not 0 <= minimum_accuracy <= 1:
        raise ValueError("minimum_accuracy must be finite and in [0, 1].")
    if maximum_latency_ms is not None and (isinstance(maximum_latency_ms, bool) or not isinstance(maximum_latency_ms, (int, float)) or not isfinite(maximum_latency_ms) or maximum_latency_ms < 0):
        raise ValueError("maximum_latency_ms must be finite, non-negative, or None.")
    results: List[Dict[str, object]] = []
    for architecture in get_architectures():
        accuracy_ok = architecture.estimated_accuracy >= minimum_accuracy
        latency_ok = maximum_latency_ms is None or architecture.estimated_latency_ms <= maximum_latency_ms
        results.append({"architecture": architecture, "feasible": accuracy_ok and latency_ok, "accuracy_constraint_met": accuracy_ok, "latency_constraint_met": latency_ok, "impact": calculate_lifecycle_impact(architecture, workload)})
    return results
