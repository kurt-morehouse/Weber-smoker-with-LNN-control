from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

from core.experiment_manifest import (
    CURRENT_SCHEMA_VERSION,
    ExperimentManifest,
    ProbeManifest,
    complete_manifest,
    load_manifest,
    save_manifest,
)
from acquisition.config import AcquisitionConfig, ProbeDefinition


@dataclass(frozen=True)
class AcquisitionSession:
    session_id: str
    directory: Path
    manifest: ExperimentManifest


class SessionManager:
    def __init__(self, config: AcquisitionConfig) -> None:
        self.config = config

    def create_session(self) -> AcquisitionSession:
        return self.create_prepared_session(self.config.probes)

    def create_prepared_session(
        self,
        probes: tuple[ProbeDefinition, ...],
    ) -> AcquisitionSession:
        started = datetime.now(timezone.utc)
        base_id = started.strftime("%Y%m%d_%H%M%S")
        self.config.sessions_directory.mkdir(parents=True, exist_ok=True)
        session_id = base_id
        suffix = 1
        while (self.config.sessions_directory / session_id).exists():
            session_id = f"{base_id}_{suffix:02d}"
            suffix += 1

        directory = self.config.sessions_directory / session_id
        directory.mkdir()
        probe_manifests = tuple(
            ProbeManifest(
                device_id=probe.match_fragment,
                friendly_name=probe.friendly_name,
                data_file=probe.data_file or _filename_for(probe.friendly_name),
                role=probe.role,
            )
            for probe in probes
        )
        manifest = ExperimentManifest(
            schema_version=CURRENT_SCHEMA_VERSION,
            experiment_id=session_id,
            name=f"Weber smoker session {session_id}",
            started_at_utc=started.isoformat(),
            probes=probe_manifests,
        )
        save_manifest(directory, manifest)
        session = AcquisitionSession(session_id, directory, manifest)
        from acquisition.recorder import SessionRecorder
        SessionRecorder(session)
        return session

    def open_session(self, directory: Path) -> AcquisitionSession:
        directory = Path(directory)
        manifest = load_manifest(directory, validate_files=False)
        return AcquisitionSession(manifest.experiment_id, directory, manifest)

    def complete_session(self, session: AcquisitionSession) -> AcquisitionSession:
        manifest = complete_manifest(session.directory)
        return AcquisitionSession(session.session_id, session.directory, manifest)


def _filename_for(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "probe"
    return f"{slug}.csv"
