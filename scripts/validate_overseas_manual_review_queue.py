from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from jfa_talent_analysis.overseas_review import validate_manual_review_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an overseas manual review queue CSV.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/manual/overseas_transfer_manual_review_queue_2023_2025_gap2.csv"),
        help="Manual review queue CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors = validate_manual_review_rows(read_csv(args.input))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        raise SystemExit(1)
    print("manual review queue is valid")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


if __name__ == "__main__":
    main()
