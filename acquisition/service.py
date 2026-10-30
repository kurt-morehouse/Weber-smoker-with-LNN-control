from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Coroutine, Any


@dataclass(frozen=True)
class AcquisitionStatus:
    running: bool
    session_directory: Path | None
    message: str


StatusCallback = Callable[
    [AcquisitionStatus],
    None,
]

ErrorCallback = Callable[
    [Exception],
    None,
]


class AcquisitionService:
    """
    Owns acquisition execution independently
    of the Qt GUI thread.

    The service owns:
        - one background Python thread
        - one asyncio event loop
        - one acquisition coroutine

    The GUI never runs BLE/asyncio work directly.
    """

    def __init__(
        self,
        acquisition_factory: Callable[
            [],
            Coroutine[Any, Any, Path | None],
        ],
        stop_callback: Callable[
            [],
            Coroutine[Any, Any, None],
        ] | None = None,
        status_callback: StatusCallback | None = None,
        error_callback: ErrorCallback | None = None,
    ) -> None:

        self._acquisition_factory = (
            acquisition_factory
        )

        self._stop_callback = stop_callback

        self._status_callback = (
            status_callback
        )

        self._error_callback = (
            error_callback
        )

        self._thread: threading.Thread | None = (
            None
        )

        self._loop: asyncio.AbstractEventLoop | None = (
            None
        )

        self._task: asyncio.Task | None = None

        self._lock = threading.Lock()

        self._running = False

        self._session_directory: (
            Path | None
        ) = None

    @property
    def running(self) -> bool:

        with self._lock:
            return self._running

    @property
    def session_directory(
        self,
    ) -> Path | None:

        with self._lock:
            return self._session_directory

    def start(self) -> None:

        with self._lock:

            if self._running:
                return

            self._running = True

        self._thread = threading.Thread(
            target=self._thread_main,
            name="weber-acquisition",
            daemon=True,
        )

        self._thread.start()

        self._publish_status(
            "Acquisition starting..."
        )

    def stop(self) -> None:

        loop = self._loop

        if loop is None:
            return

        if not loop.is_running():
            return

        asyncio.run_coroutine_threadsafe(
            self._request_stop(),
            loop,
        )

    def _thread_main(self) -> None:

        loop = asyncio.new_event_loop()

        self._loop = loop

        asyncio.set_event_loop(
            loop
        )

        try:

            loop.run_until_complete(
                self._run()
            )

        except Exception as exc:

            self._publish_error(
                exc
            )

        finally:

            pending = asyncio.all_tasks(
                loop
            )

            for task in pending:
                task.cancel()

            if pending:

                loop.run_until_complete(
                    asyncio.gather(
                        *pending,
                        return_exceptions=True,
                    )
                )

            loop.close()

            self._loop = None
            self._task = None

            with self._lock:
                self._running = False

            self._publish_status(
                "Acquisition stopped."
            )

    async def _run(self) -> None:

        self._task = asyncio.create_task(
            self._acquisition_factory()
        )

        result = await self._task

        if result is not None:

            with self._lock:
                self._session_directory = (
                    Path(result)
                )

    async def _request_stop(self) -> None:

        self._publish_status(
            "Stopping acquisition..."
        )

        if self._stop_callback is not None:

            await self._stop_callback()

        elif self._task is not None:

            self._task.cancel()

    def _publish_status(
        self,
        message: str,
    ) -> None:

        callback = self._status_callback

        if callback is None:
            return

        callback(
            AcquisitionStatus(
                running=self.running,
                session_directory=(
                    self.session_directory
                ),
                message=message,
            )
        )

    def _publish_error(
        self,
        exc: Exception,
    ) -> None:

        callback = self._error_callback

        if callback is not None:
            callback(exc)
