from __future__ import annotations

import argparse
from pathlib import Path

from jfa_talent_analysis.features import build_player_season_features
from jfa_talent_analysis.pipeline import (
    DEFAULT_LEAGUES,
    leagues_for_season,
    read_csv,
    season_dataset_paths,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build player-season features from multiple joined season datasets."
    )
    parser.add_argument("--start-season", type=int, required=True)
    parser.add_argument("--end-season", type=int, required=True)
    parser.add_argument(
        "--league",
        action="append",
        choices=DEFAULT_LEAGUES,
        dest="leagues",
        help="League set used when season datasets were built. Defaults to J1/J2/J3 where available.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Processed input/output directory.",
    )
    parser.add_argument(
        "--interim-dir",
        type=Path,
        default=Path("data/interim"),
        help="Interim directory used to infer season dataset paths.",
    )
    parser.add_argument(
        "--combined-output",
        type=Path,
        default=None,
        help="Combined joined appearance CSV path.",
    )
    parser.add_argument(
        "--features-output",
        type=Path,
        default=None,
        help="Player-season feature CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_season > args.end_season:
        raise ValueError("--start-season must be less than or equal to --end-season")

    rows: list[dict[str, str]] = []
    for season in range(args.start_season, args.end_season + 1):
        leagues = leagues_for_season(season, requested_leagues=args.leagues)
        paths = season_dataset_paths(
            season=season,
            leagues=leagues,
            interim_dir=args.interim_dir,
            processed_dir=args.processed_dir,
        )
        season_rows = read_csv(paths["joined"])
        if not season_rows:
            raise ValueError(f"No joined rows found for {season}: {paths['joined']}")
        rows.extend(season_rows)

    combined_output = args.combined_output or (
        args.processed_dir
        / f"appearance_records_{args.start_season}_{args.end_season}_J1_J2_J3_japanese_matched.csv"
    )
    features_output = args.features_output or (
        args.processed_dir
        / f"player_season_features_{args.start_season}_{args.end_season}_J1_J2_J3.csv"
    )
    features = build_player_season_features(rows)
    write_csv(combined_output, rows)
    write_csv(features_output, features)
    print(f"combined_rows={len(rows)}")
    print(f"player_season_rows={len(features)}")
    print(f"wrote_combined={combined_output}")
    print(f"wrote_features={features_output}")


if __name__ == "__main__":
    main()
