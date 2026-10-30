from pathlib import Path

from core.experiment_repository import (
    ExperimentRepository,
)


DEFAULT_SESSION_ROOT = Path(__file__).resolve().parents[1] / "data/sessions"


class SessionStore:

    def __init__(
        self,
        root: Path = DEFAULT_SESSION_ROOT,
    ) -> None:

        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def set_root(
        self,
        root: Path,
    ) -> None:

        self._root = Path(root)

    def sessions(
        self,
    ) -> tuple[Path, ...]:

        repository = (
            ExperimentRepository(
                self._root
            )
        )

        return (
            repository
            .experiment_directories()
        )

    def summaries(self):

        repository = (
            ExperimentRepository(
                self._root
            )
        )

        return repository.summaries()
