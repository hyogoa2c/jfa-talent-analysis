"""Build the integrated 1999-2025 league-career table (Phase 1b SAP §7 step 1).

Inputs: the pre-2014 matched archive rows (league pages only) and the existing 2014-2025
SFPR01 matched appearances. Output: data/processed/career_league_seasons_1999_2025.csv,
one row per player x season x division. Phase 1's frozen dataset is not modified.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, fields
from pathlib import Path

from jfa_talent_analysis.career_table import CareerSeasonRow, build_career_seasons


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 1999-2025 league-career table.")
    parser.add_argument(
        "--pre2014",
        type=Path,
        default=Path("data/interim/pre2014/matched_appearance_records_pre2014.csv"),
    )
    parser.add_argument(
        "--sfpr01",
        type=Path,
        default=Path(
            "data/processed/appearance_records_2014_2025_J1_J2_J3_japanese_matched.csv"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/career_league_seasons_1999_2025.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pre2014 = read_csv(args.pre2014)
    sfpr01 = read_csv(args.sfpr01)
    rows = build_career_seasons(pre2014, sfpr01)

    fieldnames = [f.name for f in fields(CareerSeasonRow)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)

    players = {row.source_player_id for row in rows}
    pre_players = {r.source_player_id for r in rows if r.source == "pre2014_archive"}
    sfpr_players = {r.source_player_id for r in rows if r.source == "sfpr01"}
    seasons = [row.season for row in rows]
    print(
        f"rows={len(rows)} players={len(players)} seasons={min(seasons)}-{max(seasons)} "
        f"pre2014_only={len(pre_players - sfpr_players)} "
        f"overlap={len(pre_players & sfpr_players)} "
        f"sfpr01_only={len(sfpr_players - pre_players)}"
    )
    print(f"wrote {args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


if __name__ == "__main__":
    main()
