from __future__ import annotations

from dataclasses import dataclass
import math

from core.calibration import ThermalCalibration


@dataclass(frozen=True)
class ChamberPrediction:
    elapsed_seconds: float
    chamber_temperature_f: float
    equilibrium_temperature_f: float
    heater_power_w: float
    outside_temperature_f: float


class CalibratedChamberModel:
    """
    One-node calibrated chamber model.

        C dT/dt = P - K(T - T_out)
    """

    def __init__(self, calibration: ThermalCalibration) -> None:
        self.calibration = calibration

    @property
    def heat_loss_coefficient_w_per_f(self) -> float:
        return self.calibration.heat_loss_coefficient_w_per_f

    @property
    def thermal_capacitance_j_per_f(self) -> float:
        return self.calibration.effective_thermal_capacitance_j_per_f

    @property
    def time_constant_seconds(self) -> float:
        return (
            self.thermal_capacitance_j_per_f
            / self.heat_loss_coefficient_w_per_f
        )

    def equilibrium_temperature_f(
        self,
        *,
        heater_power_w: float,
        outside_temperature_f: float,
    ) -> float:
        if heater_power_w < 0.0:
            raise ValueError("Heater power cannot be negative.")

        return (
            outside_temperature_f
            + heater_power_w / self.heat_loss_coefficient_w_per_f
        )

    def temperature_after(
        self,
        *,
        initial_temperature_f: float,
        elapsed_seconds: float,
        heater_power_w: float,
        outside_temperature_f: float,
    ) -> ChamberPrediction:
        if elapsed_seconds < 0.0:
            raise ValueError("Elapsed time cannot be negative.")

        equilibrium_f = self.equilibrium_temperature_f(
            heater_power_w=heater_power_w,
            outside_temperature_f=outside_temperature_f,
        )

        decay = math.exp(-elapsed_seconds / self.time_constant_seconds)

        temperature_f = (
            equilibrium_f
            + (initial_temperature_f - equilibrium_f) * decay
        )

        return ChamberPrediction(
            elapsed_seconds=elapsed_seconds,
            chamber_temperature_f=temperature_f,
            equilibrium_temperature_f=equilibrium_f,
            heater_power_w=heater_power_w,
            outside_temperature_f=outside_temperature_f,
        )

    def required_power_w(
        self,
        *,
        target_temperature_f: float,
        outside_temperature_f: float,
    ) -> float:
        rise_f = target_temperature_f - outside_temperature_f
        if rise_f <= 0.0:
            return 0.0
        return self.heat_loss_coefficient_w_per_f * rise_f

    def time_to_temperature_seconds(
        self,
        *,
        initial_temperature_f: float,
        target_temperature_f: float,
        heater_power_w: float,
        outside_temperature_f: float,
    ) -> float | None:
        """
        None means the target is at/above predicted equilibrium and
        therefore is not reachable with the specified power.
        """
        equilibrium_f = self.equilibrium_temperature_f(
            heater_power_w=heater_power_w,
            outside_temperature_f=outside_temperature_f,
        )

        if target_temperature_f <= initial_temperature_f:
            return 0.0

        if target_temperature_f >= equilibrium_f:
            return None

        numerator = target_temperature_f - equilibrium_f
        denominator = initial_temperature_f - equilibrium_f

        if denominator == 0.0:
            return None

        ratio = numerator / denominator
        if not 0.0 < ratio < 1.0:
            return None

        return -self.time_constant_seconds * math.log(ratio)

    def simulate(
        self,
        *,
        initial_temperature_f: float,
        duration_seconds: float,
        sample_seconds: float,
        heater_power_w: float,
        outside_temperature_f: float,
    ) -> list[ChamberPrediction]:
        if duration_seconds < 0.0:
            raise ValueError("Duration cannot be negative.")
        if sample_seconds <= 0.0:
            raise ValueError("Sample interval must be greater than zero.")

        points: list[ChamberPrediction] = []
        elapsed = 0.0

        while elapsed <= duration_seconds + 1e-9:
            points.append(
                self.temperature_after(
                    initial_temperature_f=initial_temperature_f,
                    elapsed_seconds=elapsed,
                    heater_power_w=heater_power_w,
                    outside_temperature_f=outside_temperature_f,
                )
            )
            elapsed += sample_seconds

        return points
