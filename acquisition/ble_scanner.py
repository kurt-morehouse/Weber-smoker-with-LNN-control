from __future__ import annotations

import logging
import time
from typing import Any

from bleak import BleakScanner
from home_assistant_bluetooth import BluetoothServiceInfoBleak, SOURCE_LOCAL

from acquisition.probe_service import ProbeService


LOGGER = logging.getLogger(__name__)
CHEFIQ_MANUFACTURER_ID = 0x05CD


class ChefIqScanner:
    def __init__(self, config: Any, probe_service: ProbeService) -> None:
        self.config = config
        self.probe_service = probe_service
        self._scanner: BleakScanner | None = None

    async def start(self) -> None:
        LOGGER.info("Starting Chef iQ BLE scan")
        if self._scanner is None:
            self._scanner = BleakScanner(
                detection_callback=self._on_advertisement
            )
        await self._scanner.start()

    async def stop(self) -> None:
        if self._scanner is not None:
            await self._scanner.stop()
            self._scanner = None
            LOGGER.info("Stopped Chef iQ BLE scan")

    def _on_advertisement(self, device: Any, advertisement: Any) -> None:
        manufacturer_data = advertisement.manufacturer_data or {}
        raw_packet = manufacturer_data.get(CHEFIQ_MANUFACTURER_ID)
        if raw_packet is None:
            return

        address = str(device.address)
        name = str(advertisement.local_name or device.name or "CQ60")
        service_info = BluetoothServiceInfoBleak(
            name=name,
            address=address,
            rssi=int(advertisement.rssi),
            manufacturer_data=manufacturer_data,
            service_data=advertisement.service_data or {},
            service_uuids=list(advertisement.service_uuids or []),
            source=SOURCE_LOCAL,
            device=device,
            advertisement=advertisement,
            connectable=bool(getattr(advertisement, "connectable", False)),
            time=time.monotonic(),
            tx_power=getattr(advertisement, "tx_power", None),
        )
        try:
            self.probe_service.process_advertisement(
                address=address,
                bluetooth_name=name,
                rssi=int(advertisement.rssi),
                raw_packet=raw_packet,
                service_info=service_info,
            )
        except Exception:
            LOGGER.exception("Failed to process Chef iQ advertisement from %s", address)
