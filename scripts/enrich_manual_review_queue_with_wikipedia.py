from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path

from jfa_talent_analysis.sources.wikipedia import (
    fetch_wikipedia_candidates,
    summarize_wikipedia_candidates,
)

WIKIPEDIA_COLUMNS = [
    "wikipedia_titles",
    "wikipedia_urls",
    "wikipedia_search_error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add Wikipedia search candidates to an overseas manual review queue."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/manual/overseas_transfer_manual_review_queue_2023_2025_gap2.csv"),
        help="Manual review queue CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/manual/overseas_transfer_manual_review_queue_2023_2025_gap2.csv"),
        help="Output CSV. Defaults to updating the input file.",
    )
    parser.add_argument("--language", default="ja")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=0.2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(args.input)
    limit = len(rows) if args.limit is None else min(args.limit, len(rows))
    target_rows = rows[:limit]

    enriched_rows: list[dict[str, str]] = []
    for index, row in enumerate(target_rows, start=1):
        print(f"[{index}/{len(target_rows)}] {row['name_ja']} / {row['name_en']}")
        try:
            candidates = fetch_wikipedia_candidates(
                row["name_ja"],
                row["name_en"],
                language=args.language,
                max_results=args.max_results,
            )
            wikipedia_summary = {
                **summarize_wikipedia_candidates(candidates),
                "wikipedia_search_error": "",
            }
        except Exception as error:
            # Keep any previously fetched candidates so a transient failure never
            # erases earlier enrichment results on re-run.
            wikipedia_summary = {
                "wikipedia_titles": row.get("wikipedia_titles", ""),
                "wikipedia_urls": row.get("wikipedia_urls", ""),
                "wikipedia_search_error": f"{type(error).__name__}: {error}",
            }
        enriched_rows.append({**row, **wikipedia_summary})
        if args.sleep > 0 and index < len(target_rows):
            time.sleep(args.sleep)

    # Keep rows beyond --limit so a partial enrichment run never truncates the queue.
    output_rows = enriched_rows + rows[limit:]
    write_csv(args.output, output_rows, build_fieldnames(rows))
    print(f"enriched_rows={len(enriched_rows)}")
    print(f"rows={len(output_rows)}")
    print(f"wrote={args.output}")


def build_fieldnames(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return WIKIPEDIA_COLUMNS
    fieldnames = list(rows[0].keys())
    for column in WIKIPEDIA_COLUMNS:
        if column in fieldnames:
            fieldnames.remove(column)
    insert_index = fieldnames.index("manual_decision") if "manual_decision" in fieldnames else len(fieldnames)
    return fieldnames[:insert_index] + WIKIPEDIA_COLUMNS + fieldnames[insert_index:]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_path, path)


if __name__ == "__main__":
    main()
