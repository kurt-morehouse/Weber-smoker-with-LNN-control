from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ProbeDefinition:
    match_fragment: str
    friendly_name: str
    role: str | None = None
    data_file: str | None = None


@dataclass(frozen=True)
class AcquisitionConfig:
    probes: tuple[ProbeDefinition, ...] = field(default_factory=tuple)
    sessions_directory: Path = Path(__file__).resolve().parents[1] / "data/sessions"
    record_interval_seconds: float = 2.0
    stale_timeout_seconds: float = 10.0


# Probe IDs are learned from advertisements and can be labeled in the GUI.
DEFAULT_PROBES: tuple[ProbeDefinition, ...] = ()

CONFIG = AcquisitionConfig(probes=DEFAULT_PROBES)
