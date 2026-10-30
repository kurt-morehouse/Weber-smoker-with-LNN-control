from __future__ import annotations

from collections.abc import Mapping


# CHEF iQ protocol details belong here, not in application configuration.
# Callers should use extract_chefiq_packet() rather than depending on the
# manufacturer identifier itself.
_CHEFIQ_MANUFACTURER_ID = 0x05CD
_CHEFIQ_MAX_PROBE_PACKET_LENGTH_BYTES = 18


def extract_chefiq_packet(
    manufacturer_data: Mapping[int, bytes],
) -> bytes | None:
    """
    Return a valid CHEF iQ manufacturer payload, or None.

    This is the single boundary that knows the CHEF iQ Bluetooth
    manufacturer identifier and packet-size rule.
    """
    packet = manufacturer_data.get(
        _CHEFIQ_MANUFACTURER_ID
    )

    if packet is None:
        return None

    if len(packet) > _CHEFIQ_MAX_PROBE_PACKET_LENGTH_BYTES:
        return None

    return bytes(packet)
