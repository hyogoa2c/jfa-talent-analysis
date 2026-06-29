from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.overseas_review import MANUAL_REVIEW_COLUMNS, build_manual_review_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a manual review queue from a Wikidata overseas transfer audit."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/interim/source_audit/wikidata_reappearance_candidates.csv"),
        help="Wikidata reappearance audit CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manual/overseas_transfer_manual_review_queue.csv"),
        help="Manual review queue CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = build_manual_review_rows(read_csv(args.input))
    write_csv(args.output, rows)
    print(f"rows={len(rows)}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANUAL_REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
