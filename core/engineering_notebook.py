from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


NOTEBOOK_FILENAME = "engineering_notebook.json"
PHOTO_DIRECTORY = "engineering_photos"


@dataclass
class EngineeringNotebookPage:
    title: str = ""
    objective: str = ""
    hardware_configuration: str = ""
    modifications: str = ""
    test_conditions: str = ""
    acquisition_summary: str = ""
    analysis_highlights: str = ""
    observations: str = ""
    conclusions: str = ""
    next_actions: str = ""
    tags: list[str] = field(default_factory=list)
    photos: list[str] = field(default_factory=list)
    created_utc: str = ""
    updated_utc: str = ""

    def ensure_timestamps(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_utc:
            self.created_utc = now
        self.updated_utc = now


def notebook_path(session: Path) -> Path:
    return Path(session) / NOTEBOOK_FILENAME


def load_notebook(session: Path) -> EngineeringNotebookPage:
    session = Path(session)
    path = notebook_path(session)

    if not path.exists():
        page = EngineeringNotebookPage(title=session.name)
        page.ensure_timestamps()
        return page

    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = set(EngineeringNotebookPage.__dataclass_fields__)
    page = EngineeringNotebookPage(
        **{
            key: value
            for key, value in data.items()
            if key in allowed
        }
    )
    if not page.title:
        page.title = session.name
    return page


def save_notebook(
    session: Path,
    page: EngineeringNotebookPage,
) -> Path:
    session = Path(session)
    session.mkdir(parents=True, exist_ok=True)

    page.ensure_timestamps()

    path = notebook_path(session)
    path.write_text(
        json.dumps(asdict(page), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def attach_photos(
    session: Path,
    source_paths: list[Path],
) -> list[str]:
    session = Path(session)
    destination = session / PHOTO_DIRECTORY
    destination.mkdir(parents=True, exist_ok=True)

    attached: list[str] = []

    for source in source_paths:
        source = Path(source)
        target = destination / source.name

        counter = 2
        while target.exists():
            target = destination / (
                f"{source.stem}_{counter}{source.suffix}"
            )
            counter += 1

        shutil.copy2(source, target)
        attached.append(str(target.relative_to(session)))

    return attached


def render_markdown(
    session: Path,
    page: EngineeringNotebookPage,
) -> str:
    photos = "\n".join(
        f"- `{photo}`"
        for photo in page.photos
    ) or "- None attached"

    tags = ", ".join(page.tags) or "None"

    return f"""# {page.title or Path(session).name}

## Objective

{page.objective or "Not recorded."}

## Hardware Configuration

{page.hardware_configuration or "Not recorded."}

## Modifications

{page.modifications or "Not recorded."}

## Test Conditions

{page.test_conditions or "Not recorded."}

## Acquisition Summary

{page.acquisition_summary or "Not recorded."}

## Analysis Highlights

{page.analysis_highlights or "Not recorded."}

## Observations

{page.observations or "Not recorded."}

## Conclusions

{page.conclusions or "Not recorded."}

## Next Actions

{page.next_actions or "Not recorded."}

## Tags

{tags}

## Photos

{photos}

---
Created: {page.created_utc or "—"}  
Updated: {page.updated_utc or "—"}
"""


def save_markdown(
    session: Path,
    page: EngineeringNotebookPage,
) -> Path:
    path = Path(session) / "engineering_notebook.md"
    path.write_text(
        render_markdown(session, page),
        encoding="utf-8",
    )
    return path
