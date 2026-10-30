from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.engineering_state import EngineeringState
from gui.session_store import SessionStore


class AppState(QObject):
    """
    Qt-facing wrapper around the platform's EngineeringState.

    The underlying engineering data does not depend on Qt.
    """

    session_changed = Signal(object)
    session_root_changed = Signal(object)
    sessions_changed = Signal()

    acquisition_state_changed = Signal(bool)
    acquisition_session_changed = Signal(object)
    live_probes_changed = Signal(object)

    calibration_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()

        self.engineering = EngineeringState()
        self.session_store = SessionStore()

        self._calibration = None

    @property
    def selected_session(self) -> Path | None:
        return self.engineering.selected_session

    @property
    def active_session(self) -> Path | None:
        return self.engineering.active_session

    @property
    def acquisition_running(self) -> bool:
        return self.engineering.acquisition_running

    @property
    def calibration(self):
        return self._calibration

    def set_session_root(
        self,
        path: Path,
    ) -> None:

        self.session_store.set_root(path)

        self.engineering.selected_session = None

        self.session_root_changed.emit(path)
        self.sessions_changed.emit()
        self.session_changed.emit(None)

    def set_selected_session(
        self,
        path: Path | None,
    ) -> None:

        self.engineering.selected_session = path

        self.session_changed.emit(path)

    def set_active_session(
        self,
        path: Path | None,
    ) -> None:

        self.engineering.active_session = path

        self.acquisition_session_changed.emit(path)

    def set_acquisition_running(
        self,
        running: bool,
    ) -> None:

        self.engineering.acquisition_running = running

        self.acquisition_state_changed.emit(
            running
        )

    def set_live_probes(
        self,
        probes,
    ) -> None:

        self.engineering.live_probes = tuple(
            probes
        )

        self.live_probes_changed.emit(
            self.engineering.live_probes
        )

    def refresh_sessions(self) -> None:
        self.sessions_changed.emit()

    def set_calibration(
        self,
        calibration,
    ) -> None:

        self._calibration = calibration
        self.calibration_changed.emit(
            calibration
        )
