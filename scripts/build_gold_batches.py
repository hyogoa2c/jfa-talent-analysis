"""Cut the worksheet into small per-rater batches (SAP §6b-2b-rate, v10).

Two things drive the cost of rating, and batching fixes both. A rater working a
long list re-sends its whole transcript every turn, so cost grows with the square
of the list; and when the API drops the run, the retry replays all of it. Five
rows per invocation keeps both linear. This changes nothing about how a row is
judged.

The batches also carry the v10 allocation: the strata where one wrong call moves
the estimate most stay double-rated, a seeded 15% reliability subsample of the
rest stays double-rated to measure rater error, and everything else is rated once
with the two raters balanced inside each stratum.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

IMPORTANT_STRATA = ("academy_out", "academy_in", "institution_unknown", "disagree_other")

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

INDEX_COLUMNS = ["batch_id", "rater", "mode", "size", "worksheet_ids"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--worksheet", type=Path, default=Path("data/manual/gold_holdout_worksheet.csv")
    )
    parser.add_argument(
        "--key", type=Path, default=Path("data/manual/gold_holdout_worksheet_key.csv")
    )
    parser.add_argument(
        "--done",
        type=Path,
        nargs="*",
        default=[Path("data/manual/gold_holdout/verdicts_pilot_rater_a.csv")],
        help="Verdict files whose worksheet_ids are already rated (the pilot).",
    )
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--reliability-fraction", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--outdir", type=Path, default=Path("data/manual/gold_holdout/batches"))
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def assign_modes(
    rows: list[dict[str, str]],
    stratum_of: dict[str, str],
    fraction: float,
    seed: int,
) -> dict[str, tuple[str, tuple[str, ...]]]:
    """worksheet_id -> (mode, raters), balancing single-rated rows inside a stratum."""
    by_stratum: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_stratum[stratum_of.get(row["worksheet_id"], "")].append(row["worksheet_id"])

    rng = np.random.default_rng(seed)
    assignment: dict[str, tuple[str, tuple[str, ...]]] = {}
    for stratum in sorted(by_stratum):
        members = sorted(by_stratum[stratum])
        order = rng.permutation(len(members))
        if stratum in IMPORTANT_STRATA:
            for index in order:
                assignment[members[index]] = ("dual_important", ("a", "b"))
            continue
        reliability = round(len(members) * fraction)
        for rank, index in enumerate(order):
            worksheet_id = members[index]
            if rank < reliability:
                assignment[worksheet_id] = ("dual_reliability", ("a", "b"))
            else:
                # Alternate so neither rater owns a stratum: a rater's habits
                # would otherwise land entirely on one kind of row.
                assignment[worksheet_id] = ("single", ("a",) if rank % 2 else ("b",))
    return assignment


def main() -> None:
    args = parse_args()
    worksheet = {row["worksheet_id"]: row for row in read_csv(args.worksheet)}
    stratum_of = {row["worksheet_id"]: row["stratum"] for row in read_csv(args.key)}

    done: set[str] = set()
    for path in args.done:
        if path.exists():
            done |= {row["worksheet_id"] for row in read_csv(path)}

    pending = [row for key, row in sorted(worksheet.items()) if key not in done]
    assignment = assign_modes(pending, stratum_of, args.reliability_fraction, args.seed)

    # Important strata first: they carry the signal, and if the budget runs out
    # mid-collection the rows we have should be the ones that matter most.
    def order_key(row: dict[str, str]) -> tuple[int, str]:
        mode = assignment[row["worksheet_id"]][0]
        rank = {"dual_important": 0, "dual_reliability": 1, "single": 2}[mode]
        return rank, row["worksheet_id"]

    queues: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in sorted(pending, key=order_key):
        mode, raters = assignment[row["worksheet_id"]]
        for rater in raters:
            queues[(rater, mode)].append(row)

    args.outdir.mkdir(parents=True, exist_ok=True)
    for stale in args.outdir.glob("batch_*.csv"):
        stale.unlink()

    index: list[dict[str, str]] = []
    counter = 0
    # Numbered by mode first, then rater: running the batches in order means both
    # raters finish the important strata before either starts on the single-rated
    # rows, so a budget that runs out early still leaves those rows double-rated.
    mode_rank = {"dual_important": 0, "dual_reliability": 1, "single": 2}
    for rater, mode in sorted(queues, key=lambda key: (mode_rank[key[1]], key[0])):
        rows = queues[(rater, mode)]
        for start in range(0, len(rows), args.batch_size):
            chunk = rows[start : start + args.batch_size]
            counter += 1
            batch_id = f"B{counter:03d}"
            path = args.outdir / f"batch_{batch_id}_rater_{rater}.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=WORKSHEET_COLUMNS + VERDICT_COLUMNS)
                writer.writeheader()
                for row in chunk:
                    blank = dict.fromkeys(VERDICT_COLUMNS, "")
                    blank["rater"] = rater
                    writer.writerow({**{c: row[c] for c in WORKSHEET_COLUMNS}, **blank})
            index.append(
                {
                    "batch_id": batch_id,
                    "rater": rater,
                    "mode": mode,
                    "size": str(len(chunk)),
                    "worksheet_ids": " ".join(r["worksheet_id"] for r in chunk),
                }
            )

    index_path = args.outdir / "batch_index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        writer.writerows(index)

    modes = Counter(mode for mode, _ in assignment.values())
    passes = sum(len(raters) for _, raters in assignment.values())
    print(f"pending={len(pending)} rated_passes={passes} batches={len(index)}")
    for mode, count in sorted(modes.items()):
        print(f"  {mode:18s} {count}")
    for rater in ("a", "b"):
        print(
            f"  rater {rater}: {sum(int(r['size']) for r in index if r['rater'] == rater)} passes"
        )
    print(f"wrote={args.outdir}")


if __name__ == "__main__":
    main()
