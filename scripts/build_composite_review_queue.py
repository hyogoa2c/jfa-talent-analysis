"""Queue the rows the SAP §1b-3 composite rule refuses to label on its own.

Gate A cannot pass while adjudication is outstanding, and the composite rule
deliberately produces no label for four situations: either procedure flagged the
row, the club list would take a player out of the reference category, or the
club list contradicts a value a reviewer confirmed without seeing it. Each needs
a human, so each is written out with the evidence both procedures used --
including the parsed career list, which is the decisive evidence for exactly
these cases and which reviewers were previously consulting ad hoc.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

COLUMNS = [
    "source_player_id",
    "era",
    "birth_year",
    "composite_reason",
    "prose_category",
    "club_list_category",
    "club_list_institution",
    "club_history",
    "reviewed_pathway_category",
    "reviewer_note",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pooled",
        type=Path,
        default=Path("data/processed/pooled_player_outcomes_1999_2025.csv"),
    )
    parser.add_argument(
        "--stints",
        type=Path,
        default=Path("data/interim/coach_network/player_institution_stints.csv"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/manual/pathway_review_queue_composite.csv")
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite a queue that already holds adjudications."
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def format_history(rows: list[dict[str, str]]) -> str:
    """The career list as one line, so a reviewer can read the ordering."""
    ordered = sorted(rows, key=lambda row: int(row["line_index"]))
    parts = []
    for row in ordered:
        years = "-".join(filter(None, (row.get("from_year", ""), row.get("to_year", ""))))
        formality = "[2種/特別指定]" if row.get("registration_formality") == "1" else ""
        parts.append(f"{row['institution']}{f'({years})' if years else ''}{formality}")
    return " → ".join(parts)


def main() -> None:
    args = parse_args()
    stints: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(args.stints):
        stints[row["source_player_id"]].append(row)

    queue = []
    for row in read_csv(args.pooled):
        if row["eligible_confirmatory"] != "1":
            continue
        if row["pathway_category_source"] != "needs_review":
            continue
        player_id = row["source_player_id"]
        history = stints.get(player_id, [])
        queue.append(
            {
                "source_player_id": player_id,
                "era": row["era"],
                "birth_year": row["birth_year"],
                "composite_reason": row["pathway_composite_reason"],
                "prose_category": row["pathway_prose_category"],
                "club_list_category": row["pathway_club_list_category"],
                "club_list_institution": "",
                "club_history": format_history(history),
                "reviewed_pathway_category": "",
                "reviewer_note": "",
            }
        )

    # era1 first: its rows are the ones the review flagged as least verified.
    queue.sort(key=lambda row: (row["era"], int(row["source_player_id"])))

    # Once a queue is adjudicated it feeds the pipeline, so the rows it used to
    # hold no longer appear as needs_review -- regenerating over it would erase
    # the adjudications that removed them. Refuse rather than overwrite.
    if args.output.exists():
        existing = read_csv(args.output)
        adjudicated = [row for row in existing if row.get("reviewed_pathway_category", "").strip()]
        if adjudicated and not args.force:
            raise SystemExit(
                f"{args.output} already holds {len(adjudicated)} adjudicated rows; "
                "refusing to overwrite. Pass --force to replace it, or write "
                "elsewhere with --output."
            )

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(queue)

    print(f"wrote={args.output} rows={len(queue)}")
    by_reason: dict[tuple[str, str], int] = defaultdict(int)
    for row in queue:
        by_reason[(row["era"], row["composite_reason"])] += 1
    for (era, reason), count in sorted(by_reason.items()):
        print(f"  {era} {reason}: {count}")


if __name__ == "__main__":
    main()
