from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_LEAGUES = ("J1", "J2", "J3")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a local season dataset: player universe, league appearance records, "
            "combined appearances, Japanese-player join, and diagnostics."
        )
    )
    parser.add_argument("--season", default="2014", help="Season year, e.g. 2014.")
    parser.add_argument(
        "--league",
        action="append",
        choices=DEFAULT_LEAGUES,
        dest="leagues",
        help="League to include. Can be repeated. Defaults to J1/J2/J3.",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    leagues = args.leagues or list(DEFAULT_LEAGUES)

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

    appearance_paths = collect_leagues(
        args.season,
        leagues,
        args.sleep,
        args.interim_dir,
        args.limit_teams,
    )
    combined_path = args.interim_dir / f"appearance_records_{args.season}_{'_'.join(leagues)}.csv"
    run(
        [
            sys.executable,
            "scripts/combine_csv_files.py",
            *[str(path) for path in appearance_paths],
            "--output",
            str(combined_path),
        ]
    )

    joined_path = (
        args.processed_dir / f"appearance_records_{args.season}_{'_'.join(leagues)}_japanese_matched.csv"
    )
    unmatched_path = args.interim_dir / f"unmatched_appearance_names_{args.season}_{'_'.join(leagues)}.csv"
    ambiguous_path = args.interim_dir / f"ambiguous_appearance_names_{args.season}_{'_'.join(leagues)}.csv"
    run(
        [
            sys.executable,
            "scripts/build_joined_appearance_sample.py",
            "--players",
            str(args.player_universe),
            "--appearances",
            str(combined_path),
            "--output",
            str(joined_path),
            "--unmatched-output",
            str(unmatched_path),
            "--ambiguous-output",
            str(ambiguous_path),
        ]
    )
    run(
        [
            sys.executable,
            "scripts/summarize_joined_appearance_sample.py",
            "--input",
            str(joined_path),
        ]
    )

    print("Season dataset build complete")
    print(f"player_universe={args.player_universe}")
    print(f"combined_appearances={combined_path}")
    print(f"joined_japanese_appearances={joined_path}")
    print(f"unmatched_diagnostics={unmatched_path}")
    print(f"ambiguous_diagnostics={ambiguous_path}")


def collect_leagues(
    season: str,
    leagues: list[str],
    sleep_seconds: float,
    interim_dir: Path,
    limit_teams: int | None,
) -> list[Path]:
    outputs: list[Path] = []
    for league in leagues:
        output = interim_dir / f"appearance_records_{season}_{league}.csv"
        command = [
            sys.executable,
            "scripts/collect_appearance_records_sample.py",
            "--season",
            season,
            "--league",
            league,
            "--sleep",
            str(sleep_seconds),
            "--output",
            str(output),
        ]
        if limit_teams is not None:
            command.extend(["--limit-teams", str(limit_teams)])
        run(
            command
        )
        outputs.append(output)
    return outputs


def run(command: list[str]) -> None:
    print("$ " + " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
