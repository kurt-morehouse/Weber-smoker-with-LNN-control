from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from core.calibration_store import load_calibration
from core.calibrated_simulator import CalibratedChamberModel


@dataclass(frozen=True)
class ValidationResult:
    baseline_session: Path
    observed_session: Path
    elapsed_seconds: float
    observed_temperature_f: float
    predicted_temperature_f: float
    prediction_error_f: float
    absolute_error_f: float


def validate_baseline_model_against_experiment(
    *,
    baseline_session: Path,
    observed_session: Path,
) -> ValidationResult:
    """
    Use calibration A to predict experiment B's fitted response at one B
    time constant. A large error after a physical modification can be useful
    evidence that the smoker itself changed.
    """
    baseline = load_calibration(baseline_session)
    observed = load_calibration(observed_session)

    model = CalibratedChamberModel(baseline)
    elapsed = observed.time_constant_seconds

    prediction = model.temperature_after(
        initial_temperature_f=observed.initial_temperature_f,
        elapsed_seconds=elapsed,
        heater_power_w=observed.heater_power_w,
        outside_temperature_f=observed.outside_temperature_f,
    )

    observed_at_tau = (
        observed.equilibrium_temperature_f
        + (
            observed.initial_temperature_f
            - observed.equilibrium_temperature_f
        ) * math.exp(-1.0)
    )

    error = prediction.chamber_temperature_f - observed_at_tau

    return ValidationResult(
        baseline_session=Path(baseline_session),
        observed_session=Path(observed_session),
        elapsed_seconds=elapsed,
        observed_temperature_f=observed_at_tau,
        predicted_temperature_f=prediction.chamber_temperature_f,
        prediction_error_f=error,
        absolute_error_f=abs(error),
    )
