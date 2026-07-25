from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from jfa_talent_analysis.sources.wikipedia import fetch_wikipedia_extract

OUTPUT_COLUMNS = ["source_player_id", "name_ja", "name_en", "wikipedia_title", "full_extract"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch and locally cache full Wikipedia plaintext extracts for every "
            "identity_check=confirmed candidate row. Unlike the original candidate "
            "fetch, the resolved title is already known, so this is one direct "
            "extract request per player (no search fallback). The full extract "
            "keeps sections the pathway/national-team context trimming dropped — "
            "notably the plain-text 出場歴 lines (e.g. 'Jリーグ初出場 - 2014年…J2 "
            "第5節…') and 所属クラブ career list needed for pre-2014 J1 debut "
            "backfill and overseas-stint detection (see "
            "docs/data_collection_revision_proposal_2026-07-07.md items 1 and 2)."
        )
    )
    parser.add_argument("--candidates", type=Path, required=True, help="A *_verified.csv file.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sleep", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_confirmed_rows(args.candidates)
    done = read_existing_ids(args.output)
    print(f"confirmed={len(rows)} already_fetched={len(done)}", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not args.output.exists()
    with args.output.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        if write_header:
            writer.writeheader()
        fetched = 0
        for index, row in enumerate(rows, start=1):
            if row["source_player_id"] in done:
                continue
            extract = fetch_wikipedia_extract(row["wikipedia_title"])
            writer.writerow(
                {
                    "source_player_id": row["source_player_id"],
                    "name_ja": row["name_ja"],
                    "name_en": row["name_en"],
                    "wikipedia_title": row["wikipedia_title"],
                    "full_extract": extract or "",
                }
            )
            file.flush()
            fetched += 1
            if fetched % 50 == 0:
                print(f"[{index}/{len(rows)}] fetched={fetched}", flush=True)
            if args.sleep > 0:
                time.sleep(args.sleep)
    print(f"done fetched={fetched} wrote={args.output}", flush=True)


def read_confirmed_rows(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as file:
        return [row for row in csv.DictReader(file) if row["identity_check"] == "confirmed"]


def read_existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as file:
        return {row["source_player_id"] for row in csv.DictReader(file)}


if __name__ == "__main__":
    main()
