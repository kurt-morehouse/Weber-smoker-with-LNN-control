import logging
from collections.abc import Mapping
from typing import Any

from chefiq_ble import ChefIqBluetoothDeviceData

from acquisition.models import ProbeState, utc_now
from acquisition.probe_registry import ProbeRegistry


LOGGER = logging.getLogger(__name__)


class ProbeService:
    def __init__(
        self,
        registry: ProbeRegistry,
    ) -> None:
        self._registry = registry

        self._parsers: dict[
            str,
            ChefIqBluetoothDeviceData,
        ] = {}

        self._states: dict[
            str,
            ProbeState,
        ] = {}

    def get_states(self) -> tuple[ProbeState, ...]:
        return tuple(self._states.values())

    def process_advertisement(
        self,
        *,
        address: str,
        bluetooth_name: str,
        rssi: int,
        raw_packet: bytes,
        service_info: Any,
    ) -> ProbeState | None:

        parser = self._parsers.setdefault(
            address,
            ChefIqBluetoothDeviceData(),
        )

        try:
            if not parser.supported(service_info):
                return None
            update = parser.update(service_info)

        except Exception:
            LOGGER.exception(
                "Chef iQ parser failure for %s",
                address,
            )
            return None

        friendly_name = self._registry.friendly_name_for(address)
        state = self._states.setdefault(
            address,
            ProbeState(
                address=address,
                friendly_name=friendly_name,
                bluetooth_name=bluetooth_name,
            ),
        )
        state.friendly_name = friendly_name
        state.bluetooth_name = bluetooth_name
        state.rssi = rssi
        state.last_packet_hex = raw_packet.hex()
        state.last_seen = utc_now()

        if update is None:
            return state

        entity_values = getattr(
            update,
            "entity_values",
            None,
        )

        if not entity_values:
            return state

        self._apply_values(
            state,
            entity_values,
        )

        return state

    def _apply_values(
        self,
        state: ProbeState,
        entity_values: Mapping[Any, Any],
    ) -> None:

        for key, entity in entity_values.items():

            key_name = str(
                getattr(key, "key", key)
            ).lower()

            value = getattr(
                entity,
                "native_value",
                entity,
            )

            if not isinstance(value, (int, float)):
                continue

            self._assign_value(
                state,
                key_name,
                float(value),
            )

    @staticmethod
    def _assign_value(
        state: ProbeState,
        key_name: str,
        value: float,
    ) -> None:

        normalized = (
            key_name
            .replace("-", "_")
            .replace(" ", "_")
        )

        if (
            "ambient" in normalized
            and "temperature" in normalized
        ):
            state.ambient_temperature_c = value

        elif (
            "food" in normalized
            and "temperature" in normalized
        ):
            state.food_temperature_c = value

        elif (
            "tip_1" in normalized
            and "temperature" in normalized
        ):
            state.tip_1_temperature_c = value

        elif (
            "tip_2" in normalized
            and "temperature" in normalized
        ):
            state.tip_2_temperature_c = value

        elif (
            "tip_3" in normalized
            and "temperature" in normalized
        ):
            state.tip_3_temperature_c = value

        elif (
            "tip_4" in normalized
            and "temperature" in normalized
        ):
            state.tip_4_temperature_c = value

        elif "battery" in normalized:
            state.battery_percent = value
