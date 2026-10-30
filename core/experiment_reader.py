from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.experiment import Experiment, load_experiment


@dataclass(frozen=True)
class RecordedSeries:
    name: str
    values: tuple[float | None, ...]


@dataclass(frozen=True)
class RecordedProbe:
    friendly_name: str
    role: str | None
    source_file: Path
    time_seconds: tuple[float, ...]
    series: tuple[RecordedSeries, ...]


@dataclass(frozen=True)
class RecordedExperiment:
    experiment: Experiment
    probes: tuple[RecordedProbe, ...]


def load_recorded_experiment(directory: Path) -> RecordedExperiment:
    experiment = load_experiment(directory)
    session_start = _elapsed(experiment.manifest.started_at_utc)
    probes = tuple(
        _load_probe(
            experiment, probe.friendly_name, probe.role, probe.data_file, session_start
        )
        for probe in experiment.manifest.probes
    )
    return RecordedExperiment(experiment, probes)


def _load_probe(
    experiment: Experiment,
    friendly_name: str,
    role: str | None,
    filename: str,
    session_start: float | None,
) -> RecordedProbe:
    path = experiment.directory / filename
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        rows = list(reader)
        headers = list(reader.fieldnames)

    timestamp_column = _column(headers, ("timestamp_utc", "timestamp", "Date Time", "datetime"))
    time_column = _column(headers, ("elapsed_seconds", "time_seconds", "elapsed_s"))
    timestamps = [_elapsed(row.get(timestamp_column) if timestamp_column else None) for row in rows]
    numeric_times = [_number(row.get(time_column)) for row in rows] if time_column else []
    if numeric_times and all(value is not None for value in numeric_times):
        first = numeric_times[0]
        times = tuple(value - first for value in numeric_times)
    elif timestamps and all(value is not None for value in timestamps):
        first = session_start if session_start is not None else timestamps[0]
        times = tuple(value - first for value in timestamps)
    else:
        times = tuple(float(index) for index in range(len(rows)))

    ignored = {
        "timestamp_utc", "timestamp", "date time", "datetime", "datetime_utc",
        "elapsed_seconds", "time_seconds", "elapsed_s", "seconds",
    }
    series = []
    for header in headers:
        normalized = header.strip().lower()
        if normalized in ignored or not any(token in normalized for token in ("temp", "food", "ambient", "tip", "battery", "rssi")):
            continue
        values = tuple(_number(row.get(header)) for row in rows)
        if any(value is not None for value in values):
            series.append(RecordedSeries(header, values))

    return RecordedProbe(
        friendly_name=friendly_name,
        role=role,
        source_file=path,
        time_seconds=times,
        series=tuple(series),
    )


def _column(headers: list[str], candidates: tuple[str, ...]) -> str | None:
    normalized = {header.strip().lower(): header for header in headers}
    for candidate in candidates:
        if candidate.strip().lower() in normalized:
            return normalized[candidate.strip().lower()]
    return None


def _number(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _elapsed(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if value.endswith(("Z", "z")):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        for format_string in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S"):
            try:
                parsed = datetime.strptime(value, format_string)
                break
            except ValueError:
                continue
        else:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.timestamp()
