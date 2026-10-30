from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from acquisition.acquisition_bridge import AcquisitionBridge
from acquisition.ble_scanner import ChefIqScanner
from acquisition.config import CONFIG
from acquisition.probe_registry import ProbeRegistry
from acquisition.probe_service import ProbeService
from acquisition.recorder import SessionRecorder
from acquisition.session import AcquisitionSession, SessionManager
from core.engineering_state import LiveProbeReading


class AcquisitionController(QObject):
    acquisition_started = Signal(object)
    acquisition_stopped = Signal(object)
    probe_states = Signal(object)
    error = Signal(str)
    status = Signal(str)

    def __init__(self, app_state=None, parent=None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self._config = CONFIG
        self._bridge: AcquisitionBridge | None = None
        self._starting = False
        self._active_session: AcquisitionSession | None = None
        self._stop_event: asyncio.Event | None = None
        self._registry = ProbeRegistry(CONFIG.probes)
        self._probe_service: ProbeService | None = None
        self._recorder: SessionRecorder | None = None

    @property
    def running(self) -> bool:
        return self._starting or bool(self._bridge and self._bridge.running)

    def start(self) -> None:
        if self.running:
            return
        root = (
            self.app_state.session_store.root
            if self.app_state is not None
            else CONFIG.sessions_directory
        )
        self._config = replace(
            CONFIG,
            probes=self._registry.definitions,
            sessions_directory=Path(root),
        )
        manager = SessionManager(self._config)
        self._active_session = self._selected_or_new_session(manager)
        recorder = SessionRecorder(self._active_session)
        self._probe_service = ProbeService(self._registry)
        self._recorder = recorder
        scanner = ChefIqScanner(self._config, self._probe_service)
        self._starting = True

        async def capture() -> Path:
            self._stop_event = asyncio.Event()
            scanner_started = False
            try:
                await scanner.start()
                scanner_started = True
                self.acquisition_started.emit(self._active_session.directory)
                self.status.emit("Scanning for Chef iQ probes…")
                while not self._stop_event.is_set():
                    try:
                        await asyncio.wait_for(
                            self._stop_event.wait(),
                            timeout=self._config.record_interval_seconds,
                        )
                    except TimeoutError:
                        states = self._probe_service.get_states()
                        for state in states:
                            recorder.record(state)
                        self.probe_states.emit(tuple(_reading(state) for state in states))
            finally:
                if scanner_started:
                    await scanner.stop()
                manager.complete_session(self._active_session)
                if scanner_started:
                    self.acquisition_stopped.emit(self._active_session.directory)
            return self._active_session.directory

        async def stop_capture() -> None:
            if self._stop_event is not None:
                self._stop_event.set()

        self._bridge = AcquisitionBridge(
            acquisition_factory=capture,
            stop_callback=stop_capture,
            parent=self,
        )
        self._bridge.error.connect(self._on_error)
        self._bridge.status_changed.connect(self._status_changed)
        self._bridge.acquisition_stopped.connect(self._on_stopped)
        self._bridge.start()

    def stop(self) -> None:
        if self._bridge is not None:
            self._bridge.stop()

    def probe_labels(self) -> tuple[tuple[str, str], ...]:
        states = self._probe_service.get_states() if self._probe_service else ()
        labels = {state.address: state.friendly_name for state in states}
        if not labels:
            labels = {item.match_fragment: item.friendly_name for item in self._registry.definitions}
        return tuple(sorted(labels.items(), key=lambda item: item[1].casefold()))

    def set_probe_label(self, address: str, label: str) -> None:
        self._registry.set_friendly_name(address, label)
        if self._probe_service is not None:
            for state in self._probe_service.get_states():
                if state.address.upper() == address.upper():
                    state.friendly_name = label.strip()
                    if self._recorder is not None:
                        self._recorder.rename_probe(address, label)
            self.probe_states.emit(
                tuple(_reading(state) for state in self._probe_service.get_states())
            )

    def _selected_or_new_session(self, manager: SessionManager) -> AcquisitionSession:
        selected = (
            self.app_state.selected_session
            if self.app_state is not None
            else None
        )
        if selected is not None:
            try:
                session = manager.open_session(selected)
                if session.manifest.ended_at_utc is None:
                    return session
            except Exception:
                pass
        return manager.create_session()

    def _status_changed(self, running: bool, message: str) -> None:
        self.status.emit(message)

    def _on_error(self, message: str) -> None:
        self._starting = False
        self.error.emit(message)

    def _on_stopped(self) -> None:
        self._starting = False


def _reading(state) -> LiveProbeReading:
    return LiveProbeReading(
        address=state.address,
        friendly_name=state.friendly_name,
        food_temperature_c=state.food_temperature_c,
        ambient_temperature_c=state.ambient_temperature_c,
        tip_1_temperature_c=state.tip_1_temperature_c,
        tip_2_temperature_c=state.tip_2_temperature_c,
        tip_3_temperature_c=state.tip_3_temperature_c,
        tip_4_temperature_c=state.tip_4_temperature_c,
        battery_percent=state.battery_percent,
        rssi=state.rssi,
        timestamp_utc=state.last_seen,
    )
