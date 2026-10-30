from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.calibration_store import load_calibration
from core.calibrated_simulator import CalibratedChamberModel
from core.experiment_notes import load_experiment_notes


JOURNAL_FILENAME = "engineering_report.md"


def write_engineering_report(
    session: Path,
    *,
    target_temperature_f: float = 225.0,
) -> Path:
    """Generate a reproducible engineering summary beside the experiment."""
    session = Path(session)
    calibration = load_calibration(session)
    notes = load_experiment_notes(session)
    model = CalibratedChamberModel(calibration)

    required_power = model.required_power_w(
        target_temperature_f=target_temperature_f,
        outside_temperature_f=calibration.outside_temperature_f,
    )

    tags = ", ".join(notes.tags) if notes.tags else "—"

    text = f"""# Weber Engineering Experiment Report

Generated: {datetime.now(timezone.utc).isoformat()}

## Experiment

- Session: `{session.name}`
- Calibration source probe: {calibration.source_probe}
- Calibration source channel: {calibration.source_channel}
- Tags: {tags}

## Objective

{notes.objective or "Not recorded."}

## Description / Hardware Configuration

{notes.description or "Not recorded."}

## Measured / Fitted Results

- Test heater power: {calibration.heater_power_w:.0f} W
- Outside ambient assumption: {calibration.outside_temperature_f:.1f} °F
- Initial chamber temperature: {calibration.initial_temperature_f:.1f} °F
- Fitted equilibrium temperature: {calibration.equilibrium_temperature_f:.1f} °F
- Thermal time constant: {calibration.time_constant_seconds / 3600.0:.3f} h
- Fit R²: {calibration.fit_r_squared:.4f}
- Heat-loss coefficient K: {calibration.heat_loss_coefficient_w_per_f:.4f} W/°F
- Effective thermal capacitance C: {calibration.effective_thermal_capacitance_j_per_f:,.0f} J/°F
- Estimated power for {target_temperature_f:.1f} °F: {required_power:.0f} W

## Recorded Results

{notes.results or "Not recorded."}

## Conclusions

{notes.conclusions or "Not recorded."}

## Model

Current calibrated chamber model:

`C dT/dt = P - K(T - T_out)`

This report is derived from saved calibration and experiment notes. Raw acquisition
CSV files are not altered.
"""

    path = session / JOURNAL_FILENAME
    path.write_text(text, encoding="utf-8")
    return path
