from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ChannelIntegrity:
    name: str
    samples: int
    valid_samples: int
    first_value: float | None
    last_value: float | None
    minimum: float | None
    maximum: float | None
    longest_unchanged_run: int
    longest_unchanged_seconds: float
    unchanged_run_start_seconds: float | None
    unchanged_run_end_seconds: float | None


@dataclass(frozen=True)
class CsvIntegrityReport:
    path: Path
    samples: int
    duration_seconds: float
    median_interval_seconds: float | None
    timestamp_column: str | None
    channels: tuple[ChannelIntegrity, ...]


TIMESTAMP_CANDIDATES = ("timestamp_utc", "timestamp", "datetime_utc", "datetime")
TIME_CANDIDATES = ("elapsed_seconds", "time_seconds", "elapsed_s", "seconds")


def _float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _datetime(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _find(fieldnames, candidates):
    normalized = {name.strip().lower(): name for name in fieldnames}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def _times(rows, fieldnames):
    elapsed = _find(fieldnames, TIME_CANDIDATES)
    if elapsed:
        values = [_float(row.get(elapsed)) for row in rows]
        if all(value is not None for value in values):
            first = values[0]
            return [value - first for value in values], None

    timestamp = _find(fieldnames, TIMESTAMP_CANDIDATES)
    if timestamp:
        parsed = [_datetime(row.get(timestamp)) for row in rows]
        first = next((value for value in parsed if value is not None), None)
        if first is not None:
            result = []
            previous = 0.0
            for value in parsed:
                if value is None:
                    result.append(previous)
                else:
                    previous = (value - first).total_seconds()
                    result.append(previous)
            return result, timestamp

    return [float(i) for i in range(len(rows))], None


def analyze_csv(path: Path) -> CsvIntegrityReport:
    path = Path(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"No header in {path}")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    if not rows:
        raise ValueError(f"No data rows in {path}")

    times, timestamp_column = _times(rows, fieldnames)
    intervals = [
        b - a for a, b in zip(times, times[1:])
        if b > a
    ]
    median_interval = None
    if intervals:
        ordered = sorted(intervals)
        median_interval = ordered[len(ordered) // 2]

    ignored = {
        *(name.lower() for name in TIMESTAMP_CANDIDATES),
        *(name.lower() for name in TIME_CANDIDATES),
        "probe_name", "probe_address", "rssi_dbm", "battery_percent",
    }

    channels = []
    for name in fieldnames:
        if name.lower().strip() in ignored:
            continue

        values = [_float(row.get(name)) for row in rows]
        numeric = [value for value in values if value is not None]
        if not numeric:
            continue

        best_count = 1
        best_start = 0
        best_end = 0
        run_count = 1
        run_start = 0

        for index in range(1, len(values)):
            if (
                values[index] is not None
                and values[index - 1] is not None
                and values[index] == values[index - 1]
            ):
                run_count += 1
            else:
                if run_count > best_count:
                    best_count = run_count
                    best_start = run_start
                    best_end = index - 1
                run_count = 1
                run_start = index

        if run_count > best_count:
            best_count = run_count
            best_start = run_start
            best_end = len(values) - 1

        channels.append(
            ChannelIntegrity(
                name=name,
                samples=len(values),
                valid_samples=len(numeric),
                first_value=next((v for v in values if v is not None), None),
                last_value=next((v for v in reversed(values) if v is not None), None),
                minimum=min(numeric),
                maximum=max(numeric),
                longest_unchanged_run=best_count,
                longest_unchanged_seconds=max(
                    0.0, times[best_end] - times[best_start]
                ),
                unchanged_run_start_seconds=times[best_start],
                unchanged_run_end_seconds=times[best_end],
            )
        )

    return CsvIntegrityReport(
        path=path,
        samples=len(rows),
        duration_seconds=times[-1] - times[0] if len(times) > 1 else 0.0,
        median_interval_seconds=median_interval,
        timestamp_column=timestamp_column,
        channels=tuple(channels),
    )
