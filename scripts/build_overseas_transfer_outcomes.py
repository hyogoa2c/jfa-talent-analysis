from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.outcomes import OUTCOME_COLUMNS, build_overseas_transfer_outcomes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a moved_overseas outcome table from a manual overseas "
            "transfer review queue."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/manual/overseas_transfer_manual_review_queue_2023_2025_gap2.csv"),
        help="Manual review queue CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/overseas_transfer_outcomes_2023_2025_gap2.csv"),
        help="Outcome CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = build_overseas_transfer_outcomes(read_csv(args.input))
    write_csv(args.output, rows)

    basis_counts = Counter(row["moved_overseas_basis"] or "(not reviewed)" for row in rows)
    print(f"rows={len(rows)}")
    for basis, count in sorted(basis_counts.items()):
        print(f"  {basis}: {count}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTCOME_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
