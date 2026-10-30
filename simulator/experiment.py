import csv
import json
from datetime import datetime
from pathlib import Path

from simulator.config import FAHRENHEIT_OFFSET, FAHRENHEIT_TO_CELSIUS_SCALE
from simulator.models import ExperimentData, ExperimentMetadata, MeasurementSeries

DATE_TIME_COLUMN_CANDIDATES = ("Date Time", "datetime", "timestamp", "timestamp_utc")
TEMPERATURE_COLUMN_CANDIDATES = ("Food Temperature", "food_temperature_f", "temperature_f")


def fahrenheit_to_celsius(temperature_f: float) -> float:
    return (temperature_f - FAHRENHEIT_OFFSET) * FAHRENHEIT_TO_CELSIUS_SCALE


def load_experiment(experiment_directory: Path) -> ExperimentData:
    """Prefer canonical manifest.json; retain read-only legacy experiment.json support."""
    experiment_directory = Path(experiment_directory)
    manifest_path = experiment_directory / "manifest.json"
    legacy_path = experiment_directory / "experiment.json"

    if manifest_path.exists():
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        metadata = _metadata_from_manifest(experiment_directory, raw)
    elif legacy_path.exists():
        raw = json.loads(legacy_path.read_text(encoding="utf-8"))
        metadata = _metadata_from_legacy(experiment_directory, raw)
    else:
        raise FileNotFoundError(
            f"Missing experiment metadata: expected {manifest_path} "
            f"(legacy fallback: {legacy_path})"
        )

    internal = load_temperature_file(metadata.internal_file, metadata.internal_temperature_column)
    external = load_temperature_file(metadata.external_file, metadata.external_temperature_column)
    return ExperimentData(metadata=metadata, internal=internal, external=external)


def _metadata_from_manifest(experiment_directory: Path, raw: dict) -> ExperimentMetadata:
    probes = list(raw.get("probes", []))
    if len(probes) < 2:
        raise ValueError("manifest.json needs at least two probe entries for the legacy two-node simulator.")

    internal = _choose_probe(probes, "internal") or probes[0]
    remaining = [p for p in probes if p is not internal]
    external = _choose_probe(remaining, "external") or remaining[0]

    heater = raw.get("heater", {}) or {}
    heater_power = heater.get("commanded_power_w")
    if heater_power is None:
        heater_power = heater.get("rated_power_w")
    if heater_power is None:
        raise ValueError(
            "manifest.json is missing heater.commanded_power_w and heater.rated_power_w; "
            "calibration requires known heater power."
        )

    environment = raw.get("environment", {}) or {}
    ambient = environment.get("ambient_temperature_f")

    return ExperimentMetadata(
        name=str(raw.get("name") or raw.get("experiment_id") or experiment_directory.name),
        heater_power_w=float(heater_power),
        internal_file=experiment_directory / str(internal["data_file"]),
        external_file=experiment_directory / str(external["data_file"]),
        ambient_temperature_f=float(ambient) if ambient is not None else None,
        internal_temperature_column=str(internal.get("temperature_column", "food_temperature_f")),
        external_temperature_column=str(external.get("temperature_column", "food_temperature_f")),
        notes=str(raw.get("notes") or ""),
    )


def _choose_probe(probes: list[dict], desired_role: str) -> dict | None:
    desired_role = desired_role.lower()
    for probe in probes:
        searchable = " ".join(str(probe.get(k) or "") for k in ("role", "friendly_name", "notes")).lower()
        if desired_role in searchable:
            return probe
    return None


def _metadata_from_legacy(experiment_directory: Path, raw: dict) -> ExperimentMetadata:
    return ExperimentMetadata(
        name=str(raw["name"]),
        heater_power_w=float(raw["heater_power_w"]),
        internal_file=experiment_directory / str(raw["internal_file"]),
        external_file=experiment_directory / str(raw["external_file"]),
        ambient_temperature_f=float(raw["ambient_temperature_f"]) if raw.get("ambient_temperature_f") is not None else None,
        internal_temperature_column=str(raw.get("internal_temperature_column", "Food Temperature")),
        external_temperature_column=str(raw.get("external_temperature_column", "Food Temperature")),
        notes=str(raw.get("notes", "")),
    )


def load_temperature_file(path: Path, requested_temperature_column: str) -> MeasurementSeries:
    if not path.exists():
        raise FileNotFoundError(f"Missing temperature file: {path}")
    rows = _read_csv_from_detected_header(path)
    if not rows:
        raise ValueError(f"No data rows found in {path}")
    fieldnames = {field for field in rows[0].keys() if field is not None}
    timestamp_column = _find_column(fieldnames, DATE_TIME_COLUMN_CANDIDATES)
    temperature_column = _find_column(fieldnames, (requested_temperature_column, *TEMPERATURE_COLUMN_CANDIDATES))
    timestamps, temperatures_c = [], []
    for row in rows:
        raw_timestamp, raw_temperature = row.get(timestamp_column), row.get(temperature_column)
        if not raw_timestamp or not raw_temperature:
            continue
        try:
            timestamp = _parse_datetime(raw_timestamp)
            temperature_f = float(raw_temperature)
        except (ValueError, TypeError):
            continue
        timestamps.append(timestamp)
        temperatures_c.append(fahrenheit_to_celsius(temperature_f))
    if len(timestamps) < 2:
        raise ValueError(f"Not enough usable data in {path}")
    start_time = timestamps[0]
    elapsed_seconds = tuple((timestamp - start_time).total_seconds() for timestamp in timestamps)
    return MeasurementSeries(time_seconds=elapsed_seconds, temperature_c=tuple(temperatures_c))


def _read_csv_from_detected_header(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    header_index = None
    for index, line in enumerate(lines):
        normalized = line.lower()
        if "date time" in normalized or "timestamp_utc" in normalized:
            header_index = index
            break
    if header_index is None:
        raise ValueError(f"Could not locate CSV header in {path}")
    return list(csv.DictReader(lines[header_index:]))


def _find_column(fieldnames: set[str], candidates: tuple[str, ...]) -> str:
    normalized_fields = {field.strip().lower(): field for field in fieldnames}
    for candidate in candidates:
        normalized_candidate = candidate.strip().lower()
        if normalized_candidate in normalized_fields:
            return normalized_fields[normalized_candidate]
    raise ValueError(f"Expected column not found. Available columns: {sorted(fieldnames)}")


def _parse_datetime(value: str) -> datetime:
    formats = ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z")
    clean_value = value.strip()
    for format_string in formats:
        try:
            return datetime.strptime(clean_value, format_string)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date/time: {value}")
