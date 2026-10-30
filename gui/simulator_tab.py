from __future__ import annotations

import time

from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
    Slot,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.app_state import AppState
from core.engineering_state import (
    CalibrationSnapshot,
)
from core.calibration_preflight import (
    calibration_preflight,
)
from simulator.calibration import (
    CalibrationCancelled,
)
from simulator.service import SimulatorService


class CalibrationWorker(QObject):
    progress = Signal(
        int,
        int,
        float,
        bool,
        float,
    )
    phase = Signal(str)
    completed = Signal(
        object,
        object,
        object,
        float,
    )
    failed = Signal(str, str)
    cancelled = Signal(str, float)
    finished = Signal()

    def __init__(
        self,
        session_path: Path,
    ) -> None:
        super().__init__()
        self._session_path = Path(
            session_path
        )
        self._cancel_requested = False
        self._started_at = 0.0

    @Slot()
    def run(self) -> None:
        self._started_at = time.monotonic()
        service = SimulatorService()

        try:
            self.phase.emit(
                "Loading explicit calibration inputs "
                "and starting optimizer..."
            )

            (
                experiment,
                calibration,
                prediction,
            ) = service.calibrate_session(
                self._session_path,
                progress_callback=(
                    self._progress
                ),
                cancel_requested=(
                    lambda:
                    self._cancel_requested
                ),
            )

            elapsed = (
                time.monotonic()
                - self._started_at
            )

            self.completed.emit(
                experiment,
                calibration,
                prediction,
                elapsed,
            )

        except CalibrationCancelled as exc:
            elapsed = (
                time.monotonic()
                - self._started_at
            )
            self.cancelled.emit(
                str(exc),
                elapsed,
            )

        except Exception as exc:
            self.failed.emit(
                type(exc).__name__,
                str(exc),
            )

        finally:
            self.finished.emit()

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _progress(
        self,
        iteration: int,
        total: int,
        best_rmse_c: float,
        improved: bool,
    ) -> None:
        elapsed = (
            time.monotonic()
            - self._started_at
        )

        self.progress.emit(
            iteration,
            total,
            best_rmse_c,
            improved,
            elapsed,
        )


class SimulatorTab(QWidget):

    def __init__(
        self,
        app_state: AppState,
    ) -> None:
        super().__init__()

        self._state = app_state
        self._thread: QThread | None = None
        self._worker: (
            CalibrationWorker | None
        ) = None
        self._last_logged_iteration = 0

        self._session_label = QLabel(
            "No session selected."
        )

        self._preflight_label = QLabel(
            "Select a session to validate "
            "calibration inputs."
        )
        self._preflight_label.setWordWrap(
            True
        )

        self._status_label = QLabel(
            "Calibration idle."
        )
        self._status_label.setWordWrap(
            True
        )

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(
            0,
            10000,
        )
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat(
            "%v / %m iterations"
        )

        self._run_button = QPushButton(
            "Run Calibration"
        )
        self._run_button.setEnabled(
            False
        )

        self._stop_button = QPushButton(
            "Stop Calibration"
        )
        self._stop_button.setEnabled(
            False
        )

        self._output = QTextEdit()
        self._output.setReadOnly(
            True
        )

        self._run_button.clicked.connect(
            self._run_calibration
        )
        self._stop_button.clicked.connect(
            self._stop_calibration
        )
        self._state.session_changed.connect(
            self._session_changed
        )

        buttons = QHBoxLayout()
        buttons.addWidget(
            self._run_button
        )
        buttons.addWidget(
            self._stop_button
        )

        layout = QVBoxLayout()
        layout.addWidget(
            self._session_label
        )
        layout.addWidget(
            self._preflight_label
        )
        layout.addWidget(
            self._status_label
        )
        layout.addWidget(
            self._progress_bar
        )
        layout.addLayout(
            buttons
        )
        layout.addWidget(
            self._output
        )
        self.setLayout(layout)

        if (
            self._state.selected_session
            is not None
        ):
            self._session_changed(
                self._state.selected_session
            )

    def _session_changed(
        self,
        session_path,
    ) -> None:
        if self._thread is not None:
            return

        self._run_button.setEnabled(
            False
        )

        if session_path is None:
            self._session_label.setText(
                "No session selected."
            )
            self._preflight_label.setText(
                "Select a session to validate "
                "calibration inputs."
            )
            self._status_label.setText(
                "Calibration idle."
            )
            return

        self._session_label.setText(
            f"Selected session: "
            f"{session_path.name}"
        )

        self._apply_preflight(
            session_path
        )

    def _apply_preflight(
        self,
        session_path,
    ):
        report = calibration_preflight(
            session_path
        )

        if report.ready:
            lines = [
                "Calibration preflight: READY",
                (
                    "Heater power: "
                    f"{report.heater_power_w:.0f} W "
                    f"({report.heater_power_source})"
                ),
                *report.input_summary_lines,
            ]

            self._preflight_label.setText(
                "\n".join(lines)
            )

            if self._thread is None:
                self._run_button.setEnabled(
                    True
                )

        else:
            text = (
                "Calibration preflight: NOT READY\n"
                + "\n".join(
                    f"• {error}"
                    for error
                    in report.errors
                )
            )

            self._preflight_label.setText(
                text
            )
            self._run_button.setEnabled(
                False
            )

        return report

    @Slot()
    def _run_calibration(
        self,
    ) -> None:
        session_path = (
            self._state.selected_session
        )

        if (
            session_path is None
            or self._thread is not None
        ):
            return

        report = self._apply_preflight(
            session_path
        )

        if not report.ready:
            self._output.clear()
            self._output.append(
                "WEBER THERMAL CALIBRATION"
            )
            self._output.append(
                "=" * 50
            )
            self._output.append(
                f"Session: "
                f"{session_path.name}"
            )
            self._output.append("")
            self._output.append(
                "CALIBRATION NOT STARTED"
            )

            for error in report.errors:
                self._output.append(
                    f"- {error}"
                )

            return

        self._output.clear()
        self._output.append(
            "WEBER THERMAL CALIBRATION"
        )
        self._output.append(
            "=" * 50
        )
        self._output.append(
            f"Session: "
            f"{session_path.name}"
        )
        self._output.append(
            f"Validated heater power: "
            f"{report.heater_power_w:.0f} W"
        )
        self._output.append("")
        self._output.append(
            "EXPLICIT CALIBRATION INPUTS"
        )

        for line in (
            report.input_summary_lines
        ):
            self._output.append(
                line
            )

        self._output.append("")
        self._output.append(
            "Preflight passed."
        )
        self._output.append(
            "Starting background calibration..."
        )

        self._status_label.setText(
            "Starting calibration..."
        )
        self._progress_bar.setRange(
            0,
            10000,
        )
        self._progress_bar.setValue(0)
        self._last_logged_iteration = 0

        self._run_button.setEnabled(
            False
        )
        self._stop_button.setEnabled(
            True
        )

        thread = QThread(self)
        worker = CalibrationWorker(
            Path(session_path)
        )
        worker.moveToThread(
            thread
        )

        thread.started.connect(
            worker.run
        )
        worker.phase.connect(
            self._on_phase
        )
        worker.progress.connect(
            self._on_progress
        )
        worker.completed.connect(
            self._on_completed
        )
        worker.failed.connect(
            self._on_failed
        )
        worker.cancelled.connect(
            self._on_cancelled
        )
        worker.finished.connect(
            thread.quit
        )
        worker.finished.connect(
            worker.deleteLater
        )
        thread.finished.connect(
            self._thread_finished
        )
        thread.finished.connect(
            thread.deleteLater
        )

        self._thread = thread
        self._worker = worker

        thread.start()

    @Slot()
    def _stop_calibration(
        self,
    ) -> None:
        if self._worker is None:
            return

        self._stop_button.setEnabled(
            False
        )
        self._status_label.setText(
            "Cancellation requested; "
            "finishing current iteration..."
        )
        self._output.append("")
        self._output.append(
            "Cancellation requested."
        )

        self._worker.request_cancel()

    @Slot(str)
    def _on_phase(
        self,
        message: str,
    ) -> None:
        self._status_label.setText(
            message
        )
        self._output.append(
            message
        )

    @Slot(
        int,
        int,
        float,
        bool,
        float,
    )
    def _on_progress(
        self,
        iteration: int,
        total: int,
        best_rmse_c: float,
        improved: bool,
        elapsed_seconds: float,
    ) -> None:
        self._progress_bar.setRange(
            0,
            total,
        )
        self._progress_bar.setValue(
            iteration
        )

        rate = (
            iteration / elapsed_seconds
            if elapsed_seconds > 0.0
            else 0.0
        )

        remaining = max(
            0,
            total - iteration,
        )

        eta_seconds = (
            remaining / rate
            if rate > 0.0
            else 0.0
        )

        self._status_label.setText(
            f"Iteration {iteration:,} / "
            f"{total:,} | "
            f"Best RMSE "
            f"{best_rmse_c:.3f} °C | "
            f"Elapsed "
            f"{self._format_time(elapsed_seconds)} | "
            f"ETA "
            f"{self._format_time(eta_seconds)}"
        )

        if (
            improved
            or (
                iteration
                - self._last_logged_iteration
                >= 250
            )
            or iteration == total
        ):
            marker = (
                "new best"
                if improved
                else "heartbeat"
            )

            self._output.append(
                f"Iteration "
                f"{iteration:,}/{total:,} | "
                f"best RMSE "
                f"{best_rmse_c:.3f} °C | "
                f"{marker}"
            )

            self._last_logged_iteration = (
                iteration
            )

    @Slot(
        object,
        object,
        object,
        float,
    )
    def _on_completed(
        self,
        experiment,
        calibration,
        prediction,
        elapsed_seconds: float,
    ) -> None:
        self._status_label.setText(
            "Calibration completed in "
            f"{self._format_time(elapsed_seconds)}."
        )
        self._progress_bar.setValue(
            self._progress_bar.maximum()
        )

        self._output.append("")
        self._output.append(
            "CALIBRATION COMPLETE"
        )
        self._output.append(
            f"Experiment: "
            f"{experiment.metadata.name}"
        )
        self._output.append(
            f"Heater: "
            f"{experiment.metadata.heater_power_w:.0f} W"
        )
        self._output.append(
            f"Chamber input: "
            f"{experiment.metadata.internal_file.name} / "
            f"{experiment.metadata.internal_temperature_column}"
        )
        self._output.append(
            f"Body input: "
            f"{experiment.metadata.external_file.name} / "
            f"{experiment.metadata.external_temperature_column}"
        )
        self._output.append(
            f"Internal samples: "
            f"{len(experiment.internal.time_seconds):,}"
        )
        self._output.append(
            f"External samples: "
            f"{len(experiment.external.time_seconds):,}"
        )
        self._output.append(
            f"RMSE: "
            f"{calibration.rmse_c:.3f} °C"
        )

        parameters = (
            calibration.parameters
        )

        self._output.append(
            f"Heater efficiency: "
            f"{parameters.heater_efficiency:.3f}"
        )
        self._output.append(
            "Chamber heat capacity: "
            f"{parameters.chamber_heat_capacity_j_per_k:,.0f} J/K"
        )
        self._output.append(
            "Body heat capacity: "
            f"{parameters.body_heat_capacity_j_per_k:,.0f} J/K"
        )

        required_power = (
            prediction
            .estimated_power_for_target_w
        )

        if required_power is None:
            self._output.append(
                "225°F power estimate unavailable."
            )
        else:
            self._output.append(
                f"Estimated power for 225°F: "
                f"{required_power:.0f} W"
            )

        snapshot = CalibrationSnapshot(
            session_path=Path(
                self._state.selected_session
            ),
            rmse_c=calibration.rmse_c,
            required_power_w=required_power,
        )

        self._state.set_calibration(
            snapshot
        )

    @Slot(str, str)
    def _on_failed(
        self,
        exception_name: str,
        message: str,
    ) -> None:
        self._status_label.setText(
            "Calibration failed."
        )
        self._output.append("")
        self._output.append(
            "CALIBRATION FAILED"
        )
        self._output.append(
            f"{exception_name}: "
            f"{message}"
        )

    @Slot(str, float)
    def _on_cancelled(
        self,
        message: str,
        elapsed_seconds: float,
    ) -> None:
        self._status_label.setText(
            "Calibration cancelled after "
            f"{self._format_time(elapsed_seconds)}."
        )
        self._output.append("")
        self._output.append(
            "CALIBRATION CANCELLED"
        )
        self._output.append(
            message
        )

    @Slot()
    def _thread_finished(
        self,
    ) -> None:
        self._thread = None
        self._worker = None

        self._stop_button.setEnabled(
            False
        )

        session_path = (
            self._state.selected_session
        )

        if session_path is not None:
            self._apply_preflight(
                session_path
            )

    @staticmethod
    def _format_time(
        seconds: float,
    ) -> str:
        total = max(
            0,
            int(round(seconds)),
        )

        minutes, seconds = divmod(
            total,
            60,
        )
        hours, minutes = divmod(
            minutes,
            60,
        )

        if hours:
            return (
                f"{hours:d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )
