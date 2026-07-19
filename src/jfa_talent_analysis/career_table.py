"""Integrated 1999-2025 league-career table (Phase 1b SAP §7 step 1).

Combines the pre-2014 backfill (matched_appearance_records_pre2014.csv, is_league rows
only — the SFPR01-equivalent universe per pre2014_competitions) with the existing
2014-2025 SFPR01 matched appearances into one player x season x division table.

This is a NEW output for the Phase 1b track; the Phase 1 frozen dataset is not touched.
The two sources cannot overlap by construction (archive seasons are ≤2013, SFPR01
seasons are ≥2014) and this is asserted, not assumed.
"""

from __future__ import annotations

from dataclasses import dataclass

from jfa_talent_analysis.sources.pre2014_appearances import normalize_text

# 2014-2025 SFPR01 league names (full-width) -> division code, matching the pre-2014
# competition categories (j1_league/j2_league). J3 exists only from 2014.
SFPR01_LEAGUE_DIVISIONS = {
    "J1リーグ": "J1",
    "J2リーグ": "J2",
    "J3リーグ": "J3",
}

PRE2014_CATEGORY_DIVISIONS = {
    "j1_league": "J1",
    "j2_league": "J2",
}

SOURCE_PRE2014 = "pre2014_archive"
SOURCE_SFPR01 = "sfpr01"


@dataclass
class CareerSeasonRow:
    source_player_id: str
    season: int
    division: str
    appearances: int
    minutes: int
    goals: int
    team_names: str
    source: str
    birth_date: str


def sfpr01_division(league: str) -> str | None:
    return SFPR01_LEAGUE_DIVISIONS.get(normalize_text(league))


def build_career_seasons(
    pre2014_rows: list[dict[str, str]],
    sfpr01_rows: list[dict[str, str]],
) -> list[CareerSeasonRow]:
    """Aggregate both sources to one row per (player, season, division).

    Pre-2014 J1 two-stage seasons (1999-2004: 1st/2nd stage as separate archive pages)
    are summed into a single season total here — the annual-total definition SFPR01 uses.
    """
    buckets: dict[tuple[str, int, str], dict] = {}

    def add(
        player_id: str,
        season: int,
        division: str,
        appearances: int,
        minutes: int,
        goals: int,
        team: str,
        source: str,
        birth_date: str,
    ) -> None:
        key = (player_id, season, division)
        bucket = buckets.setdefault(
            key,
            {
                "appearances": 0,
                "minutes": 0,
                "goals": 0,
                "teams": [],
                "source": source,
                "birth_date": birth_date,
            },
        )
        bucket["appearances"] += appearances
        bucket["minutes"] += minutes
        bucket["goals"] += goals
        if team and team not in bucket["teams"]:
            bucket["teams"].append(team)
        if bucket["source"] != source:
            raise ValueError(f"season {key} fed by both sources")

    for row in pre2014_rows:
        if row.get("is_league") != "true":
            continue
        division = PRE2014_CATEGORY_DIVISIONS.get(row["competition_category"])
        if division is None:
            raise ValueError(f"league row with non-league category: {row}")
        season = int(row["season_year"])
        if season > 2013:
            raise ValueError(f"pre-2014 source carries season {season}")
        add(
            row["source_player_id"],
            season,
            division,
            int(row["appearances"] or 0),
            int(row["minutes"] or 0),
            int(row["goals"] or 0),
            row["team_name"],
            SOURCE_PRE2014,
            row.get("birth_date", ""),
        )

    for row in sfpr01_rows:
        division = sfpr01_division(row["league"])
        if division is None:
            raise ValueError(f"unknown SFPR01 league: {row['league']!r}")
        season = int(row["season"])
        if season < 2014:
            raise ValueError(f"SFPR01 source carries season {season}")
        add(
            row["source_player_id"],
            season,
            division,
            int(row["appearances"] or 0),
            int(row["minutes"] or 0),
            int(row["goals"] or 0),
            row["team_name"],
            SOURCE_SFPR01,
            row.get("birth_date", ""),
        )

    return [
        CareerSeasonRow(
            source_player_id=player_id,
            season=season,
            division=division,
            appearances=bucket["appearances"],
            minutes=bucket["minutes"],
            goals=bucket["goals"],
            team_names=";".join(bucket["teams"]),
            source=bucket["source"],
            birth_date=bucket["birth_date"],
        )
        for (player_id, season, division), bucket in sorted(buckets.items())
    ]
