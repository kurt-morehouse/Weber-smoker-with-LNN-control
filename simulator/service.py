from pathlib import Path

from simulator.calibration import calibrate
from simulator.config import CONFIG
from simulator.experiment import load_experiment
from simulator.prediction import create_prediction_report


class SimulatorService:
    def calibrate_session(
        self,
        session_path: Path,
    ):
        experiment = load_experiment(
            session_path
        )

        calibration = calibrate(
            experiment,
            CONFIG,
        )

        ambient_temperature_c = (
            experiment.external.temperature_c[0]
        )

        prediction = create_prediction_report(
            parameters=calibration.parameters,
            ambient_temperature_c=(
                ambient_temperature_c
            ),
            config=CONFIG,
        )

        return (
            experiment,
            calibration,
            prediction,
        )
