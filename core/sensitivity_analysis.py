from __future__ import annotations

from dataclasses import dataclass

from core.calibrated_simulator import CalibratedChamberModel


@dataclass(frozen=True)
class SensitivityPoint:
    heater_power_w: float
    equilibrium_temperature_f: float
    temperature_after_duration_f: float
    time_to_target_seconds: float | None


def heater_power_sweep(
    model: CalibratedChamberModel,
    *,
    initial_temperature_f: float,
    outside_temperature_f: float,
    target_temperature_f: float,
    duration_seconds: float,
    center_power_w: float,
    span_percent: float = 50.0,
    steps: int = 7,
) -> list[SensitivityPoint]:
    if center_power_w <= 0.0:
        raise ValueError("Center heater power must be greater than zero.")
    if span_percent < 0.0:
        raise ValueError("Span percent cannot be negative.")
    if steps < 2:
        raise ValueError("Sensitivity sweep requires at least two steps.")

    fraction = span_percent / 100.0
    low = max(0.0, center_power_w * (1.0 - fraction))
    high = center_power_w * (1.0 + fraction)

    points: list[SensitivityPoint] = []

    for index in range(steps):
        ratio = index / (steps - 1)
        power = low + (high - low) * ratio

        prediction = model.temperature_after(
            initial_temperature_f=initial_temperature_f,
            elapsed_seconds=duration_seconds,
            heater_power_w=power,
            outside_temperature_f=outside_temperature_f,
        )

        points.append(
            SensitivityPoint(
                heater_power_w=power,
                equilibrium_temperature_f=prediction.equilibrium_temperature_f,
                temperature_after_duration_f=prediction.chamber_temperature_f,
                time_to_target_seconds=model.time_to_temperature_seconds(
                    initial_temperature_f=initial_temperature_f,
                    target_temperature_f=target_temperature_f,
                    heater_power_w=power,
                    outside_temperature_f=outside_temperature_f,
                ),
            )
        )

    return points
