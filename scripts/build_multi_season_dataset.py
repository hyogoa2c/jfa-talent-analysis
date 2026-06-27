from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from jfa_talent_analysis.pipeline import (
    DEFAULT_LEAGUES,
    leagues_for_season,
    summarize_season_dataset,
    write_csv,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build local season datasets over a small year range and write diagnostics."
    )
    parser.add_argument("--start-season", type=int, required=True)
    parser.add_argument("--end-season", type=int, required=True)
    parser.add_argument(
        "--league",
        action="append",
        choices=DEFAULT_LEAGUES,
        dest="leagues",
        help="League to include. Can be repeated. Defaults to J1/J2/J3 where available.",
    )
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument(
        "--limit-teams",
        type=int,
        default=None,
        help="Limit teams per league for smoke tests.",
    )
    parser.add_argument(
        "--skip-player-universe",
        action="store_true",
        help="Reuse existing player universe CSV.",
    )
    parser.add_argument(
        "--player-universe",
        type=Path,
        default=Path("data/interim/player_universe_sample.csv"),
        help="Player universe CSV path.",
    )
    parser.add_argument(
        "--interim-dir",
        type=Path,
        default=Path("data/interim"),
        help="Interim output directory.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("data/processed"),
        help="Processed output directory.",
    )
    parser.add_argument(
        "--diagnostics-output",
        type=Path,
        default=None,
        help="Diagnostics CSV path. Defaults to data/processed/multi_season_diagnostics_START_END.csv.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned season/league jobs without collecting data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_season > args.end_season:
        raise ValueError("--start-season must be less than or equal to --end-season")

    seasons = list(range(args.start_season, args.end_season + 1))
    season_leagues = {
        season: leagues_for_season(season, requested_leagues=args.leagues) for season in seasons
    }
    for season, leagues in season_leagues.items():
        print(f"planned {season}: {','.join(leagues)}")
    if args.dry_run:
        return

    if not args.skip_player_universe:
        run(
            [
                sys.executable,
                "scripts/poc_sfix03_player_universe.py",
                "--limit",
                "10000",
                "--output",
                str(args.player_universe),
            ]
        )

    diagnostics: list[dict[str, str]] = []
    for season, leagues in season_leagues.items():
        command = [
            sys.executable,
            "scripts/build_season_dataset.py",
            "--season",
            str(season),
            "--skip-player-universe",
            "--player-universe",
            str(args.player_universe),
            "--interim-dir",
            str(args.interim_dir),
            "--processed-dir",
            str(args.processed_dir),
            "--sleep",
            str(args.sleep),
        ]
        for league in leagues:
            command.extend(["--league", league])
        if args.limit_teams is not None:
            command.extend(["--limit-teams", str(args.limit_teams)])
        run(command)
        diagnostics.append(
            summarize_season_dataset(
                season=season,
                leagues=leagues,
                interim_dir=args.interim_dir,
                processed_dir=args.processed_dir,
            )
        )

    diagnostics_output = args.diagnostics_output or (
        args.processed_dir
        / f"multi_season_diagnostics_{args.start_season}_{args.end_season}.csv"
    )
    write_csv(diagnostics_output, diagnostics)
    print(f"wrote_diagnostics={diagnostics_output}")


def run(command: list[str]) -> None:
    print("$ " + " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
