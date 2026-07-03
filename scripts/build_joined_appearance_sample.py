from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.matching import (
    AmbiguousAppearance,
    match_appearances,
    normalize_name,
    valid_overrides,
)


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
    overrides = valid_overrides(read_csv(args.overrides))

    result = match_appearances(appearances=appearances, players=players, overrides=overrides)

    write_csv(args.output, result.joined)
    write_unmatched(args.unmatched_output, result.unmatched_name_counts)
    write_ambiguous(args.ambiguous_output, result.ambiguous)

    print(f"appearance_rows={len(appearances)}")
    print(f"matched_rows={len(result.joined)}")
    print(f"unmatched_unique_names={len(result.unmatched_name_counts)}")
    print(
        "ambiguous_unique_names="
        f"{len({normalize_name(item.appearance['name_ja']) for item in result.ambiguous})}"
    )
    print(f"wrote_joined={args.output}")
    print(f"wrote_unmatched={args.unmatched_output}")
    print(f"wrote_ambiguous={args.ambiguous_output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


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


def write_ambiguous(path: Path, ambiguous: list[AmbiguousAppearance]) -> None:
    rows: list[dict[str, str]] = []
    for item in sorted(
        ambiguous,
        key=lambda item: (
            item.appearance["season"],
            item.appearance["league"],
            item.appearance["team_name"],
            item.appearance["name_ja"],
        ),
    ):
        for player in item.candidates:
            rows.append(
                {
                    "season": item.appearance["season"],
                    "league": item.appearance["league"],
                    "team_name": item.appearance["team_name"],
                    "shirt_number": item.appearance["shirt_number"],
                    "name_ja": item.appearance["name_ja"],
                    "appearances": item.appearance["appearances"],
                    "minutes": item.appearance["minutes"],
                    "goals": item.appearance["goals"],
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
