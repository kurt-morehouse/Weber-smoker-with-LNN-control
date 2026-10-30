from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.experiment_manifest import load_manifest
from core.experiment_reader import load_recorded_experiment
from gui.probe_labels_dialog import ProbeLabelsDialog
from gui.selectable_plot import REPLAY_METRICS, SelectablePlot


class AcquisitionTab(QWidget):
    def __init__(self, app_state, acquisition_controller, parent=None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.controller = acquisition_controller
        self._replay_started_at: datetime | None = None
        self._replay_last_tick = 0.0

        self.status_label = QLabel("Acquisition stopped")
        self.session_label = QLabel("No active session")
        self.start_button = QPushButton("Start Acquisition")
        self.stop_button = QPushButton("Stop Acquisition")
        self.stop_button.setEnabled(False)
        self.labels_button = QPushButton("Configure Probe Labels")
        self.start_button.clicked.connect(self.controller.start)
        self.stop_button.clicked.connect(self.controller.stop)
        self.labels_button.clicked.connect(self._configure_labels)

        controls = QHBoxLayout()
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.labels_button)
        controls.addWidget(self.status_label, 1)

        self._views = QTabWidget()
        self.live_plot = SelectablePlot("Live probe readings")
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            [
                "Probe", "Address", "Food °F", "Ambient °F",
                "Tip 1 °F", "Tip 2 °F", "Tip 3 °F", "Tip 4 °F",
                "RSSI", "Battery %",
            ]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        live_page = QWidget()
        live_layout = QVBoxLayout(live_page)
        live_layout.addWidget(self.live_plot, 1)
        live_layout.addWidget(self.table)
        self._views.addTab(live_page, "Live")

        self._replay_sessions = QComboBox()
        self._refresh_replay_button = QPushButton("Refresh Sessions")
        self._load_replay_button = QPushButton("Load Replay")
        self._refresh_replay_button.clicked.connect(self._refresh_replay_sessions)
        self._load_replay_button.clicked.connect(self._load_replay)
        replay_controls = QHBoxLayout()
        replay_controls.addWidget(QLabel("Recorded session:"))
        replay_controls.addWidget(self._replay_sessions, 1)
        replay_controls.addWidget(self._refresh_replay_button)
        replay_controls.addWidget(self._load_replay_button)

        self._play_button = QPushButton("Play")
        self._speed = QComboBox()
        for speed in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0):
            self._speed.addItem(f"{speed:g}×", speed)
        self._speed.setCurrentIndex(2)
        self._cursor_slider = QSlider(Qt.Orientation.Horizontal)
        self._cursor_slider.setRange(0, 10000)
        self._cursor_slider.setEnabled(False)
        self._cursor_label = QLabel("Cursor: —")
        playback_controls = QHBoxLayout()
        playback_controls.addWidget(self._play_button)
        playback_controls.addWidget(QLabel("Speed:"))
        playback_controls.addWidget(self._speed)
        playback_controls.addWidget(self._cursor_slider, 1)
        playback_controls.addWidget(self._cursor_label)

        self.replay_plot = SelectablePlot("Recorded session replay")
        self._replay_plot_started_at: datetime | None = None
        self._replay_readouts = QTableWidget(0, 3)
        self._replay_readouts.setHorizontalHeaderLabels(
            ["Selected channel", "Exact sample time", "Exact value"]
        )
        self._replay_readouts.setMaximumHeight(190)
        self._replay_readouts.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        replay_header = self._replay_readouts.horizontalHeader()
        replay_header.setStretchLastSection(False)
        replay_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._replay_readouts.setColumnWidth(0, 120)
        self._replay_readouts.setColumnWidth(1, 125)
        self._replay_readouts.setColumnWidth(2, 85)
        replay_page = QWidget()
        replay_layout = QVBoxLayout(replay_page)
        replay_layout.addLayout(replay_controls)
        replay_layout.addLayout(playback_controls)
        self.replay_plot.add_side_widget(self._replay_readouts, minimum_width=345)
        replay_layout.addWidget(self.replay_plot, 1)
        self._views.addTab(replay_page, "Replay")
        self._views.currentChanged.connect(self._view_changed)

        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self.session_label)
        layout.addWidget(self._views, 1)

        self._replay_timer = QTimer(self)
        self._replay_timer.setInterval(100)
        self._replay_timer.timeout.connect(self._advance_replay)
        self._play_button.clicked.connect(self._toggle_replay)
        self._cursor_slider.valueChanged.connect(self._slider_changed)
        self.replay_plot.cursor_changed.connect(self._cursor_changed)

        self.controller.acquisition_started.connect(self._started)
        self.controller.acquisition_stopped.connect(self._stopped)
        self.controller.probe_states.connect(self._show_probes)
        self.controller.error.connect(self._show_error)
        self.controller.status.connect(self.status_label.setText)
        self._refresh_replay_sessions()

    def _view_changed(self, index: int) -> None:
        self.labels_button.setEnabled(index == 0)

    def _configure_labels(self) -> None:
        dialog = ProbeLabelsDialog(self.controller.probe_labels(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            for address, label in dialog.labels():
                self.controller.set_probe_label(address, label)
        except Exception as exc:
            self._show_error(f"{type(exc).__name__}: {exc}")
            return
        self.status_label.setText("Probe labels saved.")

    def _started(self, session_path) -> None:
        self.session_label.setText(f"Session: {session_path}")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.live_plot.reset_live()
        self.table.setRowCount(0)
        self.app_state.set_active_session(session_path)
        self.app_state.set_selected_session(session_path)
        self.app_state.set_acquisition_running(True)
        self.app_state.refresh_sessions()
        self._refresh_replay_sessions(select_path=session_path)

    def _stopped(self, session_path) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Acquisition stopped")
        self.app_state.set_acquisition_running(False)
        self.app_state.set_active_session(None)
        self.app_state.set_selected_session(session_path)
        self.app_state.refresh_sessions()
        self._refresh_replay_sessions(select_path=session_path)

    def _show_error(self, message: str) -> None:
        self.status_label.setText(f"Acquisition error: {message}")

    def _show_probes(self, readings) -> None:
        self.live_plot.add_live_readings(readings)
        self.table.setRowCount(len(readings))
        for row, reading in enumerate(readings):
            values = (
                reading.friendly_name,
                reading.address,
                _display_f(reading.food_temperature_c),
                _display_f(reading.ambient_temperature_c),
                _display_f(reading.tip_1_temperature_c),
                _display_f(reading.tip_2_temperature_c),
                _display_f(reading.tip_3_temperature_c),
                _display_f(reading.tip_4_temperature_c),
                _display(reading.rssi),
                _display(reading.battery_percent),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row, column, item)

    def _refresh_replay_sessions(self, select_path: Path | None = None) -> None:
        selected_path = Path(select_path) if select_path is not None else None
        previous = self._replay_sessions.currentData()
        if selected_path is None and previous is not None:
            selected_path = Path(previous)
        self._replay_sessions.clear()
        for session_path in self.app_state.session_store.sessions():
            try:
                manifest = load_manifest(session_path, validate_files=False)
                display = f"{manifest.name} ({session_path.name})"
            except Exception:
                display = session_path.name
            self._replay_sessions.addItem(display, str(session_path))
        if selected_path is not None:
            index = self._replay_sessions.findData(str(selected_path))
            if index >= 0:
                self._replay_sessions.setCurrentIndex(index)

    def _load_replay(self) -> None:
        selected = self._replay_sessions.currentData()
        if selected is None:
            self.status_label.setText("No recorded sessions are available.")
            return
        self._pause_replay()
        try:
            recorded = load_recorded_experiment(Path(selected))
            entries = []
            for probe_index, probe in enumerate(recorded.probes):
                for series_index, series in enumerate(probe.series):
                    metric = REPLAY_METRICS.get(series.name.strip().lower())
                    if metric is None:
                        continue
                    label, unit, group = metric
                    entries.append(
                        {
                            "key": f"{probe_index}:{series_index}:{series.name}",
                            "label": f"{probe.friendly_name} · {label}",
                            "unit": unit,
                            "group": group,
                            "x": probe.time_seconds,
                            "y": series.values,
                        }
                    )
            self._replay_plot_started_at = _parse_datetime(
                recorded.experiment.manifest.started_at_utc
            )
            self.replay_plot.set_replay_series(entries)
            duration = self.replay_plot.replay_duration
            self._cursor_slider.setEnabled(duration > 0)
            self._views.setCurrentIndex(1)
            self.status_label.setText(
                f"Loaded replay: {recorded.experiment.manifest.name}"
            )
        except Exception as exc:
            self._show_error(f"Replay load failed: {type(exc).__name__}: {exc}")

    def _toggle_replay(self) -> None:
        if self._replay_timer.isActive():
            self._pause_replay()
            return
        if self.replay_plot.replay_duration <= 0:
            return
        if self.replay_plot.replay_cursor >= self.replay_plot.replay_duration:
            self.replay_plot.set_replay_cursor(self.replay_plot.replay_start)
        self._replay_last_tick = time.monotonic()
        self._replay_timer.start()
        self._play_button.setText("Pause")

    def _pause_replay(self) -> None:
        self._replay_timer.stop()
        self._play_button.setText("Play")

    def _advance_replay(self) -> None:
        now = time.monotonic()
        elapsed = now - self._replay_last_tick
        self._replay_last_tick = now
        speed = float(self._speed.currentData() or 1.0)
        cursor = self.replay_plot.replay_cursor + elapsed * speed
        if cursor >= self.replay_plot.replay_duration:
            cursor = self.replay_plot.replay_duration
            self.replay_plot.set_replay_cursor(cursor)
            self._pause_replay()
        else:
            self.replay_plot.set_replay_cursor(cursor)

    def _slider_changed(self, value: int) -> None:
        duration = self.replay_plot.replay_duration
        if duration <= 0:
            return
        self.replay_plot.set_replay_cursor(duration * value / 10000.0)

    def _cursor_changed(self, elapsed_seconds: float) -> None:
        duration = self.replay_plot.replay_duration
        slider_value = round(10000 * elapsed_seconds / duration) if duration else 0
        self._cursor_slider.blockSignals(True)
        self._cursor_slider.setValue(slider_value)
        self._cursor_slider.blockSignals(False)
        elapsed_text = _format_elapsed(elapsed_seconds)
        absolute = None
        if self._replay_plot_started_at is not None:
            absolute = (
                self._replay_plot_started_at + timedelta(seconds=elapsed_seconds)
            ).astimezone().isoformat(timespec="microseconds")
        self._cursor_label.setText(
            f"Cursor: {elapsed_text}" + (f" · {absolute}" if absolute else "")
        )
        readouts = self.replay_plot.replay_readouts()
        self._replay_readouts.setRowCount(len(readouts))
        for row, (label, sample_time, value, unit) in enumerate(readouts):
            time_text = _format_elapsed(sample_time)
            self._replay_readouts.setItem(row, 0, QTableWidgetItem(label))
            self._replay_readouts.setItem(row, 1, QTableWidgetItem(time_text))
            self._replay_readouts.setItem(
                row, 2, QTableWidgetItem(f"{value!r} {unit}")
            )


def _parse_datetime(value: str) -> datetime:
    if value.endswith(("Z", "z")):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _format_elapsed(seconds: float) -> str:
    total_microseconds = round(seconds * 1_000_000)
    whole_seconds, micros = divmod(total_microseconds, 1_000_000)
    hours, remainder = divmod(whole_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{micros:06d}"


def _display(value) -> str:
    return "—" if value is None else f"{value:g}"


def _display_f(value) -> str:
    return "—" if value is None else f"{value * 9.0 / 5.0 + 32.0:.1f}"
