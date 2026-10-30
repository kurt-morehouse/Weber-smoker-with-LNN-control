from __future__ import annotations

import json

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CURRENT_SCHEMA_VERSION = 1
MANIFEST_FILENAME = "manifest.json"


class ManifestError(Exception):
    """Base exception for experiment manifest errors."""


class ManifestValidationError(ManifestError):
    """Raised when manifest contents are invalid."""


@dataclass(frozen=True)
class ProbeManifest:
    """
    Describes one physical probe and its role in this experiment.

    Acquisition metadata remains physical: device identity, friendly name,
    role, notes and recorded data file. Model-specific channel selection is
    deliberately kept in CalibrationInputs instead of overloading probe role.
    """

    device_id: str
    friendly_name: str
    data_file: str
    role: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class HeaterManifest:
    rated_power_w: float | None = None
    commanded_power_percent: float | None = None
    commanded_power_w: float | None = None
    control_mode: str = "manual"
    notes: str | None = None


@dataclass(frozen=True)
class EnvironmentManifest:
    ambient_temperature_f: float | None = None
    wind_speed_mph: float | None = None
    weather_notes: str | None = None


@dataclass(frozen=True)
class WeberManifest:
    configuration: str | None = None
    insulation: str | None = None
    top_vent_percent: float | None = None
    bottom_vent_percent: float | None = None
    notes: str | None = None


@dataclass(frozen=True)
class CalibrationInputMapping:
    """
    One explicit model input.

    probe may be either a manifest friendly_name or a device_id.
    channel is the exact CSV column name to use.
    """

    probe: str
    channel: str


@dataclass(frozen=True)
class CalibrationInputs:
    """
    Explicit mapping between recorded probe channels and the two-node model.

    chamber and body are required by simulator calibration when the section is
    present. validation is optional and is reserved for independent model
    checking; it is not included in the calibration objective.
    """

    chamber: CalibrationInputMapping | None = None
    body: CalibrationInputMapping | None = None
    validation: CalibrationInputMapping | None = None


@dataclass(frozen=True)
class ExperimentManifest:
    """
    Canonical experiment metadata.

    calibration_inputs is optional so acquisition-only sessions remain valid.
    The calibration preflight, not acquisition manifest validation, enforces
    model-specific readiness.
    """

    schema_version: int
    experiment_id: str
    name: str
    started_at_utc: str
    probes: tuple[ProbeManifest, ...]

    heater: HeaterManifest = field(default_factory=HeaterManifest)
    environment: EnvironmentManifest = field(default_factory=EnvironmentManifest)
    weber: WeberManifest = field(default_factory=WeberManifest)
    calibration_inputs: CalibrationInputs | None = None

    ended_at_utc: str | None = None
    notes: str | None = None
    tags: tuple[str, ...] = ()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def complete_manifest(session_directory: Path) -> ExperimentManifest:
    manifest = load_manifest(
        session_directory,
        validate_files=False,
    )
    completed = replace(
        manifest,
        ended_at_utc=utc_now_iso(),
    )
    save_manifest(session_directory, completed)
    return completed


def _probe_for_reference(
    manifest: ExperimentManifest,
    reference: str,
) -> ProbeManifest | None:
    reference = reference.strip()
    for probe in manifest.probes:
        if probe.friendly_name == reference or probe.device_id == reference:
            return probe
    return None


def validate_manifest(
    manifest: ExperimentManifest,
    session_directory: Path | None = None,
) -> None:
    errors: list[str] = []

    # Keep schema v1 readable/writable. calibration_inputs is an optional,
    # backward-compatible extension; acquisition-only v1 sessions remain valid.
    if manifest.schema_version != CURRENT_SCHEMA_VERSION:
        errors.append(
            "Unsupported schema_version "
            f"{manifest.schema_version}; "
            f"expected {CURRENT_SCHEMA_VERSION}."
        )

    if not manifest.experiment_id.strip():
        errors.append("experiment_id cannot be empty.")

    if not manifest.name.strip():
        errors.append("name cannot be empty.")

    if not manifest.started_at_utc.strip():
        errors.append("started_at_utc cannot be empty.")

    seen_device_ids: set[str] = set()
    seen_files: set[str] = set()

    for probe in manifest.probes:
        if not probe.device_id.strip():
            errors.append("Probe device_id cannot be empty.")

        if not probe.friendly_name.strip():
            errors.append(
                f"Probe {probe.device_id!r} has no friendly_name."
            )

        if not probe.data_file.strip():
            errors.append(
                f"Probe {probe.friendly_name!r} has no data_file."
            )

        if probe.device_id in seen_device_ids:
            errors.append(
                f"Duplicate probe device_id: {probe.device_id}"
            )
        seen_device_ids.add(probe.device_id)

        if probe.data_file in seen_files:
            errors.append(
                "Multiple probes reference data file: "
                f"{probe.data_file}"
            )
        seen_files.add(probe.data_file)

        if session_directory is not None:
            data_path = session_directory / probe.data_file
            if not data_path.is_file():
                errors.append(
                    f"Missing probe data file: {data_path}"
                )

    heater = manifest.heater

    if heater.rated_power_w is not None and heater.rated_power_w < 0:
        errors.append("rated_power_w cannot be negative.")

    if (
        heater.commanded_power_w is not None
        and heater.commanded_power_w < 0
    ):
        errors.append("commanded_power_w cannot be negative.")

    if heater.commanded_power_percent is not None:
        if not 0.0 <= heater.commanded_power_percent <= 100.0:
            errors.append(
                "commanded_power_percent must be between 0 and 100."
            )

    inputs = manifest.calibration_inputs
    if inputs is not None:
        for role_name, mapping in (
            ("chamber", inputs.chamber),
            ("body", inputs.body),
            ("validation", inputs.validation),
        ):
            if mapping is None:
                continue

            if not mapping.probe.strip():
                errors.append(
                    f"calibration_inputs.{role_name}.probe cannot be empty."
                )
                continue

            if not mapping.channel.strip():
                errors.append(
                    f"calibration_inputs.{role_name}.channel cannot be empty."
                )

            if _probe_for_reference(manifest, mapping.probe) is None:
                errors.append(
                    f"calibration_inputs.{role_name}.probe "
                    f"{mapping.probe!r} does not match a probe "
                    "friendly_name or device_id."
                )

    if errors:
        raise ManifestValidationError("\n".join(errors))


def manifest_to_dict(
    manifest: ExperimentManifest,
) -> dict[str, Any]:
    data = asdict(manifest)
    data["probes"] = [
        asdict(probe)
        for probe in manifest.probes
    ]
    data["tags"] = list(manifest.tags)

    # Avoid writing a noisy null section into acquisition-only manifests.
    if manifest.calibration_inputs is None:
        data.pop("calibration_inputs", None)

    return data


def _mapping_from_dict(
    value: dict[str, Any] | None,
) -> CalibrationInputMapping | None:
    if value is None:
        return None
    return CalibrationInputMapping(
        probe=str(value.get("probe", "")),
        channel=str(value.get("channel", "")),
    )


def manifest_from_dict(
    data: dict[str, Any],
) -> ExperimentManifest:
    probes = tuple(
        ProbeManifest(**probe)
        for probe in data.get("probes", [])
    )

    heater = HeaterManifest(**(data.get("heater", {}) or {}))
    environment = EnvironmentManifest(
        **(data.get("environment", {}) or {})
    )
    weber = WeberManifest(**(data.get("weber", {}) or {}))

    raw_inputs = data.get("calibration_inputs")
    calibration_inputs = None
    if raw_inputs is not None:
        calibration_inputs = CalibrationInputs(
            chamber=_mapping_from_dict(raw_inputs.get("chamber")),
            body=_mapping_from_dict(raw_inputs.get("body")),
            validation=_mapping_from_dict(raw_inputs.get("validation")),
        )

    manifest = ExperimentManifest(
        schema_version=data["schema_version"],
        experiment_id=data["experiment_id"],
        name=data["name"],
        started_at_utc=data["started_at_utc"],
        ended_at_utc=data.get("ended_at_utc"),
        probes=probes,
        heater=heater,
        environment=environment,
        weber=weber,
        calibration_inputs=calibration_inputs,
        notes=data.get("notes"),
        tags=tuple(data.get("tags", [])),
    )

    validate_manifest(manifest)
    return manifest


def save_manifest(
    session_directory: Path,
    manifest: ExperimentManifest,
) -> Path:
    session_directory = Path(session_directory)
    session_directory.mkdir(parents=True, exist_ok=True)

    validate_manifest(manifest)

    path = session_directory / MANIFEST_FILENAME
    temporary_path = session_directory / f"{MANIFEST_FILENAME}.tmp"

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(
            manifest_to_dict(manifest),
            file,
            indent=2,
            sort_keys=True,
        )
        file.write("\n")

    temporary_path.replace(path)
    return path


def load_manifest(
    session_directory: Path,
    validate_files: bool = True,
) -> ExperimentManifest:
    session_directory = Path(session_directory)
    path = session_directory / MANIFEST_FILENAME

    if not path.is_file():
        raise ManifestError(f"Manifest not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ManifestError(
            f"Invalid JSON in {path}: {exc}"
        ) from exc

    manifest = manifest_from_dict(data)

    validate_manifest(
        manifest,
        session_directory=(
            session_directory
            if validate_files
            else None
        ),
    )

    return manifest
