from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AmbiguousAppearance:
    appearance: dict[str, str]
    candidates: list[dict[str, str]]


@dataclass
class MatchResult:
    joined: list[dict[str, str]] = field(default_factory=list)
    unmatched_name_counts: dict[str, int] = field(default_factory=dict)
    ambiguous: list[AmbiguousAppearance] = field(default_factory=list)


def match_appearances(
    *,
    appearances: list[dict[str, str]],
    players: list[dict[str, str]],
    overrides: list[dict[str, str]],
) -> MatchResult:
    """Join appearance rows to the player universe by exact normalized name.

    Manual overrides win over name matching. Appearance names that match multiple
    players are reported as ambiguous; names with no match are counted as unmatched.
    """
    player_index = index_players_by_name(players)
    player_by_id = {player["source_player_id"]: player for player in players}
    result = MatchResult()

    for appearance in appearances:
        name = normalize_name(appearance["name_ja"])
        override_id = find_override(overrides, appearance)
        if override_id:
            player = player_by_id.get(override_id)
            if player is None:
                raise ValueError(f"Override references unknown source_player_id={override_id}")
            result.joined.append(join_record(appearance, player, match_method="manual_override"))
            continue

        candidates = player_index.get(name, [])
        if len(candidates) == 1:
            result.joined.append(join_record(appearance, candidates[0], match_method="exact_name"))
        elif len(candidates) > 1:
            result.ambiguous.append(AmbiguousAppearance(appearance=appearance, candidates=candidates))
        else:
            result.unmatched_name_counts[name] = result.unmatched_name_counts.get(name, 0) + 1

    return result


def normalize_name(value: str) -> str:
    return " ".join(value.split())


def index_players_by_name(players: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = {}
    for player in players:
        index.setdefault(normalize_name(player["name_ja"]), []).append(player)
    return index


def valid_overrides(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row.get("source_player_id") and row.get("name_ja")]


def find_override(overrides: list[dict[str, str]], appearance: dict[str, str]) -> str | None:
    for override in overrides:
        if (
            override["season"] == appearance["season"]
            and override["league"] == appearance["league"]
            and override["team_name"] == appearance["team_name"]
            and normalize_name(override["name_ja"]) == normalize_name(appearance["name_ja"])
        ):
            return override["source_player_id"]
    return None


def join_record(
    appearance: dict[str, str], player: dict[str, str], *, match_method: str
) -> dict[str, str]:
    return {
        "source_player_id": player["source_player_id"],
        "match_method": match_method,
        "name_ja": appearance["name_ja"],
        "name_en": player["name_en"],
        "birth_date": player["birth_date"],
        "position_master": player["position"],
        "last_belong_team": player["last_belong_team"],
        "season": appearance["season"],
        "league": appearance["league"],
        "team_id": appearance["team_id"],
        "team_name": appearance["team_name"],
        "shirt_number": appearance["shirt_number"],
        "appearances": appearance["appearances"],
        "minutes": appearance["minutes"],
        "goals": appearance["goals"],
        "appearance_source_url": appearance["source_url"],
        "player_source_url": player["source_url"],
    }
