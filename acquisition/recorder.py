from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import re

from core.experiment_manifest import ProbeManifest, save_manifest
from acquisition.models import ProbeState
from acquisition.session import AcquisitionSession


CSV_FIELDS = (
    "timestamp_utc",
    "Date Time",
    "probe_name",
    "probe_address",
    "RSSI",
    "rssi_dbm",
    "Food Temperature",
    "food_temperature_f",
    "food_temperature_c",
    "Ambient Temperature",
    "ambient_temperature_f",
    "ambient_temperature_c",
    "Tip 1 Temperature",
    "tip_1_temperature_f",
    "tip_1_temperature_c",
    "Tip 2 Temperature",
    "tip_2_temperature_f",
    "tip_2_temperature_c",
    "Tip 3 Temperature",
    "tip_3_temperature_f",
    "tip_3_temperature_c",
    "Tip 4 Temperature",
    "tip_4_temperature_f",
    "tip_4_temperature_c",
    "Battery Level",
    "battery_percent",
    "Raw Packet",
    "raw_packet_hex",
)


def celsius_to_fahrenheit(value: float) -> float:
    return value * 9.0 / 5.0 + 32.0


class SessionRecorder:
    def __init__(self, session: AcquisitionSession) -> None:
        self.session = session
        self._paths: dict[str, Path] = {}
        self._manifest_probes = list(session.manifest.probes)
        for probe in self._manifest_probes:
            path = session.directory / probe.data_file
            self._paths[probe.device_id.upper()] = path
            self._ensure_header(path)

    def record(self, state: ProbeState) -> None:
        path = self._path_for(state)
        now = datetime.now(timezone.utc)
        values = {
            "timestamp_utc": now.isoformat(),
            "Date Time": now.astimezone().strftime("%m/%d/%Y %I:%M:%S %p"),
            "probe_name": state.friendly_name,
            "probe_address": state.address,
            "RSSI": state.rssi,
            "rssi_dbm": state.rssi,
            "Food Temperature": _fahrenheit_or_blank(state.food_temperature_c),
            "food_temperature_f": _fahrenheit_or_blank(state.food_temperature_c),
            "food_temperature_c": _blank(state.food_temperature_c),
            "Ambient Temperature": _fahrenheit_or_blank(state.ambient_temperature_c),
            "ambient_temperature_f": _fahrenheit_or_blank(state.ambient_temperature_c),
            "ambient_temperature_c": _blank(state.ambient_temperature_c),
            "Tip 1 Temperature": _fahrenheit_or_blank(state.tip_1_temperature_c),
            "tip_1_temperature_f": _fahrenheit_or_blank(state.tip_1_temperature_c),
            "tip_1_temperature_c": _blank(state.tip_1_temperature_c),
            "Tip 2 Temperature": _fahrenheit_or_blank(state.tip_2_temperature_c),
            "tip_2_temperature_f": _fahrenheit_or_blank(state.tip_2_temperature_c),
            "tip_2_temperature_c": _blank(state.tip_2_temperature_c),
            "Tip 3 Temperature": _fahrenheit_or_blank(state.tip_3_temperature_c),
            "tip_3_temperature_f": _fahrenheit_or_blank(state.tip_3_temperature_c),
            "tip_3_temperature_c": _blank(state.tip_3_temperature_c),
            "Tip 4 Temperature": _fahrenheit_or_blank(state.tip_4_temperature_c),
            "tip_4_temperature_f": _fahrenheit_or_blank(state.tip_4_temperature_c),
            "tip_4_temperature_c": _blank(state.tip_4_temperature_c),
            "Battery Level": state.battery_percent,
            "battery_percent": state.battery_percent,
            "Raw Packet": state.last_packet_hex,
            "raw_packet_hex": state.last_packet_hex,
        }
        with path.open("a", encoding="utf-8", newline="") as file:
            csv.DictWriter(file, fieldnames=CSV_FIELDS).writerow(values)

    def rename_probe(self, address: str, friendly_name: str) -> None:
        updated = []
        changed = False
        for probe in self._manifest_probes:
            if probe.device_id.upper() == address.upper():
                updated.append(replace(probe, friendly_name=friendly_name.strip()))
                changed = True
            else:
                updated.append(probe)
        if not changed:
            return
        self._manifest_probes = updated
        self.session = replace(
            self.session,
            manifest=replace(self.session.manifest, probes=tuple(updated)),
        )
        save_manifest(self.session.directory, self.session.manifest)

    def _path_for(self, state: ProbeState) -> Path:
        address = state.address.upper()
        if address in self._paths:
            return self._paths[address]

        for probe in self._manifest_probes:
            if probe.device_id.upper() in address or address in probe.device_id.upper():
                path = self.session.directory / probe.data_file
                self._paths[address] = path
                return path

        filename = _filename_for(state.friendly_name)
        path = self.session.directory / filename
        probe = ProbeManifest(
            device_id=state.address,
            friendly_name=state.friendly_name,
            data_file=filename,
            role=None,
        )
        self._manifest_probes.append(probe)
        self.session = replace(
            self.session,
            manifest=replace(
                self.session.manifest,
                probes=tuple(self._manifest_probes),
            ),
        )
        save_manifest(self.session.directory, self.session.manifest)
        self._paths[address] = path
        self._ensure_header(path)
        return path

    @staticmethod
    def _ensure_header(path: Path) -> None:
        if not path.exists() or path.stat().st_size == 0:
            with path.open("w", encoding="utf-8", newline="") as file:
                csv.writer(file).writerow(CSV_FIELDS)


def _blank(value: float | None) -> str | float:
    return "" if value is None else value


def _fahrenheit_or_blank(value: float | None) -> str | float:
    return "" if value is None else celsius_to_fahrenheit(value)


def _filename_for(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "unknown_probe"
    return f"{slug}.csv"
