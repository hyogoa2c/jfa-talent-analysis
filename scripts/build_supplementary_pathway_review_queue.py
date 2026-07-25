from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.pathway_classification import (
    PATHWAY_REVIEW_QUEUE_COLUMNS,
    build_pathway_review_queue_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a review queue for needs_review rows that no existing queue covers. "
            "Whenever the classifier is re-run after a change, rows that used to be "
            "auto high-confidence can become needs_review; those players were never "
            "put in front of a reviewer, so they would silently keep an unverified "
            "label. This script diffs the current labeled files against the queues "
            "already reviewed and emits only the gap."
        )
    )
    parser.add_argument(
        "--labeled",
        type=Path,
        action="append",
        required=True,
        help="A *_labeled.csv. Repeatable; each needs a matching --verified.",
    )
    parser.add_argument(
        "--verified",
        type=Path,
        action="append",
        required=True,
        help="The *_verified.csv supplying wikipedia_pathway_context, in the same order.",
    )
    parser.add_argument(
        "--reviewed-queue",
        type=Path,
        action="append",
        default=None,
        help="An already-reviewed queue whose players should be excluded. Repeatable.",
    )
    parser.add_argument("--tier", default="", help="Value for the queue's tier column.")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if len(args.labeled) != len(args.verified):
        raise SystemExit("--labeled and --verified must be given the same number of times")

    already_reviewed = {
        row["source_player_id"]
        for queue_path in args.reviewed_queue or []
        for row in read_csv(queue_path)
    }

    rows: list[dict[str, str]] = []
    for labeled_path, verified_path in zip(args.labeled, args.verified, strict=True):
        context_by_player_id = {
            row["source_player_id"]: row["wikipedia_pathway_context"]
            for row in read_csv(verified_path)
        }
        rows.extend(
            build_pathway_review_queue_rows(
                read_csv(labeled_path), context_by_player_id, args.tier
            )
        )

    gap = [row for row in rows if row["source_player_id"] not in already_reviewed]
    write_csv(args.output, gap)
    print(f"needs_review={len(rows)} already_reviewed={len(rows) - len(gap)} gap={len(gap)}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so the file survives a round trip through Excel unchanged.
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=PATHWAY_REVIEW_QUEUE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
