from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine CSV files with identical headers.")
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, str]] = []
    fieldnames: list[str] | None = None
    for path in args.inputs:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if fieldnames is None:
                fieldnames = reader.fieldnames or []
            elif fieldnames != (reader.fieldnames or []):
                raise ValueError(f"Header mismatch in {path}")
            rows.extend(reader)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames or [])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Combined {len(rows)} rows into {args.output}")


if __name__ == "__main__":
    main()
