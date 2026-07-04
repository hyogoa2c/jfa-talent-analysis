from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from jfa_talent_analysis.matching import normalize_name
from jfa_talent_analysis.sources.wikipedia import (
    extract_pathway_context,
    fetch_wikipedia_candidates,
    fetch_wikipedia_extract,
)

OUTPUT_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "wikipedia_title",
    "wikipedia_pathway_context",
    "wikipedia_found",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch candidate pre-professional pathway text from Wikipedia for a list of "
            "players. This produces research candidates for manual/semi-automated review "
            "(see docs/pathway_source_pilot_2026-07-03.md) — it does not assign a "
            "pathway_category itself."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="CSV with at least source_player_id, name_ja, name_en columns.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output CSV path.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of players.")
    parser.add_argument("--sleep", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    players = dedupe_by_player(read_csv(args.input))
    if args.limit is not None:
        players = players[: args.limit]

    rows: list[dict[str, str]] = []
    for index, player in enumerate(players, start=1):
        print(f"[{index}/{len(players)}] {player['name_ja']} / {player['name_en']}")
        title, context = fetch_pathway_context(player["name_ja"], player["name_en"])
        rows.append(
            {
                "source_player_id": player["source_player_id"],
                "name_ja": player["name_ja"],
                "name_en": player["name_en"],
                "wikipedia_title": title or "",
                "wikipedia_pathway_context": context or "",
                "wikipedia_found": "1" if title else "0",
            }
        )
        if args.sleep > 0 and index < len(players):
            time.sleep(args.sleep)

    write_csv(args.output, rows)
    found = sum(1 for row in rows if row["wikipedia_found"] == "1")
    print(f"rows={len(rows)}")
    print(f"found={found}")
    print(f"wrote={args.output}")


def fetch_pathway_context(name_ja: str, name_en: str) -> tuple[str | None, str | None]:
    direct_title = normalize_name(name_ja).replace(" ", "")
    extract = fetch_wikipedia_extract(direct_title) if direct_title else None
    title = direct_title if extract else None

    if extract is None:
        for candidate in fetch_wikipedia_candidates(name_ja, name_en, max_results=1):
            extract = fetch_wikipedia_extract(candidate.title)
            if extract is not None:
                title = candidate.title
                break

    if extract is None:
        return None, None
    return title, extract_pathway_context(extract)


def dedupe_by_player(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in rows:
        player_id = row["source_player_id"]
        if player_id in seen:
            continue
        seen.add(player_id)
        deduped.append(row)
    return deduped


def read_csv(path: Path) -> list[dict[str, str]]:
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
