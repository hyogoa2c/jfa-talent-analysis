from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.club_history_extraction import (
    is_registration_formality,
    parse_club_history,
)

OUTPUT_COLUMNS = [
    "source_player_id",
    "name_ja",
    "line_index",
    "from_year",
    "to_year",
    "institution",
    "annotation",
    "block",
    "youth_flag",
    "registration_formality",
]

TIERS = ("a", "b", "c")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse every cached Wikipedia extract's 所属クラブ section into ordered "
            "player-institution stints with year ranges — the player side of the "
            "coach-network linkage (player -> institution×years -> coach-at-the-"
            "time). See data/interim/coach_network/ for the institution-side pilot."
        )
    )
    parser.add_argument(
        "--extracts-dir", type=Path, default=Path("data/interim/wikipedia_full_extracts")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/coach_network/player_institution_stints.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[dict[str, str]] = []
    players_total = 0
    players_with_stints = 0

    for tier in TIERS:
        for record in read_csv(args.extracts_dir / f"tier_{tier}.csv"):
            players_total += 1
            stints = parse_club_history(record["full_extract"])
            if stints:
                players_with_stints += 1
            for stint in stints:
                rows.append(
                    {
                        "source_player_id": record["source_player_id"],
                        "name_ja": record["name_ja"],
                        "line_index": str(stint.line_index),
                        "from_year": str(stint.from_year or ""),
                        "to_year": str(stint.to_year or ""),
                        "institution": stint.institution,
                        "annotation": stint.annotation,
                        "block": stint.block,
                        "youth_flag": "1" if stint.youth_flag else "0",
                        "registration_formality": "1" if is_registration_formality(stint) else "0",
                    }
                )

    write_csv(args.output, rows)
    print(f"players={players_total} with_stints={players_with_stints} "
          f"({players_with_stints / players_total * 100:.1f}%)")
    print(f"stint rows={len(rows)}")
    youth_rows = [r for r in rows if r["youth_flag"] == "1"]
    dated_youth = [r for r in youth_rows if r["from_year"]]
    print(f"youth-flagged rows={len(youth_rows)}, of which dated={len(dated_youth)} "
          f"({len(dated_youth) / len(youth_rows) * 100:.1f}%)")
    top = Counter(r["institution"] for r in youth_rows).most_common(10)
    print("top youth institutions:")
    for name, count in top:
        print(f"  {count:4d}  {name}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
