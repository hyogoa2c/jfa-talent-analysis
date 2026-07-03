from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from jfa_talent_analysis.matching import index_players_by_name, normalize_name
from jfa_talent_analysis.sources.jleague_data_site import (
    fetch_sfix04_player_profile,
    parse_sfix04_player_season_history,
    sfix04_player_url,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Suggest manual identity overrides for ambiguous SFPR01 names using "
            "SFIX04 player season histories."
        )
    )
    parser.add_argument(
        "--players",
        type=Path,
        default=Path("data/interim/player_universe_sample.csv"),
        help="Japanese player universe CSV from SFIX03.",
    )
    parser.add_argument(
        "--appearance",
        action="append",
        required=True,
        type=Path,
        dest="appearances",
        help="SFPR01 appearance CSV. Can be repeated.",
    )
    parser.add_argument(
        "--ambiguous",
        action="append",
        required=True,
        type=Path,
        dest="ambiguous_files",
        help="Ambiguous diagnostics CSV. Can be repeated.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/suggested_player_identity_overrides.csv"),
    )
    parser.add_argument("--sleep", type=float, default=0.2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    players = read_csv(args.players)
    appearances = [row for path in args.appearances for row in read_csv(path)]
    ambiguous_names = {
        normalize_name(row["name_ja"])
        for path in args.ambiguous_files
        for row in read_csv(path)
        if row.get("name_ja")
    }
    player_index = index_players_by_name(players)
    histories = fetch_candidate_histories(
        {
            player["source_player_id"]
            for name in ambiguous_names
            for player in player_index.get(name, [])
        },
        sleep_seconds=args.sleep,
    )
    suggestions = suggest_overrides(
        appearances=appearances,
        ambiguous_names=ambiguous_names,
        player_index=player_index,
        histories=histories,
    )
    write_csv(args.output, suggestions)
    print(f"ambiguous_names={len(ambiguous_names)}")
    print(f"suggested_overrides={len(suggestions)}")
    print(f"wrote={args.output}")


def suggest_overrides(
    *,
    appearances: list[dict[str, str]],
    ambiguous_names: set[str],
    player_index: dict[str, list[dict[str, str]]],
    histories: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for appearance in appearances:
        name = normalize_name(appearance["name_ja"])
        if name not in ambiguous_names:
            continue
        candidates = player_index.get(name, [])
        matched_candidates = [
            candidate
            for candidate in candidates
            if has_matching_history(
                histories.get(candidate["source_player_id"], []),
                season=appearance["season"],
                team_name=appearance["team_name"],
            )
        ]
        if len(matched_candidates) != 1:
            continue
        key = (
            appearance["season"],
            appearance["league"],
            appearance["team_name"],
            appearance["name_ja"],
        )
        if key in seen:
            continue
        seen.add(key)
        player = matched_candidates[0]
        suggestions.append(
            {
                "season": appearance["season"],
                "league": appearance["league"],
                "team_name": appearance["team_name"],
                "name_ja": appearance["name_ja"],
                "source_player_id": player["source_player_id"],
                "note": f"SFIX04 season/team history: {sfix04_player_url(player['source_player_id'])}",
            }
        )
    return sorted(
        suggestions,
        key=lambda row: (row["season"], row["league"], row["team_name"], row["name_ja"]),
    )


def fetch_candidate_histories(
    source_player_ids: set[str], *, sleep_seconds: float
) -> dict[str, list[dict[str, str]]]:
    histories: dict[str, list[dict[str, str]]] = {}
    for index, player_id in enumerate(sorted(source_player_ids), start=1):
        print(f"[{index}/{len(source_player_ids)}] SFIX04 player_id={player_id}")
        html = fetch_sfix04_player_profile(player_id)
        histories[player_id] = [
            {
                "season": record.season,
                "team_name": record.team_name,
                "league": record.league,
                "appearances": str(record.appearances or 0),
            }
            for record in parse_sfix04_player_season_history(
                html,
                source_player_id=player_id,
                source_url=sfix04_player_url(player_id),
            )
        ]
        if sleep_seconds > 0 and index < len(source_player_ids):
            time.sleep(sleep_seconds)
    return histories


def has_matching_history(
    histories: list[dict[str, str]], *, season: str, team_name: str
) -> bool:
    normalized_team = normalize_team_name(team_name)
    return any(
        history["season"] == season
        and normalize_team_name(history["team_name"]) == normalized_team
        and int(history.get("appearances") or 0) > 0
        for history in histories
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["season", "league", "team_name", "name_ja", "source_player_id", "note"]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_team_name(value: str) -> str:
    return normalize_name(value).replace("岩手", "盛岡")


if __name__ == "__main__":
    main()
