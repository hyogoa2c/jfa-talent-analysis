from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from jfa_talent_analysis.coach_exposure import (
    PATHWAY_TO_STAGE,
    institution_stage,
    select_primary_dev_coach,
)

OUTPUT_COLUMNS = [
    "source_player_id",
    "name_ja",
    "pathway_category",
    "primary_dev_coach",
    "primary_dev_institution",
    "primary_dev_role_type",
    "primary_dev_overlap_years",
    "n_dev_stage_coaches",
    "all_dev_stage_coaches",  # pipe-joined, all coaches at the pathway-stage institution(s)
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Phase A: collapse the many-to-many player x coach exposure table "
            "into one row per player naming their single most-attributable "
            "development coach — the head coach at the player's terminal "
            "pathway-stage institution with the greatest stint x tenure year "
            "overlap. The multi-membership set (all stage coaches) is kept "
            "alongside for fraction-based features. This is the clean unit the "
            "coach-pathway (Phase C) analysis attaches coach attributes to."
        )
    )
    parser.add_argument(
        "--exposures",
        type=Path,
        default=Path("data/interim/coach_network/player_coach_exposures.csv"),
    )
    parser.add_argument(
        "--outcomes", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/coach_network/player_primary_dev_coach.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    csv.field_size_limit(10_000_000)
    with args.exposures.open(encoding="utf-8-sig", newline="") as file:
        exposures = list(csv.DictReader(file))
    with args.outcomes.open(encoding="utf-8-sig", newline="") as file:
        pathway_by_player = {
            row["source_player_id"]: row["pathway_category"] for row in csv.DictReader(file)
        }

    exposures_by_player: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in exposures:
        exposures_by_player[row["source_player_id"]].append(row)

    output_rows: list[dict[str, str]] = []
    no_stage_match = 0
    for player_id, player_exposures in exposures_by_player.items():
        pathway = pathway_by_player.get(player_id, "")
        target_stage = PATHWAY_TO_STAGE.get(pathway)
        name_ja = player_exposures[0]["name_ja"]

        stage_exposures = [
            exposure
            for exposure in player_exposures
            if target_stage is not None
            and institution_stage(exposure["normalized_institution"]) == target_stage
        ]
        primary = select_primary_dev_coach(stage_exposures)
        if primary is None:
            no_stage_match += 1

        stage_coaches = sorted({exposure["coach_name"] for exposure in stage_exposures})
        output_rows.append(
            {
                "source_player_id": player_id,
                "name_ja": name_ja,
                "pathway_category": pathway,
                "primary_dev_coach": primary.coach_name if primary else "",
                "primary_dev_institution": primary.institution if primary else "",
                "primary_dev_role_type": primary.role_type if primary else "",
                "primary_dev_overlap_years": str(primary.overlap_years) if primary else "",
                "n_dev_stage_coaches": str(len(stage_coaches)),
                "all_dev_stage_coaches": "|".join(stage_coaches),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(output_rows)

    total = len(output_rows)
    with_primary = sum(1 for r in output_rows if r["primary_dev_coach"])
    print(f"players with any coach exposure={total}")
    print(f"  with an identifiable primary development coach={with_primary} "
          f"({with_primary / total * 100:.0f}%)")
    print(f"  no coach at their pathway stage (exposure only at other stages)={no_stage_match}")
    print(f"wrote={args.output}")


if __name__ == "__main__":
    main()
