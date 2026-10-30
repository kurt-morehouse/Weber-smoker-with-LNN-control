from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path

from acquisition.config import ProbeDefinition


LOGGER = logging.getLogger(__name__)
UNKNOWN_PROBE_PREFIX = "Unknown Probe"
LABELS_PATH = Path(__file__).resolve().parents[1] / "probe_labels.json"


class ProbeRegistry:
    def __init__(
        self,
        definitions: tuple[ProbeDefinition, ...],
        labels_path: Path = LABELS_PATH,
    ) -> None:
        self._definitions = list(definitions)
        self._labels_path = Path(labels_path)
        self._reported_unknown_addresses: set[str] = set()
        self._load_labels()

    @property
    def definitions(self) -> tuple[ProbeDefinition, ...]:
        return tuple(self._definitions)

    def friendly_name_for(self, address: str) -> str:
        normalized_address = address.upper()
        for definition in sorted(
            self._definitions,
            key=lambda item: len(item.match_fragment),
            reverse=True,
        ):
            fragment = definition.match_fragment.upper()
            if fragment in normalized_address:
                return definition.friendly_name

        if address not in self._reported_unknown_addresses:
            LOGGER.warning("Unknown Chef iQ probe discovered: %s", address)
            self._reported_unknown_addresses.add(address)

        return f"{UNKNOWN_PROBE_PREFIX} {address[-8:]}"

    def set_friendly_name(self, address: str, friendly_name: str) -> None:
        friendly_name = friendly_name.strip()
        if not friendly_name:
            raise ValueError("Probe label cannot be empty.")

        normalized_address = address.upper()
        for index, definition in enumerate(self._definitions):
            fragment = definition.match_fragment.upper()
            if fragment in normalized_address or normalized_address in fragment:
                self._definitions[index] = replace(
                    definition,
                    match_fragment=address,
                    friendly_name=friendly_name,
                )
                break
        else:
            self._definitions.append(
                ProbeDefinition(
                    match_fragment=address,
                    friendly_name=friendly_name,
                )
            )

        self._reported_unknown_addresses.discard(address)
        self._save_labels()

    def _load_labels(self) -> None:
        if not self._labels_path.is_file():
            return
        try:
            data = json.loads(self._labels_path.read_text(encoding="utf-8"))
            labels = data.get("probes", [])
            if not isinstance(labels, list):
                raise ValueError("'probes' must be a list")
            for item in labels:
                address = str(item.get("device_id", "")).strip()
                name = str(item.get("friendly_name", "")).strip()
                if address and name:
                    self._set_definition(address, name)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            LOGGER.exception("Could not load probe labels from %s", self._labels_path)

    def _set_definition(self, address: str, friendly_name: str) -> None:
        normalized = address.upper()
        for index, definition in enumerate(self._definitions):
            if definition.match_fragment.upper() == normalized:
                self._definitions[index] = replace(
                    definition,
                    friendly_name=friendly_name,
                )
                return
        self._definitions.append(
            ProbeDefinition(match_fragment=address, friendly_name=friendly_name)
        )

    def _save_labels(self) -> None:
        self._labels_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._labels_path.with_suffix(".json.tmp")
        data = {
            "probes": [
                {
                    "device_id": definition.match_fragment,
                    "friendly_name": definition.friendly_name,
                }
                for definition in self._definitions
            ]
        }
        temporary_path.write_text(
            json.dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self._labels_path)
