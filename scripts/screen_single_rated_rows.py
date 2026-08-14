"""Queue the single-rated rows that need a second opinion (SAP §6b-2b-screen, v12).

Single rating buys the remaining 305 rows at half the cost and accepts that a
rater's mistakes stay in the data. The reliability subsample showed that one of
those mistakes is not random: rater A filed two academy→university→pro players
under the academy, and in both rows A's own note named the university. So the
rows that can carry that error announce themselves, and the second rater can be
spent on those instead of on all of them.

This reads one rater's verdicts, flags them with `gold_screen`, and writes
re-rating batches addressed to the *other* rater in the same format
`run_gold_rater.sh` already consumes. Nothing here decides anything: a flagged
row is rated again, and the two verdicts go through the normal comparison and
adjudication path.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from jfa_talent_analysis.gold_screen import screen_rows

WORKSHEET_COLUMNS = [
    "worksheet_id",
    "name_ja",
    "name_en",
    "birth_date",
    "first_observed_season",
    "last_observed_season",
    "senior_clubs",
]

VERDICT_COLUMNS = [
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

REPORT_COLUMNS = ["worksheet_id", "name_ja", "rated_by", "category", "institution", "reason"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verdicts", type=Path, required=True, help="One rater's merged verdicts.")
    parser.add_argument("--second-rater", required=True, choices=("a", "b"))
    parser.add_argument(
        "--worksheet", type=Path, default=Path("data/manual/gold_holdout_worksheet.csv")
    )
    parser.add_argument(
        "--outdir", type=Path, default=Path("data/manual/gold_holdout/screen_batches")
    )
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--prefix", default="S", help="Batch id prefix, kept out of the B series.")
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    args = parse_args()
    verdicts = read_csv(args.verdicts)
    worksheet = {row["worksheet_id"]: row for row in read_csv(args.worksheet)}

    flagged = screen_rows(verdicts)
    missing = [row["worksheet_id"] for row, _ in flagged if row["worksheet_id"] not in worksheet]
    if missing:
        raise SystemExit(f"ワークシートに無い worksheet_id: {missing}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        for row, reason in flagged:
            writer.writerow(
                {
                    "worksheet_id": row["worksheet_id"],
                    "name_ja": row["name_ja"],
                    "rated_by": row["rater"],
                    "category": row["gold_pathway_category"],
                    "institution": row["gold_final_institution"],
                    "reason": reason,
                }
            )

    args.outdir.mkdir(parents=True, exist_ok=True)
    rater = args.second_rater
    batches = 0
    for start in range(0, len(flagged), args.batch_size):
        chunk = flagged[start : start + args.batch_size]
        batches += 1
        path = args.outdir / f"batch_{args.prefix}{batches:03d}_rater_{rater}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=WORKSHEET_COLUMNS + VERDICT_COLUMNS)
            writer.writeheader()
            for row, _ in chunk:
                blank = dict.fromkeys(VERDICT_COLUMNS, "")
                blank["rater"] = rater
                source = worksheet[row["worksheet_id"]]
                writer.writerow({**{c: source[c] for c in WORKSHEET_COLUMNS}, **blank})

    print(
        f"{len(verdicts)} 行中 {len(flagged)} 行が要再判定"
        f"（{len(flagged) / len(verdicts):.1%}）-> rater {rater} / {batches} バッチ"
    )
    print(f"report={args.report} batches={args.outdir}")


if __name__ == "__main__":
    main()
