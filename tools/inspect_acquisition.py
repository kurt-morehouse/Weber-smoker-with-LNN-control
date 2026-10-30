from __future__ import annotations

import sys
from pathlib import Path

from core.acquisition_integrity import analyze_csv


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m tools.inspect_acquisition <csv> [csv ...]")
        return 2

    for argument in sys.argv[1:]:
        report = analyze_csv(Path(argument))
        print()
        print(report.path)
        print("=" * len(str(report.path)))
        print(f"Samples: {report.samples:,}")
        print(f"Duration: {report.duration_seconds / 3600.0:.3f} h")
        print(f"Median interval: {report.median_interval_seconds}")

        for channel in report.channels:
            print(
                f"{channel.name}: min={channel.minimum}, max={channel.maximum}, "
                f"last={channel.last_value}, longest unchanged="
                f"{channel.longest_unchanged_run} samples / "
                f"{channel.longest_unchanged_seconds:.1f} s"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
