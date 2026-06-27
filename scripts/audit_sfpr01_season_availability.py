from __future__ import annotations

import argparse
from pathlib import Path

from jfa_talent_analysis.pipeline import (
    DEFAULT_LEAGUES,
    write_csv,
)
from jfa_talent_analysis.sfpr01_availability import audit_season_availability


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit SFPR01 season/league competition availability."
    )
    parser.add_argument("--start-season", type=int, required=True)
    parser.add_argument("--end-season", type=int, required=True)
    parser.add_argument(
        "--league",
        action="append",
        choices=DEFAULT_LEAGUES,
        dest="leagues",
        help="League to audit. Can be repeated. Defaults to J1/J2/J3 where available.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path. Defaults to data/interim/source_audit/sfpr01_availability_START_END.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_season > args.end_season:
        raise ValueError("--start-season must be less than or equal to --end-season")

    rows: list[dict[str, str]] = []
    for season in range(args.start_season, args.end_season + 1):
        rows.extend(audit_season_availability(season, requested_leagues=args.leagues))

    output = args.output or Path(
        f"data/interim/source_audit/sfpr01_availability_{args.start_season}_{args.end_season}.csv"
    )
    write_csv(output, rows)
    print(f"wrote={output}")
    for row in rows:
        print(
            "{season} {league}: frame={frame_found} competitions={competition_count} "
            "available={available}".format(**row)
        )

if __name__ == "__main__":
    main()
