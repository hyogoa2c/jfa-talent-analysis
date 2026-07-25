from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.overseas_classification import (
    OVERSEAS_LABEL_COLUMNS,
    classify_overseas_stint,
)

TIERS = ("a", "b", "c")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Classify senior-career foreign-club stints from cached full "
            "Wikipedia extracts, extending moved_overseas coverage from the 33 "
            "manually-reviewed reappearance-gap players to the full confirmed "
            "population. See docs/data_collection_revision_proposal_2026-07-07.md "
            "item 2. 'no' means no evidence in the article, not a verified "
            "domestic-only career."
        )
    )
    parser.add_argument(
        "--extracts-dir", type=Path, default=Path("data/interim/wikipedia_full_extracts")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/wikipedia_full_extracts/overseas_stints_labeled.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, str]] = []
    for tier in TIERS:
        path = args.extracts_dir / f"tier_{tier}.csv"
        if not path.exists():
            print(f"skipping missing {path}")
            continue
        for record in read_csv(path):
            result = classify_overseas_stint(record["full_extract"])
            rows.append(
                {
                    "source_player_id": record["source_player_id"],
                    "name_ja": record["name_ja"],
                    "name_en": record["name_en"],
                    "wikipedia_title": record["wikipedia_title"],
                    "moved_overseas_wiki": result.moved_overseas,
                    "overseas_confidence": result.confidence,
                    "overseas_evidence": result.evidence,
                    "overseas_reason": result.reason,
                }
            )

    write_csv(args.output, rows)
    print(f"rows={len(rows)}")
    print("moved_overseas_wiki:")
    for value, count in sorted(Counter(row["moved_overseas_wiki"] for row in rows).items()):
        print(f"  {value}: {count}")
    print("overseas_confidence:")
    for value, count in sorted(Counter(row["overseas_confidence"] for row in rows).items()):
        print(f"  {value}: {count}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OVERSEAS_LABEL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
