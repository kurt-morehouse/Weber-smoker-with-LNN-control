from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProbeState:
    address: str
    friendly_name: str

    bluetooth_name: str = "CQ60"
    rssi: int | None = None

    food_temperature_c: float | None = None
    ambient_temperature_c: float | None = None

    tip_1_temperature_c: float | None = None
    tip_2_temperature_c: float | None = None
    tip_3_temperature_c: float | None = None
    tip_4_temperature_c: float | None = None

    battery_percent: float | None = None

    last_packet_hex: str = ""
    last_seen: datetime = field(default_factory=utc_now)

    @property
    def short_id(self) -> str:
        return self.address[-8:]
    