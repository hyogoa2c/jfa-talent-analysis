"""The one list of adjudicated pathway review queues.

Phase 1 and Phase 1b both resolve the same exposure from the same labels, so
they have to read the same queues. They did not: `pathway_review_queue_gate_a.csv`
was registered in neither for a while and then in only one, which meant 48
adjudications reached no dataset and later reached only half of them. Keeping the
list in one importable place is what stops that recurring.

A queue belongs here only once a human has been through the file, because the
resolver reads a blank reviewed column as "confirmed as-is". Listing an
unadjudicated queue silently confirms its own rows.
"""

from __future__ import annotations

import csv
from pathlib import Path

PATHWAY_REVIEW_QUEUES: tuple[Path, ...] = (
    Path("data/manual/pathway_review_queue.csv"),
    Path("data/manual/phase1_pathway_youth_vs_university_review_queue.csv"),
    Path("data/manual/pre2014_pathway_review_queue.csv"),
    Path("data/manual/pre2014_pathway_review_queue_p2.csv"),
    Path("data/manual/pre2014_pathway_review_queue_supplement.csv"),
    Path("data/manual/pathway_review_queue_gate_a.csv"),
    Path("data/manual/pathway_review_queue_composite.csv"),
    Path("data/manual/pathway_review_queue_stale_unknown.csv"),
)

# Queues whose reviewers had the parsed career list in front of them. Their
# verdicts are final even when the verdict is "unknown"; elsewhere an unknown
# predates the career list being in scope, so it is stale rather than a finding
# (SAP §1b-5).
CLUB_LIST_AWARE_QUEUES: tuple[Path, ...] = (
    Path("data/manual/pathway_review_queue_composite.csv"),
    Path("data/manual/pathway_review_queue_stale_unknown.csv"),
)


def read_queue_rows(paths: tuple[Path, ...] = PATHWAY_REVIEW_QUEUES) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def club_list_aware_ids() -> set[str]:
    return {row["source_player_id"] for row in read_queue_rows(CLUB_LIST_AWARE_QUEUES)}
