from __future__ import annotations

import csv

from dataclasses import dataclass
from pathlib import Path

from core.experiment_manifest import (
    CalibrationInputMapping,
    ExperimentManifest,
    ManifestError,
    ProbeManifest,
    load_manifest,
)


@dataclass(frozen=True)
class CalibrationPreflightReport:
    ready: bool
    errors: tuple[str, ...]
    heater_power_w: float | None
    heater_power_source: str | None

    chamber_probe: str | None = None
    chamber_file: str | None = None
    chamber_channel: str | None = None

    body_probe: str | None = None
    body_file: str | None = None
    body_channel: str | None = None

    validation_probe: str | None = None
    validation_file: str | None = None
    validation_channel: str | None = None

    @property
    def input_summary_lines(self) -> tuple[str, ...]:
        lines: list[str] = []

        if self.chamber_probe is not None:
            lines.append(
                "Chamber: "
                f"{self.chamber_probe} / "
                f"{self.chamber_channel} / "
                f"{self.chamber_file}"
            )

        if self.body_probe is not None:
            lines.append(
                "Body: "
                f"{self.body_probe} / "
                f"{self.body_channel} / "
                f"{self.body_file}"
            )

        if self.validation_probe is not None:
            lines.append(
                "Validation: "
                f"{self.validation_probe} / "
                f"{self.validation_channel} / "
                f"{self.validation_file}"
            )

        return tuple(lines)


def _resolve_heater_power(
    manifest: ExperimentManifest,
) -> tuple[float | None, str | None]:
    heater = manifest.heater

    if heater.commanded_power_w is not None:
        return (
            float(heater.commanded_power_w),
            "heater.commanded_power_w",
        )

    if (
        heater.rated_power_w is not None
        and heater.commanded_power_percent is not None
    ):
        return (
            float(heater.rated_power_w)
            * float(heater.commanded_power_percent)
            / 100.0,
            "heater.rated_power_w × heater.commanded_power_percent",
        )

    if heater.rated_power_w is not None:
        return (
            float(heater.rated_power_w),
            "heater.rated_power_w",
        )

    return None, None


def _probe_for_mapping(
    manifest: ExperimentManifest,
    mapping: CalibrationInputMapping,
) -> ProbeManifest | None:
    for probe in manifest.probes:
        if (
            probe.friendly_name == mapping.probe
            or probe.device_id == mapping.probe
        ):
            return probe
    return None


def _csv_fieldnames(path: Path) -> tuple[str, ...]:
    lines = path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines()

    header_index: int | None = None

    for index, line in enumerate(lines):
        lowered = line.lower()
        if (
            "timestamp_utc" in lowered
            or "date time" in lowered
            or "elapsed_seconds" in lowered
        ):
            header_index = index
            break

    if header_index is None:
        raise ValueError(
            f"Could not locate CSV header in {path.name}."
        )

    reader = csv.DictReader(lines[header_index:])
    if reader.fieldnames is None:
        raise ValueError(
            f"No CSV header found in {path.name}."
        )

    return tuple(
        field.strip()
        for field in reader.fieldnames
        if field is not None
    )


def _validate_mapping(
    *,
    role_name: str,
    mapping: CalibrationInputMapping | None,
    manifest: ExperimentManifest,
    session_path: Path,
    required: bool,
    errors: list[str],
) -> tuple[str | None, str | None, str | None]:
    if mapping is None:
        if required:
            errors.append(
                f"Missing calibration_inputs.{role_name}. "
                "Calibration will not guess a probe or channel."
            )
        return None, None, None

    probe = _probe_for_mapping(
        manifest,
        mapping,
    )

    if probe is None:
        errors.append(
            f"calibration_inputs.{role_name}.probe "
            f"{mapping.probe!r} does not match any configured probe."
        )
        return mapping.probe, None, mapping.channel

    data_path = session_path / probe.data_file
    if not data_path.is_file():
        errors.append(
            f"{role_name.capitalize()} data file is missing: {data_path}"
        )
        return probe.friendly_name, probe.data_file, mapping.channel

    try:
        fields = _csv_fieldnames(data_path)
    except Exception as exc:
        errors.append(
            f"Cannot inspect {role_name} CSV {probe.data_file}: "
            f"{type(exc).__name__}: {exc}"
        )
        return probe.friendly_name, probe.data_file, mapping.channel

    normalized = {
        field.lower(): field
        for field in fields
    }

    requested = mapping.channel.strip().lower()

    if requested not in normalized:
        errors.append(
            f"{role_name.capitalize()} channel "
            f"{mapping.channel!r} is not in {probe.data_file}. "
            f"Available columns: {', '.join(fields)}"
        )

    return (
        probe.friendly_name,
        probe.data_file,
        mapping.channel,
    )


def calibration_preflight(
    session_path: Path,
) -> CalibrationPreflightReport:
    session_path = Path(session_path)
    errors: list[str] = []

    try:
        manifest = load_manifest(
            session_path,
            validate_files=True,
        )
    except Exception as exc:
        return CalibrationPreflightReport(
            ready=False,
            errors=(
                f"Experiment manifest is invalid: "
                f"{type(exc).__name__}: {exc}",
            ),
            heater_power_w=None,
            heater_power_source=None,
        )

    heater_power_w, heater_power_source = _resolve_heater_power(
        manifest
    )

    if heater_power_w is None:
        errors.append(
            "Heater power is unresolved. Set commanded_power_w, or "
            "rated_power_w with commanded_power_percent."
        )
    elif heater_power_w <= 0.0:
        errors.append(
            f"Resolved heater power must be positive; got "
            f"{heater_power_w:.3f} W."
        )

    inputs = manifest.calibration_inputs

    if inputs is None:
        errors.append(
            "Missing calibration_inputs section. Calibration requires "
            "explicit chamber/body probe and channel assignments."
        )
        chamber = body = validation = (None, None, None)
    else:
        chamber = _validate_mapping(
            role_name="chamber",
            mapping=inputs.chamber,
            manifest=manifest,
            session_path=session_path,
            required=True,
            errors=errors,
        )
        body = _validate_mapping(
            role_name="body",
            mapping=inputs.body,
            manifest=manifest,
            session_path=session_path,
            required=True,
            errors=errors,
        )
        validation = _validate_mapping(
            role_name="validation",
            mapping=inputs.validation,
            manifest=manifest,
            session_path=session_path,
            required=False,
            errors=errors,
        )

    return CalibrationPreflightReport(
        ready=not errors,
        errors=tuple(errors),
        heater_power_w=heater_power_w,
        heater_power_source=heater_power_source,
        chamber_probe=chamber[0],
        chamber_file=chamber[1],
        chamber_channel=chamber[2],
        body_probe=body[0],
        body_file=body[1],
        body_channel=body[2],
        validation_probe=validation[0],
        validation_file=validation[1],
        validation_channel=validation[2],
    )
