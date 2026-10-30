from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class LiveProbeReading:
    address: str
    friendly_name: str

    food_temperature_c: float | None
    ambient_temperature_c: float | None

    tip_1_temperature_c: float | None
    tip_2_temperature_c: float | None
    tip_3_temperature_c: float | None
    tip_4_temperature_c: float | None

    battery_percent: float | None
    rssi: int | None

    timestamp_utc: datetime


@dataclass
class DigitalTwinState:
    """
    Shared state representing the physical Weber and its digital counterpart.

    The physics model and eventual LNN will update the predicted values.
    """

    measured_chamber_temperature_c: float | None = None
    predicted_chamber_temperature_c: float | None = None

    measured_external_temperature_c: float | None = None
    predicted_external_temperature_c: float | None = None

    heater_power_w: float = 0.0
    heater_duty_cycle: float = 0.0

    prediction_error_c: float | None = None

    updated_at_utc: datetime = field(
        default_factory=utc_now
    )


@dataclass
class EngineeringState:
    selected_session: Path | None = None
    active_session: Path | None = None

    acquisition_running: bool = False

    live_probes: tuple[LiveProbeReading, ...] = ()

    digital_twin: DigitalTwinState = field(
        default_factory=DigitalTwinState
    )

@dataclass(frozen=True)
class CalibrationSnapshot:
    session_path: Path
    rmse_c: float
    required_power_w: float | None