from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExperimentMetadata:
    name: str
    heater_power_w: float

    internal_file: Path
    external_file: Path

    ambient_temperature_f: float | None

    internal_temperature_column: str
    external_temperature_column: str

    notes: str = ""


@dataclass(frozen=True)
class MeasurementSeries:
    time_seconds: tuple[float, ...]
    temperature_c: tuple[float, ...]


@dataclass(frozen=True)
class ExperimentData:
    metadata: ExperimentMetadata
    internal: MeasurementSeries
    external: MeasurementSeries


@dataclass(frozen=True)
class ThermalParameters:
    chamber_heat_capacity_j_per_k: float
    body_heat_capacity_j_per_k: float

    chamber_body_conductance_w_per_k: float
    chamber_ambient_conductance_w_per_k: float
    body_ambient_conductance_w_per_k: float

    heater_efficiency: float


@dataclass(frozen=True)
class SimulationResult:
    time_seconds: tuple[float, ...]
    chamber_temperature_c: tuple[float, ...]
    body_temperature_c: tuple[float, ...]


@dataclass(frozen=True)
class CalibrationResult:
    parameters: ThermalParameters
    rmse_c: float


@dataclass(frozen=True)
class PredictionPoint:
    heater_power_w: float
    final_temperature_c: float
    steady_state_temperature_c: float


@dataclass(frozen=True)
class PredictionReport:
    points: tuple[PredictionPoint, ...]
    estimated_power_for_target_w: float | None
