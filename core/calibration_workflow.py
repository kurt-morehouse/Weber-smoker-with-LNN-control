from __future__ import annotations

from pathlib import Path

from core.calibration import (
    ThermalCalibration,
    calibration_from_power_estimate,
)
from core.calibration_store import save_calibration
from core.experiment_reader import RecordedExperiment
from core.thermal_analysis import estimate_full_power_response


def calibrate_recorded_channel(
    *,
    recorded: RecordedExperiment,
    session_path: Path,
    probe_index: int,
    series_index: int,
    heater_power_w: float,
    outside_temperature_f: float,
    target_temperature_f: float = 225.0,
    save: bool = True,
) -> ThermalCalibration:
    """
    Measured experiment -> fitted parameters.

    Probe/channel selection is explicit so the calibration layer never
    silently mistakes a lid-loss or food channel for chamber air.
    """
    probe = recorded.probes[probe_index]
    series = probe.series[series_index]

    times: list[float] = []
    values: list[float] = []

    for elapsed, value in zip(probe.time_seconds, series.values):
        if value is None:
            continue
        times.append(float(elapsed))
        values.append(float(value))

    estimate = estimate_full_power_response(
        times,
        values,
        heater_power_w=heater_power_w,
        target_temperature_f=target_temperature_f,
        outside_temperature_f=outside_temperature_f,
    )

    calibration = calibration_from_power_estimate(
        estimate=estimate,
        source_session=session_path,
        source_probe=probe.friendly_name,
        source_channel=series.name,
    )

    if save:
        save_calibration(session_path, calibration)

    return calibration
