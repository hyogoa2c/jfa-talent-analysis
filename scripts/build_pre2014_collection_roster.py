"""Build the Phase 1b pathway-collection rosters (SAP §7 steps 3/7).

Targets: players in the integrated career table with league appearances>0 who are NOT in
the existing 2014-2025 outcome universe (pre-2014-only careers). Split per the fixed SAP:
priority 1 = born >=1981 (confirmatory-eligible), priority 2 = born <=1980 (descriptive).
Carries birth_date and career context (seasons, teams, minutes) for the downstream
identity cross-check.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Phase 1b collection rosters.")
    parser.add_argument(
        "--career-table",
        type=Path,
        default=Path("data/processed/career_league_seasons_1999_2025.csv"),
    )
    parser.add_argument(
        "--existing-universe",
        type=Path,
        default=Path("data/processed/player_pathway_outcomes.csv"),
    )
    parser.add_argument(
        "--players",
        type=Path,
        default=Path("data/interim/player_universe_sample.csv"),
        help="SFIX03 universe CSV (name_ja / name_en / birth_date).",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/interim/pre2014")
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.existing_universe.open(encoding="utf-8", newline="") as file:
        known_ids = {row["source_player_id"] for row in csv.DictReader(file)}
    with args.players.open(encoding="utf-8", newline="") as file:
        universe = {row["source_player_id"]: row for row in csv.DictReader(file)}

    careers: dict[str, dict] = defaultdict(
        lambda: {"appearances": 0, "minutes": 0, "seasons": [], "teams": []}
    )
    with args.career_table.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            career = careers[row["source_player_id"]]
            career["appearances"] += int(row["appearances"])
            career["minutes"] += int(row["minutes"])
            if int(row["appearances"]) > 0:
                career["seasons"].append(int(row["season"]))
            for team in row["team_names"].split(";"):
                if team and team not in career["teams"]:
                    career["teams"].append(team)

    priority1: list[dict[str, str]] = []
    priority2: list[dict[str, str]] = []
    for player_id, career in careers.items():
        if player_id in known_ids or career["appearances"] == 0:
            continue
        player = universe.get(player_id)
        if player is None:
            raise ValueError(f"career-table player {player_id} missing from universe CSV")
        birth_year = int(player["birth_date"][:4]) if player["birth_date"] else None
        roster_row = {
            "source_player_id": player_id,
            "name_ja": player["name_ja"],
            "name_en": player["name_en"],
            "birth_date": player["birth_date"],
            "career_minutes": str(career["minutes"]),
            "career_appearances": str(career["appearances"]),
            "first_season": str(min(career["seasons"])),
            "last_season": str(max(career["seasons"])),
            "teams": ";".join(career["teams"]),
        }
        if birth_year is not None and birth_year >= 1981:
            priority1.append(roster_row)
        else:
            priority2.append(roster_row)

    for name, rows in [
        ("collection_roster_priority1.csv", priority1),
        ("collection_roster_priority2.csv", priority2),
    ]:
        rows.sort(key=lambda row: -int(row["career_minutes"]))
        path = args.output_dir / name
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"{name}: {len(rows)} players -> {path}")


if __name__ == "__main__":
    main()
