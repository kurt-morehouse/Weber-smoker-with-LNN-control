from dataclasses import dataclass
from pathlib import Path

from core.experiment import (
    Experiment,
    load_experiment,
)

from core.experiment_manifest import (
    MANIFEST_FILENAME,
)


@dataclass(frozen=True)
class ExperimentSummary:
    directory: Path
    experiment_id: str
    name: str
    started_at_utc: str
    ended_at_utc: str | None
    probe_count: int


class ExperimentRepository:

    def __init__(
        self,
        root: Path,
    ) -> None:

        self.root = Path(root)

    def experiment_directories(
        self,
    ) -> tuple[Path, ...]:

        if not self.root.is_dir():
            return ()

        directories = []

        for directory in self.root.iterdir():

            if not directory.is_dir():
                continue

            manifest_path = (
                directory
                / MANIFEST_FILENAME
            )

            if manifest_path.is_file():

                directories.append(
                    directory
                )

        return tuple(
            sorted(
                directories,
                reverse=True,
            )
        )

    def load(
        self,
        directory: Path,
    ) -> Experiment:

        return load_experiment(
            directory
        )

    def summaries(
        self,
    ) -> tuple[
        ExperimentSummary,
        ...
    ]:

        results = []

        for directory in (
            self.experiment_directories()
        ):

            try:

                experiment = (
                    self.load(
                        directory
                    )
                )

            except Exception:
                continue

            manifest = (
                experiment.manifest
            )

            results.append(
                ExperimentSummary(
                    directory=directory,
                    experiment_id=(
                        manifest
                        .experiment_id
                    ),
                    name=manifest.name,
                    started_at_utc=(
                        manifest
                        .started_at_utc
                    ),
                    ended_at_utc=(
                        manifest
                        .ended_at_utc
                    ),
                    probe_count=len(
                        manifest.probes
                    ),
                )
            )

        return tuple(results)
