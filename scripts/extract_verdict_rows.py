"""Pull the verdict rows out of a rater's raw output.

Raw output is not clean CSV. The prompt echoes the worksheet rows back, models
print the block twice (once while working, once as the answer), and they add a
sentence despite being told not to. Matching on the category column separates
verdicts from the echoed worksheet, and keeping the last row per worksheet_id
takes the answer rather than the draft.

Quotes contain commas, so this parses with the csv module rather than grep.
They also contain newlines: a club's official career block is one field spread
over several lines, and reading the output line by line drops those rows without
a trace -- two of rater A's 152 single-rated rows (W381, W383) came back that
way, counted as a short batch. So the document is parsed as a whole first, and
the line-by-line pass is kept as the fallback for output the csv module cannot
read end to end.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

from jfa_talent_analysis.gold_vocabulary import CATEGORIES

COLUMNS = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected", type=int, default=0)
    return parser.parse_args()


def _looks_like_verdict(fields: list[str]) -> bool:
    return len(fields) >= 3 and fields[0].strip().startswith("W") and fields[2] in CATEGORIES


def _trimmed(fields: list[str]) -> list[str]:
    return fields[:COLUMNS] if len(fields) > COLUMNS else fields


def document_rows(text: str) -> list[list[str]]:
    """Verdict rows read from the output as one csv document, newlines and all."""
    try:
        parsed = list(csv.reader(io.StringIO(text)))
    except csv.Error:
        return []
    return [_trimmed(fields) for fields in parsed if _looks_like_verdict(fields)]


def line_rows(text: str) -> list[list[str]]:
    """Verdict rows read one line at a time, for output that will not parse whole."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("W") or line.count(",") < COLUMNS - 1:
            continue
        try:
            fields = next(csv.reader(io.StringIO(line)))
        except (csv.Error, StopIteration):
            continue
        if _looks_like_verdict(fields):
            rows.append(_trimmed(fields))
    return rows


def candidate_rows(text: str) -> list[list[str]]:
    """Every parseable row that looks like a verdict, in order of appearance.

    The line pass comes first so that the document pass, which is the one that
    keeps a multi-line quote intact, wins where both found the same row.
    """
    return line_rows(text) + document_rows(text)


def verdict_rows(text: str) -> dict[str, list[str]]:
    """One complete row per worksheet_id, taking the answer over the draft."""
    latest: dict[str, list[str]] = {}
    for fields in candidate_rows(text):
        if len(fields) == COLUMNS:
            latest[fields[0]] = fields  # a later row supersedes an earlier draft
    return latest


def main() -> None:
    args = parse_args()
    text = args.raw.read_text(encoding="utf-8", errors="replace")

    latest = verdict_rows(text)

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(latest[key] for key in sorted(latest))

    print(f"{args.raw.name}: {len(latest)} 行")
    if args.expected and len(latest) != args.expected:
        print(f"  期待 {args.expected} 行と一致しない", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
