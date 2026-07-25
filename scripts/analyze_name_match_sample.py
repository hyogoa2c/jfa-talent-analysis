from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.matching import normalize_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze simple name matching between SFPR01 appearances and SFIX03 players."
    )
    parser.add_argument(
        "--players",
        type=Path,
        default=Path("data/interim/player_universe_sample.csv"),
        help="Player universe CSV from SFIX03.",
    )
    parser.add_argument(
        "--appearances",
        type=Path,
        default=Path("data/interim/appearance_records_2014_J1.csv"),
        help="Appearance records CSV from SFPR01.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    players = read_csv(args.players)
    appearances = read_csv(args.appearances)

    player_names = {normalize_name(row["name_ja"]) for row in players}
    appearance_names = [normalize_name(row["name_ja"]) for row in appearances]
    matched = [name for name in appearance_names if name in player_names]
    unmatched = sorted(set(name for name in appearance_names if name not in player_names))

    total_rows = len(appearance_names)
    total_unique = len(set(appearance_names))
    matched_unique = len(set(matched))
    match_rate = matched_unique / total_unique if total_unique else 0

    print(f"appearance_rows={total_rows}")
    print(f"appearance_unique_names={total_unique}")
    print(f"player_universe_names={len(player_names)}")
    print(f"matched_unique_names={matched_unique}")
    print(f"simple_name_match_rate={match_rate:.3f}")
    print("unmatched_sample=" + ", ".join(unmatched[:30]))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


if __name__ == "__main__":
    main()
