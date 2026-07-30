"""Pull the verdict rows out of a rater's raw output.

Raw output is not clean CSV. The prompt echoes the worksheet rows back, models
print the block twice (once while working, once as the answer), and they add a
sentence despite being told not to. Matching on the category column separates
verdicts from the echoed worksheet, and keeping the last row per worksheet_id
takes the answer rather than the draft.

Quotes contain commas, so this parses with the csv module rather than grep.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

CATEGORIES = {"j_club_academy", "high_school", "university", "other", "unknown"}
COLUMNS = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected", type=int, default=0)
    return parser.parse_args()


def candidate_rows(text: str) -> list[list[str]]:
    """Every parseable row that looks like a verdict, in order of appearance."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("W") or line.count(",") < COLUMNS - 1:
            continue
        try:
            fields = next(csv.reader(io.StringIO(line)))
        except (csv.Error, StopIteration):
            continue
        if len(fields) >= 3 and fields[2] in CATEGORIES:
            rows.append(fields[:COLUMNS] if len(fields) > COLUMNS else fields)
    return rows


def main() -> None:
    args = parse_args()
    text = args.raw.read_text(encoding="utf-8", errors="replace")

    latest: dict[str, list[str]] = {}
    for fields in candidate_rows(text):
        if len(fields) == COLUMNS:
            latest[fields[0]] = fields  # a later row supersedes an earlier draft

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(latest[key] for key in sorted(latest))

    print(f"{args.raw.name}: {len(latest)} 行")
    if args.expected and len(latest) != args.expected:
        print(f"  期待 {args.expected} 行と一致しない", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
