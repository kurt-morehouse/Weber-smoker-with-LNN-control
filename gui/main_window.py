from dataclasses import replace

from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QToolBar,
)

from acquisition.config import CONFIG
from acquisition.session import SessionManager
from gui.app_state import AppState
from gui.acquisition_controller import AcquisitionController
from gui.acquisition_tab import AcquisitionTab
from gui.sessions_tab import SessionsTab
from gui.simulator_tab import SimulatorTab
from gui.predictions_tab import PredictionsTab
from gui.engineering_notebook_tab import EngineeringNotebookTab


WINDOW_TITLE = "Weber Smoker Engineering Console"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(
            WINDOW_TITLE
        )

        self.resize(
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
        )

        self._state = AppState()

        self._acquisition_controller = (
            AcquisitionController(app_state=self._state)
        )

        # -------------------------------------------------
        # Main experiment workflow toolbar
        # -------------------------------------------------

        workflow_toolbar = QToolBar(
            "Experiment Workflow",
            self,
        )
        workflow_toolbar.setMovable(False)

        self._new_session_button = QPushButton(
            "New Session"
        )
        self._new_session_button.setToolTip(
            "Create the experiment before acquisition so setup "
            "can be documented in the Engineering Notebook."
        )
        self._new_session_button.clicked.connect(
            self._create_new_session
        )

        workflow_toolbar.addWidget(
            self._new_session_button
        )
        self.addToolBar(
            workflow_toolbar
        )

        # -------------------------------------------------
        # Tabs
        # -------------------------------------------------

        self._tabs = QTabWidget()

        self._acquisition_tab = AcquisitionTab(
            app_state=self._state,
            acquisition_controller=
                self._acquisition_controller
        )

        self._sessions_tab = SessionsTab(
            app_state=self._state,
        )

        self._simulator_tab = SimulatorTab(
            app_state=self._state,
        )

        self._predictions_tab = PredictionsTab(
            app_state=self._state,
        )

        self._notebook_tab = EngineeringNotebookTab(
            app_state=self._state,
        )

        self._tabs.addTab(
            self._acquisition_tab,
            "Acquisition",
        )
        self._tabs.addTab(
            self._sessions_tab,
            "Sessions",
        )
        self._tabs.addTab(
            self._simulator_tab,
            "Simulator",
        )
        self._tabs.addTab(
            self._predictions_tab,
            "Predictions",
        )
        self._tabs.addTab(
            self._notebook_tab,
            "Engineering Notebook",
        )

        self.setCentralWidget(
            self._tabs
        )

        self._acquisition_controller.acquisition_started.connect(
            self._acquisition_started
        )
        self._acquisition_controller.acquisition_stopped.connect(
            self._acquisition_stopped
        )
        self._acquisition_controller.probe_states.connect(
            self._probe_states_changed
        )
        self._acquisition_controller.error.connect(
            self._acquisition_error
        )

        self._state.acquisition_state_changed.connect(
            lambda running:
            self._new_session_button.setEnabled(
                not running
            )
        )

    def _create_new_session(
        self,
    ) -> None:
        if self._acquisition_controller.running:
            QMessageBox.warning(
                self,
                "Acquisition running",
                "Stop acquisition before creating another experiment.",
            )
            return

        root = (
            self._state
            .session_store
            .root
        )
        root.mkdir(
            parents=True,
            exist_ok=True,
        )

        config = replace(
            CONFIG,
            sessions_directory=root,
        )

        manager = SessionManager(
            config
        )

        try:
            session = manager.create_prepared_session(
                config.probes
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "New session failed",
                f"{type(exc).__name__}: {exc}",
            )
            return

        # Make the prepared experiment visible everywhere immediately.
        self._state.refresh_sessions()
        self._state.set_selected_session(
            session.directory
        )

        # Go straight to the notebook: define the experiment first.
        self._tabs.setCurrentWidget(
            self._notebook_tab
        )

        self.statusBar().showMessage(
            f"Prepared experiment {session.session_id}. "
            "Document setup, then start acquisition.",
            10000,
        )

    # =====================================================
    # Acquisition events
    # =====================================================

    def _acquisition_started(
        self,
        session_path,
    ) -> None:
        self._state.set_active_session(
            session_path
        )
        self._state.set_acquisition_running(
            True
        )
        self._state.set_selected_session(
            session_path
        )
        self._state.refresh_sessions()

    def _acquisition_stopped(
        self,
        session_path,
    ) -> None:
        self._state.set_acquisition_running(
            False
        )
        self._state.set_active_session(
            None
        )
        self._state.refresh_sessions()
        self._state.set_selected_session(
            session_path
        )

    def _probe_states_changed(
        self,
        readings,
    ) -> None:
        self._state.set_live_probes(
            readings
        )

    def _acquisition_error(
        self,
        message: str,
    ) -> None:
        print(
            "Acquisition error:",
            message,
        )
