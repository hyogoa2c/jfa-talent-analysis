from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.reappearance import build_reappearance_candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build candidates for players who reappear in a target window after a gap "
            "in observed J.League appearances."
        )
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=Path("data/processed/player_season_features_2014_2025_J1_J2_J3.csv"),
        help="Player-season feature CSV.",
    )
    parser.add_argument("--target-start-season", type=int, required=True)
    parser.add_argument("--target-end-season", type=int, required=True)
    parser.add_argument(
        "--min-gap-seasons",
        type=int,
        default=2,
        help="Minimum number of absent seasons between observed appearance seasons.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.target_start_season > args.target_end_season:
        raise ValueError("--target-start-season must be less than or equal to --target-end-season")

    rows = read_csv(args.features)
    candidates = build_reappearance_candidates(
        rows,
        target_start_season=args.target_start_season,
        target_end_season=args.target_end_season,
        min_gap_seasons=args.min_gap_seasons,
    )
    output = args.output or Path(
        "data/processed/"
        f"reappearance_candidates_{args.target_start_season}_{args.target_end_season}"
        f"_gap{args.min_gap_seasons}.csv"
    )
    write_csv(output, candidates)
    print(f"candidates={len(candidates)}")
    print(f"wrote={output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_player_id",
        "name_ja",
        "name_en",
        "previous_observed_season",
        "reappearance_season",
        "absent_seasons",
        "reappearance_leagues",
        "reappearance_teams",
        "reappearance_minutes",
        "note",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
