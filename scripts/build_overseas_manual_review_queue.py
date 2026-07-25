from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

from jfa_talent_analysis.overseas_review import (
    MANUAL_REVIEW_COLUMNS,
    build_manual_review_rows,
    merge_existing_review_entries,
)


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
    existing_rows = read_csv(args.output) if args.output.exists() else []
    rows, dropped_reviewed = merge_existing_review_entries(rows, existing_rows)
    for row in dropped_reviewed:
        print(
            "warning: reviewed row no longer in rebuilt queue: "
            f"source_player_id={row.get('source_player_id', '')} "
            f"name_ja={row.get('name_ja', '')} "
            f"manual_decision={row.get('manual_decision', '')}",
            file=sys.stderr,
        )
    write_csv(args.output, rows)
    print(f"rows={len(rows)}")
    print(f"existing_queue_rows={len(existing_rows)}")
    print(f"dropped_reviewed_rows={len(dropped_reviewed)}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANUAL_REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_path, path)


if __name__ == "__main__":
    main()
