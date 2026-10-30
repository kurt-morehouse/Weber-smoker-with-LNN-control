from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from core.engineering_notebook import (
    EngineeringNotebookPage,
    attach_photos,
    load_notebook,
    render_markdown,
    save_markdown,
    save_notebook,
)
from gui.app_state import AppState


class EngineeringNotebookTab(QWidget):
    """
    OneNote-inspired engineering notebook.

    Left side: experiment pages.
    Right side: editable page with section tabs, photo attachments and preview.

    All narrative fields are QTextEdit widgets, so Return/Enter creates real
    new lines. Nothing here writes to the acquisition CSV files.
    """

    def __init__(self, app_state: AppState) -> None:
        super().__init__()

        self._state = app_state
        self._session: Path | None = None
        self._page: EngineeringNotebookPage | None = None
        self._dirty = False

        # -------- Notebook / page list --------
        self._page_list = QListWidget()
        self._page_list.currentItemChanged.connect(
            self._page_selected
        )

        self._refresh_button = QPushButton("Refresh Pages")
        self._refresh_button.clicked.connect(self._refresh_pages)

        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Engineering Notebook"))
        left_layout.addWidget(self._page_list, stretch=1)
        left_layout.addWidget(self._refresh_button)
        left.setLayout(left_layout)

        # -------- Page header --------
        self._title = QLineEdit()
        self._title.textChanged.connect(self._mark_dirty)

        self._status = QLabel("Select an experiment page.")
        self._status.setWordWrap(True)

        header_form = QFormLayout()
        header_form.addRow("Page title:", self._title)

        # -------- Editable sections --------
        self._objective = self._editor()
        self._hardware = self._editor()
        self._modifications = self._editor()
        self._conditions = self._editor()
        self._acquisition = self._editor()
        self._analysis = self._editor()
        self._observations = self._editor()
        self._conclusions = self._editor()
        self._next_actions = self._editor()
        self._tags = QLineEdit()
        self._tags.textChanged.connect(self._mark_dirty)

        self._sections = QTabWidget()
        self._sections.addTab(
            self._section_page(
                ("Objective", self._objective),
                ("Hardware configuration", self._hardware),
                ("Modifications", self._modifications),
                ("Test conditions", self._conditions),
            ),
            "Setup",
        )
        self._sections.addTab(
            self._section_page(
                ("Acquisition summary", self._acquisition),
                ("Analysis highlights", self._analysis),
            ),
            "Data & Analysis",
        )
        self._sections.addTab(
            self._section_page(
                ("Observations", self._observations),
                ("Conclusions", self._conclusions),
                ("Next actions", self._next_actions),
            ),
            "Findings",
        )

        # -------- Photos --------
        self._photo_list = QListWidget()
        self._photo_list.currentItemChanged.connect(
            self._photo_selected
        )

        self._photo_preview = QLabel("No photo selected")
        self._photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._photo_preview.setMinimumHeight(260)
        self._photo_preview.setWordWrap(True)

        self._attach_button = QPushButton("Attach Photos")
        self._attach_button.clicked.connect(self._attach_photos)

        photos_page = QWidget()
        photos_layout = QVBoxLayout()
        photos_layout.addWidget(self._attach_button)
        photos_layout.addWidget(self._photo_list)
        photos_layout.addWidget(self._photo_preview, stretch=1)
        photos_page.setLayout(photos_layout)
        self._sections.addTab(photos_page, "Photos")

        # -------- Rendered page preview --------
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)

        preview_page = QWidget()
        preview_layout = QVBoxLayout()
        preview_layout.addWidget(
            QLabel(
                "Notebook page preview. This is regenerated from the "
                "editable sections when you save."
            )
        )
        preview_layout.addWidget(self._preview, stretch=1)
        preview_page.setLayout(preview_layout)
        self._sections.addTab(preview_page, "Page Preview")

        # -------- Actions --------
        self._save_button = QPushButton("Save Page")
        self._save_button.clicked.connect(self._save_page)

        self._export_button = QPushButton("Export Markdown")
        self._export_button.clicked.connect(self._export_markdown)

        self._autofill_button = QPushButton("Auto-Fill Known Data")
        self._autofill_button.clicked.connect(self._autofill)

        actions = QHBoxLayout()
        actions.addWidget(self._save_button)
        actions.addWidget(self._autofill_button)
        actions.addWidget(self._export_button)
        actions.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(self._status)
        right_layout.addLayout(header_form)
        right_layout.addWidget(self._sections, stretch=1)
        right_layout.addLayout(actions)
        right.setLayout(right_layout)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 940])

        layout = QVBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

        self._state.sessions_changed.connect(self._refresh_pages)
        self._state.session_root_changed.connect(
            lambda _path: self._refresh_pages()
        )
        self._state.session_changed.connect(
            self._select_session_from_state
        )

        self._set_editing_enabled(False)
        self._refresh_pages()

    def _editor(self) -> QTextEdit:
        editor = QTextEdit()
        editor.setAcceptRichText(False)
        editor.setMinimumHeight(95)
        editor.textChanged.connect(self._mark_dirty)
        return editor

    def _section_page(self, *fields) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        for label, editor in fields:
            heading = QLabel(f"<b>{label}</b>")
            layout.addWidget(heading)
            layout.addWidget(editor)

        layout.addStretch(1)
        widget.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)

        page = QWidget()
        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        page.setLayout(page_layout)
        return page

    def _set_editing_enabled(self, enabled: bool) -> None:
        self._title.setEnabled(enabled)
        self._sections.setEnabled(enabled)
        self._save_button.setEnabled(enabled)
        self._export_button.setEnabled(enabled)
        self._autofill_button.setEnabled(enabled)
        self._attach_button.setEnabled(enabled)
        self._tags.setEnabled(enabled)

    def _refresh_pages(self) -> None:
        selected = self._session

        self._page_list.blockSignals(True)
        self._page_list.clear()

        sessions = self._state.session_store.sessions()

        for session in sessions:
            item = QListWidgetItem(session.name)
            item.setData(Qt.ItemDataRole.UserRole, session)
            self._page_list.addItem(item)

        self._page_list.blockSignals(False)

        target = selected or self._state.selected_session
        if target is not None:
            self._select_list_item(target)
        elif self._page_list.count():
            self._page_list.setCurrentRow(0)

    def _select_list_item(self, session: Path) -> None:
        for index in range(self._page_list.count()):
            item = self._page_list.item(index)
            if Path(item.data(Qt.ItemDataRole.UserRole)) == Path(session):
                self._page_list.setCurrentRow(index)
                return

    def _select_session_from_state(self, session) -> None:
        if session is not None:
            self._select_list_item(Path(session))

    def _page_selected(self, current, previous) -> None:
        if current is None:
            return

        if self._dirty and previous is not None:
            answer = QMessageBox.question(
                self,
                "Unsaved notebook changes",
                "Save changes to the current notebook page before switching?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )

            if answer == QMessageBox.StandardButton.Cancel:
                self._page_list.blockSignals(True)
                self._page_list.setCurrentItem(previous)
                self._page_list.blockSignals(False)
                return

            if answer == QMessageBox.StandardButton.Save:
                self._save_page()

        session = Path(current.data(Qt.ItemDataRole.UserRole))
        self._load_page(session)

    def _load_page(self, session: Path) -> None:
        self._session = session
        self._page = load_notebook(session)

        self._block_editor_signals(True)

        page = self._page
        self._title.setText(page.title)
        self._objective.setPlainText(page.objective)
        self._hardware.setPlainText(page.hardware_configuration)
        self._modifications.setPlainText(page.modifications)
        self._conditions.setPlainText(page.test_conditions)
        self._acquisition.setPlainText(page.acquisition_summary)
        self._analysis.setPlainText(page.analysis_highlights)
        self._observations.setPlainText(page.observations)
        self._conclusions.setPlainText(page.conclusions)
        self._next_actions.setPlainText(page.next_actions)
        self._tags.setText(", ".join(page.tags))

        self._block_editor_signals(False)

        self._refresh_photo_list()
        self._refresh_preview()
        self._dirty = False
        self._set_editing_enabled(True)
        self._status.setText(
            f"Page: {session.name} — saved notebook is independent "
            "of raw acquisition CSV data."
        )

        if self._state.selected_session != session:
            self._state.set_selected_session(session)

    def _block_editor_signals(self, block: bool) -> None:
        widgets = [
            self._title,
            self._objective,
            self._hardware,
            self._modifications,
            self._conditions,
            self._acquisition,
            self._analysis,
            self._observations,
            self._conclusions,
            self._next_actions,
            self._tags,
        ]
        for widget in widgets:
            widget.blockSignals(block)

    def _mark_dirty(self, *_args) -> None:
        if self._session is None:
            return
        self._dirty = True
        self._status.setText(
            f"Page: {self._session.name} — unsaved changes"
        )

    def _collect_page(self) -> EngineeringNotebookPage:
        if self._page is None:
            raise RuntimeError("No notebook page is loaded.")

        return EngineeringNotebookPage(
            title=self._title.text().strip(),
            objective=self._objective.toPlainText().rstrip(),
            hardware_configuration=self._hardware.toPlainText().rstrip(),
            modifications=self._modifications.toPlainText().rstrip(),
            test_conditions=self._conditions.toPlainText().rstrip(),
            acquisition_summary=self._acquisition.toPlainText().rstrip(),
            analysis_highlights=self._analysis.toPlainText().rstrip(),
            observations=self._observations.toPlainText().rstrip(),
            conclusions=self._conclusions.toPlainText().rstrip(),
            next_actions=self._next_actions.toPlainText().rstrip(),
            tags=[
                item.strip()
                for item in self._tags.text().split(",")
                if item.strip()
            ],
            photos=list(self._page.photos),
            created_utc=self._page.created_utc,
            updated_utc=self._page.updated_utc,
        )

    def _save_page(self) -> None:
        if self._session is None:
            return

        try:
            self._page = self._collect_page()
            path = save_notebook(self._session, self._page)
            save_markdown(self._session, self._page)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Notebook save failed",
                f"{type(exc).__name__}: {exc}",
            )
            return

        self._dirty = False
        self._refresh_preview()
        self._status.setText(f"Saved: {path}")

    def _export_markdown(self) -> None:
        if self._session is None:
            return

        if self._dirty:
            self._save_page()

        path = save_markdown(self._session, self._page)
        self._status.setText(f"Markdown page written: {path}")

    def _attach_photos(self) -> None:
        if self._session is None or self._page is None:
            return

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach Experiment Photos",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.heic);;All Files (*)",
        )

        if not files:
            return

        try:
            attached = attach_photos(
                self._session,
                [Path(item) for item in files],
            )
            self._page.photos.extend(attached)
            self._dirty = True
            self._refresh_photo_list()
            self._save_page()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Photo attachment failed",
                f"{type(exc).__name__}: {exc}",
            )

    def _refresh_photo_list(self) -> None:
        self._photo_list.clear()
        self._photo_preview.setText("No photo selected")
        self._photo_preview.setPixmap(QPixmap())

        if self._page is None:
            return

        for relative_path in self._page.photos:
            item = QListWidgetItem(Path(relative_path).name)
            item.setData(Qt.ItemDataRole.UserRole, relative_path)
            self._photo_list.addItem(item)

    def _photo_selected(self, current, _previous) -> None:
        if current is None or self._session is None:
            return

        relative = current.data(Qt.ItemDataRole.UserRole)
        path = self._session / relative

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._photo_preview.setText(
                f"Preview unavailable for:\n{path.name}"
            )
            self._photo_preview.setPixmap(QPixmap())
            return

        scaled = pixmap.scaled(
            700,
            420,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._photo_preview.setPixmap(scaled)
        self._photo_preview.setText("")

    def _autofill(self) -> None:
        if self._session is None:
            return

        manifest_path = self._session / "manifest.json"
        session_path = self._session / "session.json"
        calibration_path = self._session / "thermal_calibration.json"

        acquisition_lines = []
        analysis_lines = []

        for path in (manifest_path, session_path):
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

            if path.name == "manifest.json":
                experiment_id = data.get("experiment_id")
                started = data.get("started_at_utc")
                ended = data.get("ended_at_utc")
                probes = data.get("probes", [])

                if experiment_id:
                    acquisition_lines.append(
                        f"Experiment ID: {experiment_id}"
                    )
                if started:
                    acquisition_lines.append(f"Started UTC: {started}")
                if ended:
                    acquisition_lines.append(f"Ended UTC: {ended}")
                if probes:
                    acquisition_lines.append(
                        f"Configured probes: {len(probes)}"
                    )

        if calibration_path.exists():
            try:
                data = json.loads(
                    calibration_path.read_text(encoding="utf-8")
                )
                mapping = (
                    ("source_probe", "Calibration probe"),
                    ("source_channel", "Calibration channel"),
                    ("heater_power_w", "Heater power (W)"),
                    ("equilibrium_temperature_f", "Fitted equilibrium (°F)"),
                    ("time_constant_seconds", "Time constant (s)"),
                    ("fit_r_squared", "Fit R²"),
                    ("heat_loss_coefficient_w_per_f", "K heat loss (W/°F)"),
                    (
                        "effective_thermal_capacitance_j_per_f",
                        "C effective thermal mass (J/°F)",
                    ),
                )
                for key, label in mapping:
                    if key in data:
                        analysis_lines.append(
                            f"{label}: {data[key]}"
                        )
            except Exception:
                pass

        if acquisition_lines:
            existing = self._acquisition.toPlainText().strip()
            generated = "\n".join(acquisition_lines)
            self._acquisition.setPlainText(
                f"{existing}\n\n{generated}".strip()
            )

        if analysis_lines:
            existing = self._analysis.toPlainText().strip()
            generated = "\n".join(analysis_lines)
            self._analysis.setPlainText(
                f"{existing}\n\n{generated}".strip()
            )

        self._mark_dirty()

    def _refresh_preview(self) -> None:
        if self._session is None or self._page is None:
            self._preview.clear()
            return

        try:
            page = self._collect_page()
        except Exception:
            page = self._page

        self._preview.setPlainText(
            render_markdown(self._session, page)
        )
