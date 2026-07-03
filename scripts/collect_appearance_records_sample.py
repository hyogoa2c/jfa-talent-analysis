from __future__ import annotations

import argparse
import csv
import time
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path

from jfa_talent_analysis.pipeline import LEAGUE_FRAME_IDS
from jfa_talent_analysis.sources.jleague_data_site import (
    AppearanceRecord,
    create_competition_frames,
    create_competitions,
    create_teams,
    fetch_sfpr01_appearance_records,
    parse_sfpr01_appearance_records,
    sfpr01_search_url,
)

EXCLUDED_TEAM_NAMES = {"J-22"}


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
    # Write per-team batches as they arrive so a failed run keeps everything
    # fetched so far instead of discarding hours of collection.
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(AppearanceRecord.__dataclass_fields__.keys())
    total = 0
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for team_records in iter_team_appearance_records(
            season=args.season,
            league_key=args.league,
            limit_teams=args.limit_teams,
            sleep_seconds=args.sleep,
        ):
            writer.writerows(asdict(record) for record in team_records)
            file.flush()
            total += len(team_records)
    print(f"Collected {total} appearance records for {args.season} {args.league}")
    print(f"Wrote records to {output}")


def iter_team_appearance_records(
    *,
    season: str,
    league_key: str,
    limit_teams: int | None,
    sleep_seconds: float,
) -> Iterator[list[AppearanceRecord]]:
    competition_frame_id = LEAGUE_FRAME_IDS[league_key]
    league_name = find_league_name(season, competition_frame_id) or league_key
    competition_ids = find_competition_ids(season, competition_frame_id)

    for competition_index, competition_id in enumerate(competition_ids, start=1):
        teams = create_teams(competition_id)
        teams = [team for team in teams if team.display_name not in EXCLUDED_TEAM_NAMES]
        if limit_teams is not None:
            teams = teams[:limit_teams]

        for team_index, team in enumerate(teams, start=1):
            print(
                f"[competition {competition_index}/{len(competition_ids)} "
                f"team {team_index}/{len(teams)}] {season} {league_key} {team.display_name}"
            )
            html = fetch_sfpr01_appearance_records(
                season=season,
                competition_frame_id=competition_frame_id,
                competition_id=competition_id,
                team_id=team.select_value,
                league=league_name,
                team_name=team.display_name,
            )
            source_url = sfpr01_search_url(
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
                source_url=source_url,
            )
            yield team_records
            is_last_team = (
                competition_index == len(competition_ids)
                and team_index == len(teams)
            )
            if sleep_seconds > 0 and not is_last_team:
                time.sleep(sleep_seconds)


def find_league_name(season: str, competition_frame_id: str) -> str | None:
    for option in create_competition_frames(season):
        if option.select_value == competition_frame_id:
            return option.display_name
    return None


def find_competition_ids(season: str, competition_frame_id: str) -> list[str]:
    competitions = create_competitions(season, competition_frame_id)
    if not competitions:
        raise ValueError(
            f"Expected at least one competition for {season=} {competition_frame_id=}"
        )
    return [competition.select_value for competition in competitions]


if __name__ == "__main__":
    main()
