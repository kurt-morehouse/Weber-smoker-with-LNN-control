from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


NOTES_FILENAME = "experiment_notes.json"


@dataclass
class ExperimentNotes:
    description: str = ""
    objective: str = ""
    results: str = ""
    conclusions: str = ""
    tags: list[str] = field(default_factory=list)


def notes_path(session: Path) -> Path:
    return session / NOTES_FILENAME


def load_experiment_notes(session: Path) -> ExperimentNotes:
    path = notes_path(session)

    if not path.exists():
        return ExperimentNotes()

    data = json.loads(path.read_text(encoding="utf-8"))

    return ExperimentNotes(
        description=str(data.get("description", "")),
        objective=str(data.get("objective", "")),
        results=str(data.get("results", "")),
        conclusions=str(data.get("conclusions", "")),
        tags=[str(tag) for tag in data.get("tags", [])],
    )


def save_experiment_notes(session: Path, notes: ExperimentNotes) -> None:
    path = notes_path(session)
    path.write_text(
        json.dumps(asdict(notes), indent=2) + "\n",
        encoding="utf-8",
    )
