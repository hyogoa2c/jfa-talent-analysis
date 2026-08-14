"""Turn rater verdicts plus adjudications into the resolved gold (SAP §6b-2b).

Precedence is simple and one-directional: an adjudicated row takes the
adjudicator's value, everything else must have both raters agreeing on the
category, and a row counts as `confirmed` only when both raters confirmed it.
A row where the raters agree on `unknown` is agreement about not knowing, not a
gold value, so it stays indeterminate.

Rows keep their `worksheet_id`. The join back to `source_player_id` happens in
the Gate A step, which is also where labels enter -- keeping it out of here means
the resolved gold can be inspected without touching the blinding boundary.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

COLUMNS = [
    "worksheet_id",
    "name_ja",
    "gold_pathway_category",
    "gold_final_institution",
    "determination",
    "resolution",
    "note",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rater-a", type=Path, action="append", default=[])
    parser.add_argument("--rater-b", type=Path, action="append", default=[])
    parser.add_argument("--adjudication", type=Path, action="append", default=[])
    parser.add_argument(
        "--single",
        type=Path,
        action="append",
        default=[],
        help="Verdicts from a single-rated layer (SAP §6b-2b-rate); taken as they stand.",
    )
    parser.add_argument("--resolved", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_all(paths: list[Path]) -> dict[str, dict[str, str]]:
    return {row["worksheet_id"]: row for path in paths for row in read_csv(path)}


def main() -> None:
    args = parse_args()
    a = read_all(args.rater_a)
    b = read_all(args.rater_b)
    adjudicated = read_all(args.adjudication)

    resolved, unresolved = [], []

    # Rows already resolved in an earlier layer (the pilot) come through as they
    # are; re-deriving them would mean re-reading verdicts their adjudication has
    # already settled.
    for path in args.resolved:
        resolved.extend({column: row[column] for column in COLUMNS} for row in read_csv(path))

    # A single-rated row has no second verdict to reconcile it with, so it enters
    # as the rater left it (SAP §6b-2b-rate (3): the row carries that rater's
    # error, and the reliability subsample is what estimates how often). The
    # vocabulary already forces `unknown` whenever the determination is not
    # `confirmed`, so no separate rule is needed for the ones the rater could not
    # settle. `resolution` keeps which rater it was, so the resolved gold can be
    # split by rating regime later.
    for path in args.single:
        for row in read_csv(path):
            resolved.append(
                {
                    "worksheet_id": row["worksheet_id"],
                    "name_ja": row["name_ja"],
                    "gold_pathway_category": row["gold_pathway_category"],
                    "gold_final_institution": row["gold_final_institution"],
                    "determination": row["determination"],
                    "resolution": f"single_{row['rater']}",
                    "note": row["note"],
                }
            )

    for worksheet_id in sorted(set(a) & set(b)):
        left, right = a[worksheet_id], b[worksheet_id]
        if worksheet_id in adjudicated:
            verdict = adjudicated[worksheet_id]
            resolved.append(
                {
                    "worksheet_id": worksheet_id,
                    "name_ja": left["name_ja"],
                    "gold_pathway_category": verdict["adjudicated_category"],
                    "gold_final_institution": verdict["adjudicated_institution"],
                    "determination": verdict["adjudicated_determination"],
                    "resolution": f"adjudicated_{verdict['review_reason']}",
                    "note": verdict["adjudicator_note"],
                }
            )
            continue

        if left["gold_pathway_category"] != right["gold_pathway_category"]:
            unresolved.append(worksheet_id)
            continue

        both_confirmed = left["determination"] == right["determination"] == "confirmed"
        category = left["gold_pathway_category"]
        resolved.append(
            {
                "worksheet_id": worksheet_id,
                "name_ja": left["name_ja"],
                "gold_pathway_category": category if both_confirmed else "unknown",
                "gold_final_institution": left["gold_final_institution"] if both_confirmed else "",
                "determination": "confirmed" if both_confirmed else "indeterminate",
                "resolution": "both_raters_agree",
                "note": "",
            }
        )

    if unresolved:
        raise SystemExit(f"裁定されていない不一致が {len(unresolved)} 件: {unresolved}")

    duplicates = [
        worksheet_id
        for worksheet_id, count in Counter(row["worksheet_id"] for row in resolved).items()
        if count > 1
    ]
    if duplicates:
        raise SystemExit(f"worksheet_id が重複している: {duplicates}")

    resolved.sort(key=lambda row: row["worksheet_id"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(resolved)

    determinations = Counter(row["determination"] for row in resolved)
    confirmed = determinations["confirmed"]
    print(f"resolved={len(resolved)} -> {args.output}")
    print(f"  confirmed {confirmed} / indeterminate {determinations['indeterminate']}")
    print(f"  判定不能率 {1 - confirmed / len(resolved):.1%}")
    for category, count in Counter(
        row["gold_pathway_category"] for row in resolved if row["determination"] == "confirmed"
    ).most_common():
        print(f"    {category:16s} {count}")


if __name__ == "__main__":
    main()
