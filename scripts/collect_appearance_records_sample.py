from __future__ import annotations

import argparse
import time
from pathlib import Path

from jfa_talent_analysis.sources.jleague_data_site import (
    AppearanceRecord,
    create_competition_frames,
    create_competitions,
    create_teams,
    fetch_sfpr01_appearance_records,
    parse_sfpr01_appearance_records,
    write_appearance_sample,
)

LEAGUE_FRAME_IDS = {
    "J1": "1",
    "J2": "2",
    "J3": "3",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect a small season-league sample of SFPR01 appearance records."
    )
    parser.add_argument("--season", default="2014", help="Season year, e.g. 2014.")
    parser.add_argument("--league", choices=sorted(LEAGUE_FRAME_IDS), default="J1")
    parser.add_argument(
        "--limit-teams",
        type=int,
        default=None,
        help="Limit number of teams for quick testing.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="Delay between team requests in seconds.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path. Defaults to data/interim/appearance_records_{season}_{league}.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or Path(f"data/interim/appearance_records_{args.season}_{args.league}.csv")
    records = collect_season_league(
        season=args.season,
        league_key=args.league,
        limit_teams=args.limit_teams,
        sleep_seconds=args.sleep,
    )
    write_appearance_sample(output, records, limit=len(records))
    print(f"Collected {len(records)} appearance records for {args.season} {args.league}")
    print(f"Wrote records to {output}")


def collect_season_league(
    *,
    season: str,
    league_key: str,
    limit_teams: int | None,
    sleep_seconds: float,
) -> list[AppearanceRecord]:
    competition_frame_id = LEAGUE_FRAME_IDS[league_key]
    league_name = find_league_name(season, competition_frame_id) or league_key
    competition_id = find_single_competition_id(season, competition_frame_id)
    teams = create_teams(competition_id)
    if limit_teams is not None:
        teams = teams[:limit_teams]

    records: list[AppearanceRecord] = []
    for index, team in enumerate(teams, start=1):
        print(f"[{index}/{len(teams)}] {season} {league_key} {team.display_name}")
        html = fetch_sfpr01_appearance_records(
            season=season,
            competition_frame_id=competition_frame_id,
            competition_id=competition_id,
            team_id=team.select_value,
            league=league_name,
            team_name=team.display_name,
        )
        team_records = parse_sfpr01_appearance_records(
            html,
            season=season,
            competition_frame_id=competition_frame_id,
            competition_id=competition_id,
            league=league_name,
            team_id=team.select_value,
            team_name=team.display_name,
        )
        records.extend(team_records)
        if sleep_seconds > 0 and index < len(teams):
            time.sleep(sleep_seconds)
    return records


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


if __name__ == "__main__":
    main()
