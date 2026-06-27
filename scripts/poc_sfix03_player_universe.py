from __future__ import annotations

import argparse
from pathlib import Path

from jfa_talent_analysis.sources.jleague_data_site import (
    fetch_sfix03_japanese_players,
    parse_sfix03_player_universe,
    write_player_universe_sample,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a small local sample of Japanese players from SFIX03/search."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum records to write.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/player_universe_sample.csv"),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    html = fetch_sfix03_japanese_players()
    records = parse_sfix03_player_universe(html)
    write_player_universe_sample(args.output, records, args.limit)
    print(f"Parsed {len(records)} Japanese player records")
    print(f"Wrote {min(len(records), args.limit)} records to {args.output}")


if __name__ == "__main__":
    main()
