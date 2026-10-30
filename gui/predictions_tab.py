from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from gui.app_state import AppState


class PredictionsTab(QWidget):

    def __init__(
        self,
        app_state: AppState,
    ) -> None:

        super().__init__()

        self._state = app_state

        self._title = QLabel(
            "Heater Power Prediction"
        )

        self._session = QLabel(
            "No calibrated session."
        )

        self._rmse = QLabel(
            "Calibration RMSE: ---"
        )

        self._target = QLabel(
            "Target chamber temperature: 225°F"
        )

        self._required_power = QLabel(
            "Required heater power: ---"
        )

        layout = QVBoxLayout()

        layout.addWidget(
            self._title
        )

        layout.addWidget(
            self._session
        )

        layout.addWidget(
            self._rmse
        )

        layout.addWidget(
            self._target
        )

        layout.addWidget(
            self._required_power
        )

        layout.addStretch()

        self.setLayout(layout)

        self._state.calibration_changed.connect(
            self._calibration_changed
        )

    def _calibration_changed(
        self,
        calibration,
    ) -> None:

        if calibration is None:
            return

        self._session.setText(
            f"Calibrated session: "
            f"{calibration.session_path.name}"
        )

        self._rmse.setText(
            f"Calibration RMSE: "
            f"{calibration.rmse_c:.3f} °C"
        )

        if (
            calibration.required_power_w
            is None
        ):

            self._required_power.setText(
                "Required heater power: "
                "unavailable"
            )

        else:

            self._required_power.setText(
                f"Required heater power: "
                f"{calibration.required_power_w:.0f} W"
            )
