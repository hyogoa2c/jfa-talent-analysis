from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from jfa_talent_analysis.sources.wikidata import fetch_player_team_stints, summarize_stints


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Wikidata coverage for J.League reappearance candidates."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/reappearance_candidates_2023_2025_gap2.csv"),
        help="Reappearance candidates CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/source_audit/wikidata_reappearance_candidates.csv"),
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = read_csv(args.input)
    if args.limit is not None:
        candidates = candidates[: args.limit]

    rows: list[dict[str, str]] = []
    for index, candidate in enumerate(candidates, start=1):
        print(f"[{index}/{len(candidates)}] {candidate['name_ja']} / {candidate['name_en']}")
        stints = fetch_player_team_stints(candidate["name_ja"], candidate["name_en"])
        rows.append(
            {
                **candidate,
                **summarize_stints(stints),
            }
        )
        if args.sleep > 0 and index < len(candidates):
            time.sleep(args.sleep)

    write_csv(args.output, rows)
    print(f"rows={len(rows)}")
    print(f"wrote={args.output}")


def read_csv(path: Path) -> list[dict[str, str]]:
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


if __name__ == "__main__":
    main()
