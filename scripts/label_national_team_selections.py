from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.national_team_classification import (
    NATIONAL_TEAM_LABEL_COLUMNS,
    build_national_team_label_rows,
)

CONTEXT_COLUMN = "wikipedia_national_team_context"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply the national-team-selection heuristic classifier to a "
            "verify_wikipedia_candidate_identity.py output CSV. Only identity_check="
            "confirmed rows are labeled; others are kept with a blank result for "
            "coverage visibility. See docs/national_team_pilot_2026-07-03.md's "
            "Labeling Phase section for accuracy/coverage notes."
        )
    )
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(args.candidates)
    labeled = build_national_team_label_rows(rows, CONTEXT_COLUMN)
    write_csv(args.output, labeled)

    selection_counts = Counter(
        row["any_national_team_selection"] or "(not confirmed)" for row in labeled
    )
    confidence_counts = Counter(
        row["national_team_confidence"] or "(not confirmed)" for row in labeled
    )
    print(f"rows={len(labeled)}")
    print("any_national_team_selection:")
    for selection, count in sorted(selection_counts.items()):
        print(f"  {selection}: {count}")
    print("national_team_confidence:")
    for confidence, count in sorted(confidence_counts.items()):
        print(f"  {confidence}: {count}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=NATIONAL_TEAM_LABEL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
