from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join SFPR01 appearance records to the SFIX03 Japanese player universe."
    )
    parser.add_argument(
        "--players",
        type=Path,
        default=Path("data/interim/player_universe_sample.csv"),
        help="Japanese player universe CSV from SFIX03.",
    )
    parser.add_argument(
        "--appearances",
        type=Path,
        default=Path("data/interim/appearance_records_2014_J1.csv"),
        help="Appearance records CSV from SFPR01.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/appearance_records_2014_J1_japanese_matched.csv"),
        help="Joined Japanese-player appearance records CSV.",
    )
    parser.add_argument(
        "--unmatched-output",
        type=Path,
        default=Path("data/interim/unmatched_appearance_names_2014_J1.csv"),
        help="Unmatched appearance-name diagnostics CSV.",
    )
    parser.add_argument(
        "--ambiguous-output",
        type=Path,
        default=Path("data/interim/ambiguous_appearance_names_2014_J1.csv"),
        help="Ambiguous player-name diagnostics CSV.",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=Path("data/manual/player_identity_overrides.csv"),
        help="Manual player identity overrides CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    players = read_csv(args.players)
    appearances = read_csv(args.appearances)

    player_index = index_players_by_name(players)
    player_by_id = {player["source_player_id"]: player for player in players}
    overrides = read_overrides(args.overrides)
    joined: list[dict[str, str]] = []
    unmatched: dict[str, int] = {}
    ambiguous: dict[str, list[dict[str, str]]] = {}

    for appearance in appearances:
        name = normalize_name(appearance["name_ja"])
        override_id = find_override(overrides, appearance)
        if override_id:
            player = player_by_id.get(override_id)
            if player is None:
                raise ValueError(f"Override references unknown source_player_id={override_id}")
            joined.append(join_record(appearance, player, match_method="manual_override"))
            continue

        candidates = player_index.get(name, [])
        if len(candidates) == 1:
            joined.append(join_record(appearance, candidates[0], match_method="exact_name"))
        elif len(candidates) > 1:
            ambiguous[name] = candidates
        else:
            unmatched[name] = unmatched.get(name, 0) + 1

    write_csv(args.output, joined)
    write_unmatched(args.unmatched_output, unmatched)
    write_ambiguous(args.ambiguous_output, ambiguous)

    print(f"appearance_rows={len(appearances)}")
    print(f"matched_rows={len(joined)}")
    print(f"unmatched_unique_names={len(unmatched)}")
    print(f"ambiguous_unique_names={len(ambiguous)}")
    print(f"wrote_joined={args.output}")
    print(f"wrote_unmatched={args.unmatched_output}")
    print(f"wrote_ambiguous={args.ambiguous_output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def normalize_name(value: str) -> str:
    return " ".join(value.split())


def index_players_by_name(players: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = {}
    for player in players:
        index.setdefault(normalize_name(player["name_ja"]), []).append(player)
    return index


def read_overrides(path: Path) -> list[dict[str, str]]:
    return [
        row
        for row in read_csv(path)
        if row.get("source_player_id") and row.get("name_ja")
    ]


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


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_unmatched(path: Path, unmatched: dict[str, int]) -> None:
    rows = [
        {"name_ja": name, "appearance_rows": count}
        for name, count in sorted(unmatched.items(), key=lambda item: (-item[1], item[0]))
    ]
    write_csv(path, rows)


def write_ambiguous(path: Path, ambiguous: dict[str, list[dict[str, str]]]) -> None:
    rows: list[dict[str, str]] = []
    for name, candidates in sorted(ambiguous.items()):
        for player in candidates:
            rows.append(
                {
                    "name_ja": name,
                    "source_player_id": player["source_player_id"],
                    "name_en": player["name_en"],
                    "birth_date": player["birth_date"],
                    "last_belong_team": player["last_belong_team"],
                    "position": player["position"],
                }
            )
    write_csv(path, rows)


if __name__ == "__main__":
    main()
