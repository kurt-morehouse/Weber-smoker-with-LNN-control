from __future__ import annotations

import json
from pathlib import Path

from core.calibration import ThermalCalibration


CALIBRATION_FILENAME = "thermal_calibration.json"


def calibration_path(session: Path) -> Path:
    return session / CALIBRATION_FILENAME


def save_calibration(
    session: Path,
    calibration: ThermalCalibration,
) -> Path:
    """
    Save fitted parameters beside the experiment that produced them.
    Raw acquisition files and the manifest are not modified.
    """
    session.mkdir(parents=True, exist_ok=True)
    path = calibration_path(session)

    path.write_text(
        json.dumps(calibration.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_calibration(session: Path) -> ThermalCalibration:
    path = calibration_path(session)

    if not path.exists():
        raise FileNotFoundError(f"No thermal calibration found at {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    return ThermalCalibration(
        schema_version=int(data["schema_version"]),
        created_utc=str(data["created_utc"]),
        source_session=str(data["source_session"]),
        source_probe=str(data["source_probe"]),
        source_channel=str(data["source_channel"]),
        heater_power_w=float(data["heater_power_w"]),
        outside_temperature_f=float(data["outside_temperature_f"]),
        initial_temperature_f=float(data["initial_temperature_f"]),
        equilibrium_temperature_f=float(data["equilibrium_temperature_f"]),
        time_constant_seconds=float(data["time_constant_seconds"]),
        fit_r_squared=float(data["fit_r_squared"]),
        heat_loss_coefficient_w_per_f=float(
            data["heat_loss_coefficient_w_per_f"]
        ),
        effective_thermal_capacitance_j_per_f=float(
            data["effective_thermal_capacitance_j_per_f"]
        ),
    )
