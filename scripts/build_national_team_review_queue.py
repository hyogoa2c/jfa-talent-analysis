from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.national_team_classification import (
    NATIONAL_TEAM_REVIEW_QUEUE_COLUMNS,
    build_national_team_review_queue_rows,
)

TIERS = ("a", "b", "c")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a human review queue from label_national_team_selections.py's "
            "needs_review rows across all three tiers, joining back the original "
            "Wikipedia context text. See "
            "docs/pathway_national_team_review_instructions_2026-07-05.md for how "
            "to fill in the reviewed_any_national_team_selection/reviewed_categories/"
            "reviewer_note columns."
        )
    )
    parser.add_argument(
        "--labeled-dir",
        type=Path,
        default=Path("data/interim/pathway_national_team"),
        help="Directory containing national_team_tier_{a,b,c}_labeled.csv and _verified.csv.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manual/national_team_review_queue.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    all_rows: list[dict[str, str]] = []
    for tier in TIERS:
        labeled_rows = read_csv(args.labeled_dir / f"national_team_tier_{tier}_labeled.csv")
        verified_rows = read_csv(args.labeled_dir / f"national_team_tier_{tier}_verified.csv")
        context_by_player_id = {
            row["source_player_id"]: row["wikipedia_national_team_context"]
            for row in verified_rows
        }
        all_rows.extend(
            build_national_team_review_queue_rows(labeled_rows, context_by_player_id, tier)
        )

    write_csv(args.output, all_rows)
    print(f"rows={len(all_rows)}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=NATIONAL_TEAM_REVIEW_QUEUE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
