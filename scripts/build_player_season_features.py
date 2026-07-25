from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.features import build_player_season_features


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build player-season analytical features from joined appearance records."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/appearance_records_2014_J1_J2_J3_japanese_matched.csv"),
        help="Joined Japanese-player appearance CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/player_season_features_2014_J1_J2_J3.csv"),
        help="Player-season feature CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(args.input)
    features = build_player_season_features(rows)
    write_csv(args.output, features)
    print(f"input_rows={len(rows)}")
    print(f"player_season_rows={len(features)}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
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


if __name__ == "__main__":
    main()
