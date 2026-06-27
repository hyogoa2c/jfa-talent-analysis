from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

LEAGUES = ("J1", "J2", "J3")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect SFPR01 appearance records for multiple leagues in a season."
    )
    parser.add_argument("--season", default="2014", help="Season year, e.g. 2014.")
    parser.add_argument(
        "--league",
        action="append",
        choices=LEAGUES,
        dest="leagues",
        help="League to collect. Can be repeated. Defaults to J1/J2/J3.",
    )
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/interim"),
        help="Output directory for league CSVs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    leagues = args.leagues or list(LEAGUES)
    for league in leagues:
        output = args.output_dir / f"appearance_records_{args.season}_{league}.csv"
        run(
            [
                sys.executable,
                "scripts/collect_appearance_records_sample.py",
                "--season",
                args.season,
                "--league",
                league,
                "--sleep",
                str(args.sleep),
                "--output",
                str(output),
            ]
        )


def run(command: list[str]) -> None:
    print("$ " + " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
