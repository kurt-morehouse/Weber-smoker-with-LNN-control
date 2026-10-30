from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.thermal_analysis import ThermalPowerEstimate


CALIBRATION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ThermalCalibration:
    """
    Fitted parameters derived from one measured experiment.

    Raw measurements are intentionally not stored in this object.
    """

    schema_version: int
    created_utc: str

    source_session: str
    source_probe: str
    source_channel: str

    heater_power_w: float
    outside_temperature_f: float
    initial_temperature_f: float
    equilibrium_temperature_f: float
    time_constant_seconds: float
    fit_r_squared: float

    heat_loss_coefficient_w_per_f: float
    effective_thermal_capacitance_j_per_f: float

    @property
    def heat_loss_coefficient_w_per_k(self) -> float:
        return self.heat_loss_coefficient_w_per_f * 1.8

    @property
    def effective_thermal_capacitance_j_per_k(self) -> float:
        return self.effective_thermal_capacitance_j_per_f * 1.8

    def to_dict(self) -> dict:
        data = asdict(self)
        data["heat_loss_coefficient_w_per_k"] = (
            self.heat_loss_coefficient_w_per_k
        )
        data["effective_thermal_capacitance_j_per_k"] = (
            self.effective_thermal_capacitance_j_per_k
        )
        return data


def calibration_from_power_estimate(
    *,
    estimate: ThermalPowerEstimate,
    source_session: Path | str,
    source_probe: str,
    source_channel: str,
) -> ThermalCalibration:
    """
    Convert the fitted first-order response to physical parameters.

        P = K * (T_inf - T_out)
        tau = C / K

    therefore:

        K = P / (T_inf - T_out)
        C = tau * K
    """
    temperature_rise_f = (
        estimate.equilibrium_temperature_f
        - estimate.outside_temperature_f
    )

    if estimate.heater_power_w <= 0.0:
        raise ValueError("Heater power must be greater than zero.")

    if temperature_rise_f <= 1.0:
        raise ValueError(
            "Equilibrium temperature must be meaningfully above outside ambient."
        )

    if estimate.time_constant_seconds <= 0.0:
        raise ValueError("Thermal time constant must be greater than zero.")

    heat_loss_w_per_f = estimate.heater_power_w / temperature_rise_f
    capacitance_j_per_f = (
        estimate.time_constant_seconds * heat_loss_w_per_f
    )

    return ThermalCalibration(
        schema_version=CALIBRATION_SCHEMA_VERSION,
        created_utc=datetime.now(timezone.utc).isoformat(),
        source_session=str(source_session),
        source_probe=source_probe,
        source_channel=source_channel,
        heater_power_w=estimate.heater_power_w,
        outside_temperature_f=estimate.outside_temperature_f,
        initial_temperature_f=estimate.initial_temperature_f,
        equilibrium_temperature_f=estimate.equilibrium_temperature_f,
        time_constant_seconds=estimate.time_constant_seconds,
        fit_r_squared=estimate.r_squared,
        heat_loss_coefficient_w_per_f=heat_loss_w_per_f,
        effective_thermal_capacitance_j_per_f=capacitance_j_per_f,
    )
