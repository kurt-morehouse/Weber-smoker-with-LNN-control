from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QObject,
    Signal,
)

from acquisition.service import (
    AcquisitionService,
    AcquisitionStatus,
)


class AcquisitionBridge(QObject):
    """
    Converts background acquisition callbacks
    into Qt signals.

    Qt automatically queues these signals onto
    the GUI thread.
    """

    status_changed = Signal(
        bool,
        str,
    )

    session_changed = Signal(
        object
    )

    error = Signal(
        str
    )

    acquisition_stopped = Signal()

    def __init__(
        self,
        acquisition_factory,
        stop_callback=None,
        parent=None,
    ) -> None:

        super().__init__(parent)

        self._service = AcquisitionService(
            acquisition_factory=(
                acquisition_factory
            ),
            stop_callback=stop_callback,
            status_callback=(
                self._on_status
            ),
            error_callback=(
                self._on_error
            ),
        )

    @property
    def running(self) -> bool:

        return self._service.running

    def start(self) -> None:

        self._service.start()

    def stop(self) -> None:

        self._service.stop()

    def _on_status(
        self,
        status: AcquisitionStatus,
    ) -> None:

        self.status_changed.emit(
            status.running,
            status.message,
        )

        if (
            status.session_directory
            is not None
        ):

            self.session_changed.emit(
                Path(
                    status.session_directory
                )
            )

        if (
            not status.running
            and status.message
            == "Acquisition stopped."
        ):

            self.acquisition_stopped.emit()

    def _on_error(
        self,
        exc: Exception,
    ) -> None:

        self.error.emit(
            f"{type(exc).__name__}: {exc}"
        )
