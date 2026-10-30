from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def inspect(path: Path) -> None:
    counts = Counter()
    types = defaultdict(Counter)
    unique_payloads = defaultdict(set)
    rssi_ranges = {}

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            address = row["address"]
            counts[address] += 1
            types[address][row["packet_type_hex"]] += 1
            unique_payloads[address].add(row["payload_hex"])
            try:
                rssi = int(row["rssi_dbm"])
                lo, hi = rssi_ranges.get(address, (rssi, rssi))
                rssi_ranges[address] = (min(lo, rssi), max(hi, rssi))
            except ValueError:
                pass

    print(f"Raw BLE file: {path}")
    print(f"Devices: {len(counts)}")
    for address, count in counts.most_common():
        print()
        print(address)
        print(f"  packets: {count}")
        print(f"  unique payloads: {len(unique_payloads[address])}")
        if address in rssi_ranges:
            lo, hi = rssi_ranges[address]
            print(f"  RSSI range: {lo} .. {hi} dBm")
        print("  packet types:")
        for packet_type, number in types[address].most_common():
            print(f"    {packet_type or '<empty>'}: {number}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    inspect(args.csv)


if __name__ == "__main__":
    main()
