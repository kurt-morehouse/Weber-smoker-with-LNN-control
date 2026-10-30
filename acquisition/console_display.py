from datetime import datetime, timezone

from acquisition.models import ProbeState
from acquisition.recorder import celsius_to_fahrenheit


TABLE_WIDTH: int = 120
MISSING_VALUE_TEXT: str = "---"


def format_temperature(
    temperature_c: float | None,
) -> str:

    temperature_f = celsius_to_fahrenheit(
        temperature_c
    )

    if temperature_f is None:
        return MISSING_VALUE_TEXT

    return f"{temperature_f:6.1f}°F"


def display_probe_states(
    states: tuple[ProbeState, ...],
    stale_timeout_seconds: float,
) -> None:

    print()
    print("=" * TABLE_WIDTH)
    print("CHEF iQ CQ60 LIVE TEMPERATURES")
    print("=" * TABLE_WIDTH)

    if not states:
        print("Waiting for Chef iQ probes...")
        return

    now = datetime.now(timezone.utc)

    for state in sorted(
        states,
        key=lambda item: item.friendly_name,
    ):

        age_seconds = (
            now - state.last_seen
        ).total_seconds()

        status = (
            "LIVE"
            if age_seconds <= stale_timeout_seconds
            else "STALE"
        )

        print(
            f"{state.friendly_name:<22}"
            f"{status:<7}"
            f"RSSI {state.rssi!s:>4} | "
            f"Food {format_temperature(state.food_temperature_c)} | "
            f"Amb {format_temperature(state.ambient_temperature_c)} | "
            f"T1 {format_temperature(state.tip_1_temperature_c)} | "
            f"T2 {format_temperature(state.tip_2_temperature_c)} | "
            f"T3 {format_temperature(state.tip_3_temperature_c)} | "
            f"T4 {format_temperature(state.tip_4_temperature_c)}"
        )
