from dataclasses import dataclass
from pathlib import Path

from core.experiment_manifest import (
    ExperimentManifest,
    load_manifest,
)


@dataclass(frozen=True)
class Experiment:
    directory: Path
    manifest: ExperimentManifest

    def probe_file(
        self,
        friendly_name: str,
    ) -> Path:

        for probe in self.manifest.probes:

            if (
                probe.friendly_name
                == friendly_name
            ):
                return (
                    self.directory
                    / probe.data_file
                )

        raise KeyError(
            "No probe named "
            f"{friendly_name!r} "
            "exists in this experiment."
        )


def load_experiment(
    directory: Path,
) -> Experiment:

    directory = (
        Path(directory)
        .expanduser()
        .resolve()
    )

    manifest = load_manifest(
        directory,
        validate_files=True,
    )

    return Experiment(
        directory=directory,
        manifest=manifest,
    )
