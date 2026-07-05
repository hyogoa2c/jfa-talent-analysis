from __future__ import annotations

import argparse
import csv
import time
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.sources.wikipedia import (
    extract_lead_birth_date,
    fetch_wikipedia_extract,
    looks_like_junk_title,
)

IDENTITY_CHECK_COLUMN = "identity_check"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Add an identity_check column to a Wikipedia candidate CSV (from "
            "build_pathway_candidates_from_wikipedia.py or "
            "build_national_team_candidates_from_wikipedia.py). Rejects titles that "
            "look like list/character pages outright, and cross-checks the "
            "remaining candidates' lead-sentence birth date against the known "
            "player birth_date (re-fetching each candidate's full extract, since "
            "the saved context column may be a trimmed section, not the article "
            "lead). See docs/pathway_source_pilot_2026-07-03.md's Implementation "
            "Status for why this check exists: the fuzzy search fallback can match "
            "an unrelated page when a player has no article of their own."
        )
    )
    parser.add_argument("--candidates", type=Path, required=True, help="Candidate CSV to check.")
    parser.add_argument(
        "--players",
        type=Path,
        required=True,
        help="Master CSV with source_player_id and birth_date columns (e.g. "
        "player_season_features_2014_2025_J1_J2_J3.csv).",
    )
    parser.add_argument("--output", type=Path, required=True, help="Annotated output CSV path.")
    parser.add_argument("--sleep", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(args.candidates)
    birth_dates = read_birth_dates(args.players)
    context_column = detect_context_column(rows)

    checked = 0
    for index, row in enumerate(rows, start=1):
        row[IDENTITY_CHECK_COLUMN] = check_identity(row, birth_dates, context_column)
        if row[IDENTITY_CHECK_COLUMN] in {"confirmed", "birth_date_mismatch", "no_birth_date_found"}:
            checked += 1
            if args.sleep > 0:
                time.sleep(args.sleep)
        if index % 100 == 0:
            print(f"[{index}/{len(rows)}] refetched={checked}")

    write_csv(args.output, rows, context_column)
    counts = Counter(row[IDENTITY_CHECK_COLUMN] for row in rows)
    print(f"rows={len(rows)}")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    print(f"wrote={args.output}")


def check_identity(
    row: dict[str, str], birth_dates: dict[str, str], context_column: str
) -> str:
    if row.get("wikipedia_found") != "1":
        return "no_article"
    if looks_like_junk_title(row["wikipedia_title"]):
        return "title_pattern_reject"

    known_birth_date = birth_dates.get(row["source_player_id"])
    extract = fetch_wikipedia_extract(row["wikipedia_title"])
    if extract is None:
        # The page existed when originally fetched but is gone now; treat cautiously.
        return "refetch_failed"

    lead_birth_date = extract_lead_birth_date(extract)
    if lead_birth_date is None:
        return "no_birth_date_found"
    if known_birth_date is None:
        return "no_birth_date_found"
    if normalize_birth_date(lead_birth_date) == normalize_birth_date(known_birth_date):
        return "confirmed"
    return "birth_date_mismatch"


def normalize_birth_date(value: str) -> str:
    return value.replace("/", "-")


def detect_context_column(rows: list[dict[str, str]]) -> str:
    if not rows:
        raise ValueError("candidates CSV has no rows")
    for column in ("wikipedia_pathway_context", "wikipedia_national_team_context"):
        if column in rows[0]:
            return column
    raise ValueError("candidates CSV has neither a pathway nor national-team context column")


def read_birth_dates(path: Path) -> dict[str, str]:
    birth_dates: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            birth_dates.setdefault(row["source_player_id"], row["birth_date"])
    return birth_dates


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]], context_column: str) -> None:
    fieldnames = [
        "source_player_id",
        "name_ja",
        "name_en",
        "wikipedia_title",
        context_column,
        "wikipedia_found",
        IDENTITY_CHECK_COLUMN,
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
