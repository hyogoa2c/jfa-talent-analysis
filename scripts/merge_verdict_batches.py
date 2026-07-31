"""Join per-batch verdict files into one file with a header (SAP §6b-2b-rate).

The raters write bare rows -- no header, because a header is the thing a model
most reliably echoes back into the data -- while everything downstream
(`validate_gold_verdicts.py`, `compare_gold_verdicts.py`, `resolve_gold_verdicts.py`)
opens a `DictReader`. Running the validator straight at a batch file therefore
reports every row as having a category outside the vocabulary, which is a
confusing way to find out the file was fine all along.

The merge is also where a batch that came back short or doubled shows up, so it
checks the column count and the worksheet_ids rather than concatenating blindly.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

COLUMNS = [
    "worksheet_id",
    "name_ja",
    "gold_pathway_category",
    "gold_final_institution",
    "determination",
    "evidence_url",
    "evidence_quote",
    "evidence_source_type",
    "rater",
    "researched_at",
    "minutes_spent",
    "note",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--expect",
        type=Path,
        help="Batch index; checks the merged worksheet_ids against the batches' own list.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    rows: list[list[str]] = []
    problems: list[str] = []
    for path in sorted(args.batches):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for number, row in enumerate(csv.reader(handle), start=1):
                if not row:
                    continue
                if len(row) != len(COLUMNS):
                    problems.append(f"{path.name}:{number}: 列数 {len(row)}（期待 {len(COLUMNS)}）")
                    continue
                rows.append(row)

    seen = Counter(row[0] for row in rows)
    for worksheet_id, count in sorted(seen.items()):
        if count > 1:
            problems.append(f"{worksheet_id}: {count} 回現れる")

    if args.expect:
        with args.expect.open(encoding="utf-8-sig") as handle:
            wanted = {
                worksheet_id
                for entry in csv.DictReader(handle)
                for worksheet_id in entry["worksheet_ids"].split()
                if f"batch_{entry['batch_id']}_rater_{entry['rater']}.csv"
                in {path.name for path in args.batches}
            }
        for missing in sorted(wanted - set(seen)):
            problems.append(f"{missing}: バッチにあるが判定結果に無い")
        for extra in sorted(set(seen) - wanted):
            problems.append(f"{extra}: 判定結果にあるがバッチに無い")

    for problem in problems:
        print(problem, file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print(
        f"{len(args.batches)} バッチ / {len(rows)} 行 -> {args.output}（問題 {len(problems)} 件）"
    )
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
