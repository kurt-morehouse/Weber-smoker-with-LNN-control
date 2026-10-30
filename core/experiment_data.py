from __future__ import annotations

import csv

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class DataSeries:
    name: str
    values: tuple[float | None, ...]


@dataclass(frozen=True)
class ProbeData:
    friendly_name: str
    role: str | None
    source_file: Path

    time_seconds: tuple[float, ...]

    series: tuple[DataSeries, ...]


TIME_COLUMN_CANDIDATES = (
    "elapsed_seconds",
    "time_seconds",
    "elapsed_s",
    "seconds",
)

TIMESTAMP_COLUMN_CANDIDATES = (
    "timestamp_utc",
    "timestamp",
    "datetime_utc",
    "datetime",
)

TEMPERATURE_HINTS = (
    "temperature",
    "temp",
    "food",
    "ambient",
    "tip",
)


def _float_or_none(
    value: str | None,
) -> float | None:

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    try:
        return float(value)

    except ValueError:
        return None


def _datetime_or_none(
    value: str | None,
) -> datetime | None:

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    # Python's ISO parser accepts timezone offsets directly.
    # Normalize the common UTC "Z" suffix for compatibility.
    if value.endswith(("Z", "z")):
        value = value[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(value)

    except ValueError:
        return None


def _find_column(
    fieldnames: list[str],
    candidates: tuple[str, ...],
) -> str | None:

    normalized = {
        name.lower().strip(): name
        for name in fieldnames
    }

    for candidate in candidates:

        if candidate in normalized:
            return normalized[candidate]

    return None


def _find_time_column(
    fieldnames: list[str],
) -> str | None:

    return _find_column(
        fieldnames,
        TIME_COLUMN_CANDIDATES,
    )


def _find_timestamp_column(
    fieldnames: list[str],
) -> str | None:

    return _find_column(
        fieldnames,
        TIMESTAMP_COLUMN_CANDIDATES,
    )


def _temperature_columns(
    fieldnames: list[str],
) -> tuple[str, ...]:

    results: list[str] = []

    for name in fieldnames:

        lowered = name.lower()

        if any(
            hint in lowered
            for hint in TEMPERATURE_HINTS
        ):
            results.append(name)

    return tuple(results)


def _elapsed_from_numeric_column(
    rows: list[dict[str, str]],
    time_column: str,
) -> list[float]:

    times: list[float] = []

    for index, row in enumerate(rows):

        value = _float_or_none(
            row.get(time_column)
        )

        times.append(
            value
            if value is not None
            else float(index)
        )

    return times


def _elapsed_from_timestamp_column(
    rows: list[dict[str, str]],
    timestamp_column: str,
) -> list[float]:

    parsed = [
        _datetime_or_none(
            row.get(timestamp_column)
        )
        for row in rows
    ]

    first_timestamp = next(
        (
            timestamp
            for timestamp in parsed
            if timestamp is not None
        ),
        None,
    )

    if first_timestamp is None:
        raise ValueError(
            f"Timestamp column {timestamp_column!r} "
            "contains no valid timestamps."
        )

    times: list[float] = []
    previous_elapsed = 0.0

    for index, timestamp in enumerate(parsed):

        if timestamp is None:
            # A malformed individual timestamp should not destroy an
            # otherwise usable experiment. Preserve monotonic order using
            # the previous elapsed time; the corresponding measurement
            # remains available for inspection.
            elapsed = previous_elapsed if index > 0 else 0.0

        else:
            try:
                elapsed = (
                    timestamp - first_timestamp
                ).total_seconds()

            except TypeError as exc:
                raise ValueError(
                    "Timestamp timezone information is inconsistent "
                    f"in column {timestamp_column!r}."
                ) from exc

        if elapsed < 0.0:
            raise ValueError(
                f"Timestamps move backward in {timestamp_column!r}."
            )

        if index > 0 and elapsed < previous_elapsed:
            raise ValueError(
                f"Timestamps are not monotonic in {timestamp_column!r}."
            )

        times.append(elapsed)
        previous_elapsed = elapsed

    return times


def load_probe_csv(
    path: Path,
    friendly_name: str,
    role: str | None = None,
) -> ProbeData:

    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                f"No CSV header found in {path}"
            )

        fieldnames = list(
            reader.fieldnames
        )

        rows = list(reader)

    if not rows:
        raise ValueError(
            f"No measurements found in {path}"
        )

    time_column = _find_time_column(
        fieldnames
    )

    timestamp_column = (
        _find_timestamp_column(
            fieldnames
        )
    )

    temperature_columns = (
        _temperature_columns(
            fieldnames
        )
    )

    if not temperature_columns:
        raise ValueError(
            "No temperature columns found in "
            f"{path.name}. Columns were: "
            f"{fieldnames}"
        )

    # Prefer a recorder-provided elapsed-time column when available.
    # Native acquisition CSVs currently provide timestamp_utc instead,
    # so derive true elapsed seconds from those timestamps.
    if time_column is not None:

        times = _elapsed_from_numeric_column(
            rows,
            time_column,
        )

    elif timestamp_column is not None:

        times = _elapsed_from_timestamp_column(
            rows,
            timestamp_column,
        )

    else:

        # Compatibility fallback for legacy/imported CSVs that contain
        # neither elapsed time nor an absolute timestamp.
        times = [
            float(index)
            for index in range(len(rows))
        ]

    data_series: list[DataSeries] = []

    for column in temperature_columns:

        values = tuple(
            _float_or_none(
                row.get(column)
            )
            for row in rows
        )

        data_series.append(
            DataSeries(
                name=column,
                values=values,
            )
        )

    return ProbeData(
        friendly_name=friendly_name,
        role=role,
        source_file=path,
        time_seconds=tuple(times),
        series=tuple(data_series),
    )
