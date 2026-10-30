#!/usr/bin/env python3
"""
Add or replace explicit calibration_inputs in a session manifest.

This utility edits manifest.json only. It does not touch raw CSV data.

Example:
    python tools/apply_calibration_mapping.py \
        gui/data/sessions/20260827_193544 \
        --chamber-probe "inside in water 1" \
        --chamber-channel ambient_temperature_f \
        --body-probe "outside on top" \
        --body-channel ambient_temperature_f \
        --validation-probe "inside in water 2" \
        --validation-channel ambient_temperature_f
"""

from __future__ import annotations

import argparse
import json

from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)

    parser.add_argument(
        "--chamber-probe",
        required=True,
    )
    parser.add_argument(
        "--chamber-channel",
        required=True,
    )
    parser.add_argument(
        "--body-probe",
        required=True,
    )
    parser.add_argument(
        "--body-channel",
        required=True,
    )
    parser.add_argument(
        "--validation-probe",
    )
    parser.add_argument(
        "--validation-channel",
    )

    args = parser.parse_args()

    manifest_path = (
        args.session
        / "manifest.json"
    )

    data = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    calibration_inputs = {
        "chamber": {
            "probe": args.chamber_probe,
            "channel": args.chamber_channel,
        },
        "body": {
            "probe": args.body_probe,
            "channel": args.body_channel,
        },
    }

    if (
        args.validation_probe
        or args.validation_channel
    ):
        if not (
            args.validation_probe
            and args.validation_channel
        ):
            raise SystemExit(
                "Validation probe and channel "
                "must be supplied together."
            )

        calibration_inputs[
            "validation"
        ] = {
            "probe": (
                args.validation_probe
            ),
            "channel": (
                args.validation_channel
            ),
        }

    data["calibration_inputs"] = (
        calibration_inputs
    )

    temporary = (
        manifest_path
        .with_suffix(".json.tmp")
    )

    temporary.write_text(
        json.dumps(
            data,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(
        manifest_path
    )

    print(
        "Updated explicit calibration "
        f"mapping: {manifest_path}"
    )


if __name__ == "__main__":
    main()
