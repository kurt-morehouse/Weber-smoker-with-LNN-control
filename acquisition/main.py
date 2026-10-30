import asyncio
import logging

from acquisition.ble_scanner import ChefIqScanner
from acquisition.config import CONFIG
from acquisition.console_display import display_probe_states
from acquisition.probe_registry import ProbeRegistry
from acquisition.probe_service import ProbeService
from acquisition.recorder import SessionRecorder
from acquisition.session import SessionManager


LOG_FORMAT: str = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)


async def run() -> None:

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
    )

    registry = ProbeRegistry(
        CONFIG.probes
    )

    probe_service = ProbeService(
        registry
    )

    session_manager = SessionManager(
        CONFIG
    )

    session = session_manager.create_session()

    recorder = SessionRecorder(
        session
    )

    scanner = ChefIqScanner(
        config=CONFIG,
        probe_service=probe_service,
    )

    logging.info(
        "Recording session: %s",
        session.directory,
    )

    scanner_started = False

    try:
        await scanner.start()
        scanner_started = True

        while True:
            await asyncio.sleep(CONFIG.record_interval_seconds)
            states = probe_service.get_states()
            display_probe_states(states, CONFIG.stale_timeout_seconds)
            for state in states:
                recorder.record(state)
    finally:
        if scanner_started:
            await scanner.stop()
        session_manager.complete_session(session)


def main() -> None:

    try:
        asyncio.run(run())

    except KeyboardInterrupt:
        print()
        print("Chef iQ monitoring session ended.")


if __name__ == "__main__":
    main()
