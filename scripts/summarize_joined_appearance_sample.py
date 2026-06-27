from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a joined Japanese appearance sample.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/appearance_records_2014_J1_japanese_matched.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(args.input)
    unique_players = {row["source_player_id"] for row in rows}
    total_minutes = sum(parse_int(row["minutes"]) for row in rows)
    total_goals = sum(parse_int(row["goals"]) for row in rows)
    by_team = count_by(rows, "team_name")

    print(f"rows={len(rows)}")
    print(f"unique_players={len(unique_players)}")
    print(f"total_minutes={total_minutes}")
    print(f"total_goals={total_goals}")
    print("teams=")
    for team, count in sorted(by_team.items()):
        print(f"  {team}: {count}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def parse_int(value: str) -> int:
    return int(value or 0)


def count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row[key]] = counts.get(row[key], 0) + 1
    return counts


if __name__ == "__main__":
    main()
