from __future__ import annotations

import argparse
from pathlib import Path

from jfa_talent_analysis.sources.jleague_data_site import (
    create_competition_frames,
    create_competitions,
    create_teams,
    fetch_sfpr01_appearance_records,
    parse_sfpr01_appearance_records,
    sfpr01_search_url,
    write_appearance_sample,
)

LEAGUE_FRAME_IDS = {
    "J1": "1",
    "J2": "2",
    "J3": "3",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local sample of player appearance records from SFPR01."
    )
    parser.add_argument("--season", default="2014", help="Season year, e.g. 2014.")
    parser.add_argument("--league", choices=sorted(LEAGUE_FRAME_IDS), default="J1")
    parser.add_argument("--team-id", default="1", help="J.League Data Site team ID.")
    parser.add_argument("--team-name", default="鹿島", help="Team display name.")
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum records to write.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/appearance_records_sample.csv"),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    competition_frame_id = LEAGUE_FRAME_IDS[args.league]
    league_name = find_league_name(args.season, competition_frame_id) or args.league
    competition_id = find_single_competition_id(args.season, competition_frame_id)

    html = fetch_sfpr01_appearance_records(
        season=args.season,
        competition_frame_id=competition_frame_id,
        competition_id=competition_id,
        team_id=args.team_id,
        league=league_name,
        team_name=args.team_name,
    )
    source_url = sfpr01_search_url(
        season=args.season,
        competition_frame_id=competition_frame_id,
        competition_id=competition_id,
        team_id=args.team_id,
        league=league_name,
        team_name=args.team_name,
    )
    records = parse_sfpr01_appearance_records(
        html,
        season=args.season,
        competition_frame_id=competition_frame_id,
        competition_id=competition_id,
        league=league_name,
        team_id=args.team_id,
        team_name=args.team_name,
        source_url=source_url,
    )
    write_appearance_sample(args.output, records, args.limit)
    print(
        "Parsed "
        f"{len(records)} appearance records for {args.season} {args.league} {args.team_name}"
    )
    print(f"Wrote {min(len(records), args.limit)} records to {args.output}")


def find_league_name(season: str, competition_frame_id: str) -> str | None:
    for option in create_competition_frames(season):
        if option.select_value == competition_frame_id:
            return option.display_name
    return None


def find_single_competition_id(season: str, competition_frame_id: str) -> str:
    competitions = create_competitions(season, competition_frame_id)
    if len(competitions) != 1:
        raise ValueError(
            f"Expected one competition for {season=} {competition_frame_id=}, "
            f"got {len(competitions)}"
        )
    return competitions[0].select_value


def list_team_options(competition_id: str) -> list[tuple[str, str]]:
    return [(option.select_value, option.display_name) for option in create_teams(competition_id)]


if __name__ == "__main__":
    main()
