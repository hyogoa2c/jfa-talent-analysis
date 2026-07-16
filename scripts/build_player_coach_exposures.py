from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.coach_network import (
    is_gap_placeholder,
    normalize_institution_name,
    years_overlap,
)

OUTPUT_COLUMNS = [
    "source_player_id",
    "name_ja",
    "institution",
    "normalized_institution",
    "stint_from_year",
    "stint_to_year",
    "coach_name",
    "role_type",
    "tenure_from_year",
    "tenure_to_year",
    "confidence",
    "source_batch",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Join player_institution_stints.csv against coach_tenures_canonical.csv "
            "on normalized institution + year-range overlap: one output row per "
            "(player stint, coach tenure) pair where the player was plausibly at "
            "that institution while that coach held that role there. This is the "
            "'was exposed to coach Y' layer, not a claim of direct interaction — "
            "see docs/coach_network_design_2026-07-10.md's analytical cautions."
        )
    )
    parser.add_argument(
        "--stints",
        type=Path,
        default=Path("data/interim/coach_network/player_institution_stints.csv"),
    )
    parser.add_argument(
        "--tenures",
        type=Path,
        default=Path("data/interim/coach_network/coach_tenures_canonical.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/coach_network/player_coach_exposures.csv"),
    )
    return parser.parse_args()


def parse_year(value: str) -> int | None:
    return int(value) if value else None


def main() -> None:
    args = parse_args()

    csv.field_size_limit(10_000_000)
    with args.stints.open(encoding="utf-8", newline="") as file:
        stint_rows = list(csv.DictReader(file))
    with args.tenures.open(encoding="utf-8", newline="") as file:
        tenure_rows = list(csv.DictReader(file))

    gap_placeholder_count = sum(
        1 for row in tenure_rows if is_gap_placeholder(row["coach_name"], row["role_type"])
    )
    tenures_by_institution: dict[str, list[dict[str, str]]] = {}
    for row in tenure_rows:
        if is_gap_placeholder(row["coach_name"], row["role_type"]):
            continue
        tenures_by_institution.setdefault(row["normalized_institution"], []).append(row)

    researched_institutions = set(tenures_by_institution)

    exposures: list[dict[str, str]] = []
    stints_at_researched_institutions = 0
    stints_with_no_year_overlap = 0

    for stint in stint_rows:
        if stint["registration_formality"] == "1":
            continue
        normalized = normalize_institution_name(stint["institution"])
        tenures = tenures_by_institution.get(normalized)
        if not tenures:
            continue
        stints_at_researched_institutions += 1
        stint_from = parse_year(stint["from_year"])
        stint_to = parse_year(stint["to_year"])
        matched_any = False
        for tenure in tenures:
            tenure_from = parse_year(tenure["from_year"])
            tenure_to = parse_year(tenure["to_year"])
            if not years_overlap(stint_from, stint_to, tenure_from, tenure_to):
                continue
            matched_any = True
            exposures.append(
                {
                    "source_player_id": stint["source_player_id"],
                    "name_ja": stint["name_ja"],
                    "institution": stint["institution"],
                    "normalized_institution": normalized,
                    "stint_from_year": stint["from_year"],
                    "stint_to_year": stint["to_year"],
                    "coach_name": tenure["coach_name"],
                    "role_type": tenure["role_type"],
                    "tenure_from_year": tenure["from_year"],
                    "tenure_to_year": tenure["to_year"],
                    "confidence": tenure["confidence"],
                    "source_batch": tenure["source_batch"],
                }
            )
        if not matched_any:
            stints_with_no_year_overlap += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(exposures)

    distinct_players = {row["source_player_id"] for row in exposures}
    print(f"gap-placeholder tenure rows excluded from join={gap_placeholder_count}")
    print(f"researched institutions (normalized)={len(researched_institutions)}")
    print(f"player stints at a researched institution={stints_at_researched_institutions}")
    print(
        f"  of which no coach found for the stint's exact years="
        f"{stints_with_no_year_overlap} "
        f"({stints_with_no_year_overlap / stints_at_researched_institutions * 100:.1f}%)"
    )
    print(f"exposure rows written={len(exposures)}")
    print(f"distinct players with >=1 coach exposure={len(distinct_players)}")
    top_coaches = Counter(row["coach_name"] for row in exposures).most_common(10)
    print("top coaches by matched player-exposure rows:")
    for name, count in top_coaches:
        print(f"  {count:4d}  {name}")
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
