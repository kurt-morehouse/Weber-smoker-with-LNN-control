from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.calibration import ThermalCalibration
from core.calibration_store import load_calibration
from core.calibrated_simulator import CalibratedChamberModel


@dataclass(frozen=True)
class DigitalTwinSnapshot:
    session: Path
    calibration: ThermalCalibration

    @property
    def model(self) -> CalibratedChamberModel:
        return CalibratedChamberModel(self.calibration)

    @property
    def heat_loss_w_per_f(self) -> float:
        return self.calibration.heat_loss_coefficient_w_per_f

    @property
    def capacitance_j_per_f(self) -> float:
        return self.calibration.effective_thermal_capacitance_j_per_f

    @property
    def time_constant_hours(self) -> float:
        return self.calibration.time_constant_seconds / 3600.0


class DigitalTwinManager:
    """Loads calibrated experiment snapshots without modifying raw data."""

    def load(self, session: Path) -> DigitalTwinSnapshot:
        session = Path(session)
        return DigitalTwinSnapshot(
            session=session,
            calibration=load_calibration(session),
        )
