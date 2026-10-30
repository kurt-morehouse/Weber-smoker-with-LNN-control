from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.calibration import ThermalCalibration
from core.calibration_store import load_calibration


@dataclass(frozen=True)
class ExperimentComparison:
    baseline_session: Path
    modified_session: Path
    baseline: ThermalCalibration
    modified: ThermalCalibration
    heat_loss_change_percent: float
    capacitance_change_percent: float
    time_constant_change_percent: float
    equilibrium_change_f: float
    baseline_required_power_w: float
    modified_required_power_w: float
    required_power_change_w: float
    required_power_change_percent: float
    target_temperature_f: float
    outside_temperature_f: float


def _percent_change(new: float, old: float) -> float:
    if old == 0.0:
        raise ValueError("Cannot calculate percent change from zero.")
    return 100.0 * (new - old) / old


def _required_power(
    calibration: ThermalCalibration,
    target_f: float,
    outside_f: float,
) -> float:
    return max(
        0.0,
        calibration.heat_loss_coefficient_w_per_f * (target_f - outside_f),
    )


def compare_calibrations(
    *,
    baseline_session: Path,
    modified_session: Path,
    target_temperature_f: float = 225.0,
    outside_temperature_f: float = 75.0,
) -> ExperimentComparison:
    baseline = load_calibration(baseline_session)
    modified = load_calibration(modified_session)

    p_a = _required_power(baseline, target_temperature_f, outside_temperature_f)
    p_b = _required_power(modified, target_temperature_f, outside_temperature_f)

    return ExperimentComparison(
        baseline_session=Path(baseline_session),
        modified_session=Path(modified_session),
        baseline=baseline,
        modified=modified,
        heat_loss_change_percent=_percent_change(
            modified.heat_loss_coefficient_w_per_f,
            baseline.heat_loss_coefficient_w_per_f,
        ),
        capacitance_change_percent=_percent_change(
            modified.effective_thermal_capacitance_j_per_f,
            baseline.effective_thermal_capacitance_j_per_f,
        ),
        time_constant_change_percent=_percent_change(
            modified.time_constant_seconds,
            baseline.time_constant_seconds,
        ),
        equilibrium_change_f=(
            modified.equilibrium_temperature_f
            - baseline.equilibrium_temperature_f
        ),
        baseline_required_power_w=p_a,
        modified_required_power_w=p_b,
        required_power_change_w=p_b - p_a,
        required_power_change_percent=_percent_change(p_b, p_a),
        target_temperature_f=target_temperature_f,
        outside_temperature_f=outside_temperature_f,
    )
