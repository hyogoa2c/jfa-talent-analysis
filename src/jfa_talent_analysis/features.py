from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from jfa_talent_analysis.pipeline import parse_int

MIDSEASON_MONTH = 6
MIDSEASON_DAY = 30


@dataclass(frozen=True)
class PlayerSeasonKey:
    source_player_id: str
    season: int


def build_player_season_features(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    player_seasons = group_player_seasons(rows)
    first_observed = first_season_by_player(rows)
    first_j1 = first_j1_season_by_player(rows)
    cumulative_minutes: dict[str, dict[str, int]] = defaultdict(lambda: {"u21": 0, "u23": 0})
    output: list[dict[str, str]] = []

    for key in sorted(player_seasons, key=lambda item: (item.source_player_id, item.season)):
        values = player_seasons[key]
        birth_date = values["birth_date"]
        age = age_in_season(birth_date, key.season)
        minutes = values["minutes"]
        j1_minutes = values["j1_minutes"]
        if age is not None and age < 21:
            cumulative_minutes[key.source_player_id]["u21"] += minutes
        if age is not None and age < 23:
            cumulative_minutes[key.source_player_id]["u23"] += minutes

        player_first_j1 = first_j1.get(key.source_player_id)
        first_j1_age = (
            age_in_season(birth_date, player_first_j1) if player_first_j1 is not None else None
        )

        output.append(
            {
                "source_player_id": key.source_player_id,
                "name_ja": values["name_ja"],
                "name_en": values["name_en"],
                "birth_date": birth_date,
                "position_master": values["position_master"],
                "season": str(key.season),
                "age_in_season": format_optional_int(age),
                "appearances": str(values["appearances"]),
                "minutes": str(minutes),
                "goals": str(values["goals"]),
                "leagues": "|".join(sorted(values["leagues"])),
                "teams": "|".join(sorted(values["teams"])),
                "j1_minutes": str(j1_minutes),
                "u21_minutes_to_date": str(cumulative_minutes[key.source_player_id]["u21"]),
                "u23_minutes_to_date": str(cumulative_minutes[key.source_player_id]["u23"]),
                "first_observed_season": str(first_observed[key.source_player_id]),
                "first_j1_season": format_optional_int(player_first_j1),
                "first_j1_age": format_optional_int(first_j1_age),
                "reached_j1": "1" if player_first_j1 is not None else "0",
            }
        )

    return output


def group_player_seasons(rows: list[dict[str, str]]) -> dict[PlayerSeasonKey, dict]:
    grouped: dict[PlayerSeasonKey, dict] = {}
    for row in rows:
        key = PlayerSeasonKey(row["source_player_id"], int(row["season"]))
        if key not in grouped:
            grouped[key] = {
                "name_ja": row["name_ja"],
                "name_en": row["name_en"],
                "birth_date": row["birth_date"],
                "position_master": row["position_master"],
                "appearances": 0,
                "minutes": 0,
                "goals": 0,
                "j1_minutes": 0,
                "leagues": set(),
                "teams": set(),
            }
        values = grouped[key]
        appearances = parse_int(row.get("appearances", ""))
        minutes = parse_int(row.get("minutes", ""))
        goals = parse_int(row.get("goals", ""))
        values["appearances"] += appearances
        values["minutes"] += minutes
        values["goals"] += goals
        values["leagues"].add(row["league"])
        values["teams"].add(row["team_name"])
        if is_j1(row["league"]):
            values["j1_minutes"] += minutes
    return grouped


def first_season_by_player(rows: list[dict[str, str]]) -> dict[str, int]:
    output: dict[str, int] = {}
    for row in rows:
        player_id = row["source_player_id"]
        season = int(row["season"])
        output[player_id] = min(output.get(player_id, season), season)
    return output


def first_j1_season_by_player(rows: list[dict[str, str]]) -> dict[str, int]:
    output: dict[str, int] = {}
    for row in rows:
        if not is_j1(row["league"]):
            continue
        player_id = row["source_player_id"]
        season = int(row["season"])
        output[player_id] = min(output.get(player_id, season), season)
    return output


def age_in_season(birth_date: str, season: int) -> int | None:
    born = parse_birth_date(birth_date)
    if born is None:
        return None
    reference = date(season, MIDSEASON_MONTH, MIDSEASON_DAY)
    age = reference.year - born.year
    if (reference.month, reference.day) < (born.month, born.day):
        age -= 1
    return age


def parse_birth_date(value: str) -> date | None:
    parts = value.split("/")
    if len(parts) != 3:
        return None
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def is_j1(league: str) -> bool:
    return "Ｊ１" in league or "J1" in league


def format_optional_int(value: int | None) -> str:
    return "" if value is None else str(value)
