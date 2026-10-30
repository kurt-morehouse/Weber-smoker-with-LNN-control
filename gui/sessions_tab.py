from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.experiment_notes import (
    ExperimentNotes,
    load_experiment_notes,
    save_experiment_notes,
)
from core.experiment_reader import RecordedExperiment, load_recorded_experiment
from core.thermal_analysis import estimate_full_power_response
from core.calibration import calibration_from_power_estimate
from core.calibration_store import calibration_path, save_calibration
from core.experiment_comparison import compare_calibrations
from core.model_validation import validate_baseline_model_against_experiment
from gui.app_state import AppState
from gui.experiment_plot import ExperimentPlot


class SessionsTab(QWidget):
    def __init__(self, app_state: AppState) -> None:
        super().__init__()
        self._state = app_state
        self._current_recorded: RecordedExperiment | None = None
        self._current_estimate = None

        self._list = QListWidget()
        self._refresh_sessions_button = QPushButton("Refresh Sessions")
        self._choose_root_button = QPushButton("Choose Session Root")

        self._experiment_name = QLabel("No experiment selected")
        self._experiment_name.setStyleSheet("font-weight: bold;")
        self._summary = QLabel("")
        self._last_refresh = QLabel("Last refreshed: ---")
        self._refresh_graph_button = QPushButton("Refresh Graph")
        self._refresh_graph_button.setEnabled(False)

        self._plot = ExperimentPlot()

        self._stats = QTableWidget()
        self._stats.setColumnCount(5)
        self._stats.setHorizontalHeaderLabels(
            ["Probe / Channel", "Current (°F)", "Min (°F)", "Max (°F)", "Samples"]
        )
        self._stats.setMaximumHeight(160)
        self._stats.setEditTriggers(QTableWidget.NoEditTriggers)
        self._stats.setSelectionBehavior(QTableWidget.SelectRows)
        self._stats.horizontalHeader().setStretchLastSection(True)

        # -------- Engineering analysis --------
        self._analysis_channel = QComboBox()

        self._heater_watts = QDoubleSpinBox()
        self._heater_watts.setRange(1.0, 10000.0)
        self._heater_watts.setDecimals(0)
        self._heater_watts.setValue(1100.0)
        self._heater_watts.setSuffix(" W")

        self._target_f = QDoubleSpinBox()
        self._target_f.setRange(-100.0, 1000.0)
        self._target_f.setDecimals(1)
        self._target_f.setValue(225.0)
        self._target_f.setSuffix(" °F")

        self._outside_f = QDoubleSpinBox()
        self._outside_f.setRange(-100.0, 200.0)
        self._outside_f.setDecimals(1)
        self._outside_f.setValue(75.0)
        self._outside_f.setSuffix(" °F")

        self._analyze_button = QPushButton("Analyze Full-Power Run")
        self._analyze_button.setEnabled(False)

        self._save_calibration_button = QPushButton("Save Calibration")
        self._save_calibration_button.setEnabled(False)

        self._analysis_output = QTextEdit()
        self._analysis_output.setReadOnly(True)

        analysis_form = QFormLayout()
        analysis_form.addRow("Temperature channel:", self._analysis_channel)
        analysis_form.addRow("Test heater power:", self._heater_watts)
        analysis_form.addRow("Target chamber:", self._target_f)
        analysis_form.addRow("Outside ambient:", self._outside_f)

        analysis_page = QWidget()
        analysis_layout = QVBoxLayout()
        analysis_layout.addLayout(analysis_form)
        analysis_layout.addWidget(self._analyze_button)
        analysis_layout.addWidget(self._save_calibration_button)
        analysis_layout.addWidget(self._analysis_output, stretch=1)
        analysis_page.setLayout(analysis_layout)

        # -------- Experiment comparison / validation --------
        self._baseline_session = QComboBox()
        self._modified_session = QComboBox()

        self._comparison_target_f = QDoubleSpinBox()
        self._comparison_target_f.setRange(-100.0, 1000.0)
        self._comparison_target_f.setValue(225.0)
        self._comparison_target_f.setSuffix(" °F")

        self._comparison_outside_f = QDoubleSpinBox()
        self._comparison_outside_f.setRange(-100.0, 200.0)
        self._comparison_outside_f.setValue(75.0)
        self._comparison_outside_f.setSuffix(" °F")

        self._compare_button = QPushButton("Compare Experiments")
        self._compare_button.setEnabled(False)

        self._comparison_output = QTextEdit()
        self._comparison_output.setReadOnly(True)

        comparison_form = QFormLayout()
        comparison_form.addRow("Experiment A — baseline:", self._baseline_session)
        comparison_form.addRow("Experiment B — modified:", self._modified_session)
        comparison_form.addRow("Target:", self._comparison_target_f)
        comparison_form.addRow("Outside ambient:", self._comparison_outside_f)

        comparison_page = QWidget()
        comparison_layout = QVBoxLayout()
        comparison_layout.addLayout(comparison_form)
        comparison_layout.addWidget(self._compare_button)
        comparison_layout.addWidget(self._comparison_output, stretch=1)
        comparison_page.setLayout(comparison_layout)

        # -------- Experiment notes --------
        self._description = QTextEdit()
        self._objective = QTextEdit()
        self._results = QTextEdit()
        self._conclusions = QTextEdit()
        self._tags = QTextEdit()
        self._save_notes_button = QPushButton("Save Experiment Notes")
        self._save_notes_button.setEnabled(False)

        notes_form = QFormLayout()
        notes_form.addRow("Description:", self._description)
        notes_form.addRow("Objective:", self._objective)
        notes_form.addRow("Results:", self._results)
        notes_form.addRow("Conclusions:", self._conclusions)
        notes_form.addRow("Tags (comma separated):", self._tags)

        notes_page = QWidget()
        notes_layout = QVBoxLayout()
        notes_layout.addLayout(notes_form)
        notes_layout.addWidget(self._save_notes_button)
        notes_page.setLayout(notes_layout)

        self._details_tabs = QTabWidget()
        self._details_tabs.addTab(analysis_page, "Thermal / Power Analysis")
        self._details_tabs.addTab(comparison_page, "Compare / Validate")
        self._details_tabs.addTab(notes_page, "Experiment Notes")
        self._details_tabs.setMinimumHeight(250)

        self._refresh_sessions_button.clicked.connect(self.refresh_sessions)
        self._refresh_graph_button.clicked.connect(self.refresh_graph)
        self._choose_root_button.clicked.connect(self.choose_session_root)
        self._list.currentRowChanged.connect(self._selection_changed)
        self._analyze_button.clicked.connect(self._analyze_current)
        self._save_calibration_button.clicked.connect(self._save_calibration)
        self._compare_button.clicked.connect(self._compare_experiments)
        self._save_notes_button.clicked.connect(self._save_notes)

        self._state.sessions_changed.connect(self.refresh_sessions)
        self._state.session_root_changed.connect(self._session_root_changed)

        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Experiments"))
        left_layout.addWidget(self._list, stretch=1)
        left_layout.addWidget(self._refresh_sessions_button)
        left_layout.addWidget(self._choose_root_button)
        left.setLayout(left_layout)
        left.setMinimumWidth(210)
        left.setMaximumWidth(320)

        header = QHBoxLayout()
        header.addWidget(self._experiment_name)
        header.addSpacing(12)
        header.addWidget(self._summary)
        header.addStretch()
        header.addWidget(self._last_refresh)
        header.addWidget(self._refresh_graph_button)

        right = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addLayout(header)
        right_layout.addWidget(self._plot, stretch=3)
        right_layout.addWidget(self._stats)
        right_layout.addWidget(self._details_tabs, stretch=2)
        right.setLayout(right_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 960])

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)
        self.refresh_sessions()

    def refresh_sessions(self) -> None:
        selected = self._state.selected_session
        sessions = self._state.session_store.sessions()
        self._populate_comparison_sessions(sessions)

        self._list.blockSignals(True)
        self._list.clear()
        selected_row = -1

        for index, session in enumerate(sessions):
            self._list.addItem(session.name)
            if session == selected:
                selected_row = index

        if selected_row >= 0:
            self._list.setCurrentRow(selected_row)

        self._list.blockSignals(False)

        if selected is not None and selected.exists():
            self._load_experiment(selected)

    def choose_session_root(self) -> None:
        current_root = self._state.session_store.root
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Experiment Root", str(current_root)
        )
        if folder:
            self._state.set_session_root(Path(folder))

    def _selection_changed(self, row: int) -> None:
        sessions = self._state.session_store.sessions()
        if row < 0 or row >= len(sessions):
            return
        session = sessions[row]
        self._state.set_selected_session(session)
        self._load_experiment(session)

    def refresh_graph(self) -> None:
        session = self._state.selected_session
        if session is not None:
            self._load_experiment(session)

    def _load_experiment(self, session: Path) -> None:
        self._refresh_graph_button.setEnabled(False)

        try:
            recorded = load_recorded_experiment(session)
        except Exception as exc:
            self._current_recorded = None
            self._experiment_name.setText("Experiment load failed")
            self._summary.setText(f"{type(exc).__name__}: {exc}")
            self._stats.setRowCount(0)
            self._plot.clear()
            self._analysis_channel.clear()
            self._analyze_button.setEnabled(False)
            self._save_notes_button.setEnabled(False)
            print("Experiment load failed:", repr(exc))
            return

        self._current_recorded = recorded
        self._current_estimate = None
        self._save_calibration_button.setEnabled(False)
        manifest = recorded.experiment.manifest
        self._experiment_name.setText(manifest.name)

        sample_count = self._sample_count(recorded)
        duration = self._duration_seconds(recorded)
        self._summary.setText(f"{sample_count:,} samples   |   {duration:.0f} s")

        self._plot.display(recorded)
        self._update_statistics(recorded)
        self._populate_analysis_channels(recorded)
        self._load_notes(session)

        self._last_refresh.setText(
            "Refreshed " + datetime.now().strftime("%H:%M:%S")
        )
        self._refresh_graph_button.setEnabled(True)
        self._analyze_button.setEnabled(self._analysis_channel.count() > 0)
        self._save_notes_button.setEnabled(True)

    def _populate_analysis_channels(self, recorded: RecordedExperiment) -> None:
        previous = self._analysis_channel.currentText()
        self._analysis_channel.clear()

        for probe_index, probe in enumerate(recorded.probes):
            for series_index, series in enumerate(probe.series):
                if not series.name.lower().endswith("_f"):
                    continue
                label = f"{probe.friendly_name} — {series.name}"
                self._analysis_channel.addItem(label, (probe_index, series_index))

        if previous:
            index = self._analysis_channel.findText(previous)
            if index >= 0:
                self._analysis_channel.setCurrentIndex(index)

    def _analyze_current(self) -> None:
        recorded = self._current_recorded
        selection = self._analysis_channel.currentData()

        if recorded is None or selection is None:
            return

        probe_index, series_index = selection
        probe = recorded.probes[probe_index]
        series = probe.series[series_index]

        times = []
        values = []
        for t, value in zip(probe.time_seconds, series.values):
            if value is not None:
                times.append(t)
                values.append(value)

        try:
            estimate = estimate_full_power_response(
                times,
                values,
                heater_power_w=self._heater_watts.value(),
                target_temperature_f=self._target_f.value(),
                outside_temperature_f=self._outside_f.value(),
            )
        except Exception as exc:
            self._analysis_output.setPlainText(
                f"Analysis failed: {type(exc).__name__}: {exc}"
            )
            return

        tau_hours = estimate.time_constant_seconds / 3600.0

        lines = [
            f"Channel: {self._analysis_channel.currentText()}",
            "",
            f"Estimated equilibrium: {estimate.equilibrium_temperature_f:.1f} °F",
            f"Estimated thermal time constant: {tau_hours:.2f} h",
            f"Fit quality R²: {estimate.r_squared:.4f}",
            "",
            f"Test heater: {estimate.heater_power_w:.0f} W",
            f"Outside ambient assumption: {estimate.outside_temperature_f:.1f} °F",
            f"Target chamber: {estimate.target_temperature_f:.1f} °F",
        ]

        if estimate.estimated_required_power_w is None:
            lines += ["", "Required heater power could not be estimated."]
        else:
            extra = estimate.additional_power_w or 0.0
            lines += [
                "",
                f"Estimated power for target: {estimate.estimated_required_power_w:.0f} W",
                f"Estimated power margin vs test: {extra:+.0f} W",
            ]

        lines += [
            "",
            "Assumptions:",
            "• Heater was at full power during the fitted heating period.",
            "• Heat loss is approximated as linear with temperature rise.",
            "• Selected channel represents chamber temperature.",
            "• This is an engineering estimate, not an electrical safety rating.",
        ]

        self._current_estimate = estimate
        self._save_calibration_button.setEnabled(True)
        self._analysis_output.setPlainText("\n".join(lines))

    def _save_calibration(self) -> None:
        recorded = self._current_recorded
        estimate = self._current_estimate
        session = self._state.selected_session
        selection = self._analysis_channel.currentData()

        if recorded is None or estimate is None or session is None or selection is None:
            return

        probe_index, series_index = selection
        probe = recorded.probes[probe_index]
        series = probe.series[series_index]

        try:
            calibration = calibration_from_power_estimate(
                estimate=estimate,
                source_session=session,
                source_probe=probe.friendly_name,
                source_channel=series.name,
            )
            path = save_calibration(session, calibration)
        except Exception as exc:
            self._analysis_output.append(
                f"\nCalibration save failed: {type(exc).__name__}: {exc}"
            )
            return

        self._populate_comparison_sessions(self._state.session_store.sessions())
        self._analysis_output.append(
            "\nCALIBRATION SAVED"
            f"\n{path}"
            f"\nK = {calibration.heat_loss_coefficient_w_per_f:.3f} W/°F"
            f"\nC = {calibration.effective_thermal_capacitance_j_per_f:,.0f} J/°F"
        )

    def _populate_comparison_sessions(self, sessions) -> None:
        self._baseline_session.clear()
        self._modified_session.clear()

        calibrated = [
            session for session in sessions
            if calibration_path(session).exists()
        ]

        for session in calibrated:
            self._baseline_session.addItem(session.name, session)
            self._modified_session.addItem(session.name, session)

        if len(calibrated) >= 2:
            self._modified_session.setCurrentIndex(1)

        self._compare_button.setEnabled(len(calibrated) >= 2)

    def _compare_experiments(self) -> None:
        baseline = self._baseline_session.currentData()
        modified = self._modified_session.currentData()

        if baseline is None or modified is None:
            return
        if baseline == modified:
            self._comparison_output.setPlainText(
                "Choose two different calibrated experiments."
            )
            return

        try:
            result = compare_calibrations(
                baseline_session=baseline,
                modified_session=modified,
                target_temperature_f=self._comparison_target_f.value(),
                outside_temperature_f=self._comparison_outside_f.value(),
            )
            validation = validate_baseline_model_against_experiment(
                baseline_session=baseline,
                observed_session=modified,
            )
        except Exception as exc:
            self._comparison_output.setPlainText(
                f"Comparison failed: {type(exc).__name__}: {exc}"
            )
            return

        heat_word = "IMPROVEMENT" if result.heat_loss_change_percent < 0 else "INCREASE"
        power_word = "IMPROVEMENT" if result.required_power_change_w < 0 else "INCREASE"

        lines = [
            "EXPERIMENT A/B COMPARISON",
            "=" * 28,
            f"A baseline: {baseline.name}",
            f"B modified: {modified.name}",
            "",
            "HEAT LOSS",
            f"A K: {result.baseline.heat_loss_coefficient_w_per_f:.3f} W/°F",
            f"B K: {result.modified.heat_loss_coefficient_w_per_f:.3f} W/°F",
            f"Change: {result.heat_loss_change_percent:+.1f}% — {heat_word}",
            "",
            "THERMAL RESPONSE",
            f"A tau: {result.baseline.time_constant_seconds / 3600.0:.2f} h",
            f"B tau: {result.modified.time_constant_seconds / 3600.0:.2f} h",
            f"Tau change: {result.time_constant_change_percent:+.1f}%",
            f"Effective capacitance change: {result.capacitance_change_percent:+.1f}%",
            f"Equilibrium change: {result.equilibrium_change_f:+.1f} °F",
            "",
            f"POWER FOR {result.target_temperature_f:.1f} °F",
            f"A required: {result.baseline_required_power_w:.0f} W",
            f"B required: {result.modified_required_power_w:.0f} W",
            f"Change: {result.required_power_change_w:+.0f} W "
            f"({result.required_power_change_percent:+.1f}%) — {power_word}",
            "",
            "OLD-MODEL VALIDATION AGAINST B",
            f"Validation time: {validation.elapsed_seconds / 3600.0:.2f} h",
            f"A-model prediction: {validation.predicted_temperature_f:.1f} °F",
            f"B fitted response: {validation.observed_temperature_f:.1f} °F",
            f"Prediction error: {validation.prediction_error_f:+.1f} °F",
            "",
            "A large A→B error after a hardware modification can be evidence "
            "that the smoker's physical parameters changed; it is not "
            "automatically a model failure.",
        ]
        self._comparison_output.setPlainText("\n".join(lines))

    def _load_notes(self, session: Path) -> None:
        try:
            notes = load_experiment_notes(session)
        except Exception as exc:
            notes = ExperimentNotes(description=f"Notes load error: {exc}")

        self._description.setPlainText(notes.description)
        self._objective.setPlainText(notes.objective)
        self._results.setPlainText(notes.results)
        self._conclusions.setPlainText(notes.conclusions)
        self._tags.setPlainText(", ".join(notes.tags))

    def _save_notes(self) -> None:
        session = self._state.selected_session
        if session is None:
            return

        tags = [
            item.strip()
            for item in self._tags.toPlainText().split(",")
            if item.strip()
        ]

        notes = ExperimentNotes(
            description=self._description.toPlainText().strip(),
            objective=self._objective.toPlainText().strip(),
            results=self._results.toPlainText().strip(),
            conclusions=self._conclusions.toPlainText().strip(),
            tags=tags,
        )

        try:
            save_experiment_notes(session, notes)
        except Exception as exc:
            self._save_notes_button.setText(f"Save failed: {exc}")
            return

        self._save_notes_button.setText("Saved")
        self._save_notes_button.setText("Save Experiment Notes")

    def _update_statistics(self, recorded: RecordedExperiment) -> None:
        rows = []

        for probe in recorded.probes:
            for series in probe.series:
                if not series.name.lower().endswith("_f"):
                    continue

                values = [value for value in series.values if value is not None]
                if not values:
                    continue

                rows.append((
                    f"{probe.friendly_name} — {series.name}",
                    values[-1],
                    min(values),
                    max(values),
                    len(values),
                ))

        self._stats.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            name, current, minimum, maximum, count = row
            display = (
                name,
                f"{current:.1f}",
                f"{minimum:.1f}",
                f"{maximum:.1f}",
                f"{count:,}",
            )
            for column, value in enumerate(display):
                self._stats.setItem(
                    row_index, column, QTableWidgetItem(str(value))
                )

        self._stats.resizeColumnsToContents()

    @staticmethod
    def _sample_count(recorded: RecordedExperiment) -> int:
        if not recorded.probes:
            return 0
        return max(
            (len(probe.time_seconds) for probe in recorded.probes),
            default=0,
        )

    @staticmethod
    def _duration_seconds(recorded: RecordedExperiment) -> float:
        durations = []
        for probe in recorded.probes:
            if len(probe.time_seconds) < 2:
                continue
            durations.append(probe.time_seconds[-1] - probe.time_seconds[0])
        return max(durations, default=0.0)

    def _session_root_changed(self, _path) -> None:
        self.refresh_sessions()
