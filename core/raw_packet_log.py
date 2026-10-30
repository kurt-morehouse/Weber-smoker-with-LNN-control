from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


RAW_PACKET_FILENAME = "raw_ble_packets.csv"


class RawPacketLogger:
    """
    Optional diagnostic logger for BLE advertisement payloads.

    This module intentionally does not alter the scanner.  Wire log_packet()
    into the scanner callback only when we have the current scanner source in
    hand, so acquisition stability is not risked by a guessed patch.
    """

    def __init__(self, session_directory: Path) -> None:
        self.path = Path(session_directory) / RAW_PACKET_FILENAME
        self._header_written = self.path.exists() and self.path.stat().st_size > 0

    def log_packet(
        self,
        *,
        device_identifier: str,
        manufacturer_id: int,
        payload: bytes,
        rssi_dbm: int | None = None,
    ) -> None:
        write_header = not self._header_written

        with self.path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)

            if write_header:
                writer.writerow(
                    [
                        "timestamp_utc",
                        "device_identifier",
                        "manufacturer_id_hex",
                        "rssi_dbm",
                        "payload_hex",
                        "payload_length",
                    ]
                )
                self._header_written = True

            writer.writerow(
                [
                    datetime.now(timezone.utc).isoformat(),
                    device_identifier,
                    f"0x{manufacturer_id:04X}",
                    "" if rssi_dbm is None else rssi_dbm,
                    payload.hex(" "),
                    len(payload),
                ]
            )
