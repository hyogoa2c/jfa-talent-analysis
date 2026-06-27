from __future__ import annotations

from jfa_talent_analysis.pipeline import LEAGUE_FRAME_IDS, leagues_for_season
from jfa_talent_analysis.sources.jleague_data_site import (
    CompetitionOption,
    create_competition_frames,
    create_competitions,
)


def audit_season_availability(
    season: int,
    requested_leagues: list[str] | None = None,
) -> list[dict[str, str]]:
    frames = create_competition_frames(str(season))
    return summarize_availability(
        season=season,
        requested_leagues=requested_leagues,
        frames=frames,
        competitions_by_frame={
            frame.select_value: create_competitions(str(season), frame.select_value)
            for frame in frames
        },
    )


def summarize_availability(
    *,
    season: int,
    requested_leagues: list[str] | None,
    frames: list[CompetitionOption],
    competitions_by_frame: dict[str, list[CompetitionOption]],
) -> list[dict[str, str]]:
    frame_by_id = {frame.select_value: frame for frame in frames}
    rows: list[dict[str, str]] = []
    for league in leagues_for_season(season, requested_leagues=requested_leagues):
        frame_id = LEAGUE_FRAME_IDS[league]
        frame = frame_by_id.get(frame_id)
        competitions = competitions_by_frame.get(frame_id, []) if frame is not None else []
        rows.append(
            {
                "season": str(season),
                "league": league,
                "expected_frame_id": frame_id,
                "frame_found": "1" if frame is not None else "0",
                "frame_display_name": frame.display_name if frame is not None else "",
                "competition_count": str(len(competitions)),
                "competition_ids": "|".join(competition.select_value for competition in competitions),
                "competition_names": "|".join(
                    competition.display_name for competition in competitions
                ),
                "available": "1" if competitions else "0",
            }
        )
    return rows
