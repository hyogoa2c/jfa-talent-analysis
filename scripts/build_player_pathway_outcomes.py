from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.analysis_dataset import (
    PLAYER_PATHWAY_OUTCOMES_COLUMNS,
    apply_review_overrides,
    build_player_pathway_outcomes,
    collapse_player_season_features,
)

TIERS = ("a", "b", "c")

# The youth-vs-university queue resolves the university<->j_club_academy cases the
# hardened classifier (commit 76ba3c4 + the university-competition guard) deliberately
# routes to review instead of auto-flipping; see docs/measurement_equivalence_phase1b_
# 2026-07-20.md. It is disjoint from the original queue but is applied last regardless.
PATHWAY_REVIEW_QUEUE_DEFAULTS = (
    Path("data/manual/pathway_review_queue.csv"),
    Path("data/manual/phase1_pathway_youth_vs_university_review_queue.csv"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the Step 5 analysis-ready dataset (docs/data_collection_plan.md): "
            "join player-season features with resolved pathway_category, "
            "any_national_team_selection, and moved_overseas outcomes into one row "
            "per player."
        )
    )
    parser.add_argument(
        "--season-features",
        type=Path,
        default=Path("data/processed/player_season_features_2014_2025_J1_J2_J3.csv"),
    )
    parser.add_argument(
        "--pathway-national-team-dir",
        type=Path,
        default=Path("data/interim/pathway_national_team"),
    )
    parser.add_argument(
        "--pathway-review-queue",
        type=Path,
        action="append",
        dest="pathway_review_queues",
        help=(
            "Human review of the pathway classifier's needs_review rows. Repeatable; "
            "queues are applied in the order given, so a later queue wins for a player "
            "reviewed in more than one. Defaults to PATHWAY_REVIEW_QUEUE_DEFAULTS."
        ),
    )
    parser.add_argument(
        "--national-team-review-queue",
        type=Path,
        default=Path("data/manual/national_team_review_queue.csv"),
    )
    parser.add_argument(
        "--overseas-outcomes",
        type=Path,
        default=Path("data/processed/overseas_transfer_outcomes_2023_2025_gap2.csv"),
    )
    parser.add_argument(
        "--j1-debut-evidence",
        type=Path,
        default=Path("data/interim/wikipedia_full_extracts/j1_debut_evidence.csv"),
        help="Output of extract_j1_debuts_from_wikipedia.py; optional (skipped if missing).",
    )
    parser.add_argument(
        "--overseas-wiki-labels",
        type=Path,
        default=Path("data/interim/wikipedia_full_extracts/overseas_stints_labeled.csv"),
        help="Output of label_overseas_stints.py; optional (skipped if missing).",
    )
    parser.add_argument(
        "--overseas-review-queue",
        type=Path,
        default=Path("data/manual/overseas_review_queue.csv"),
        help="Human review of the overseas classifier's needs_review rows; optional.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/player_pathway_outcomes.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    player_summaries = collapse_player_season_features(read_csv(args.season_features))

    pathway_labeled = read_all_tiers(args.pathway_national_team_dir, "pathway_tier_{tier}_labeled.csv")
    pathway_review_queue: list[dict[str, str]] = []
    for queue_path in args.pathway_review_queues or PATHWAY_REVIEW_QUEUE_DEFAULTS:
        pathway_review_queue.extend(read_csv(queue_path))
    pathway_resolved = apply_review_overrides(
        pathway_labeled,
        pathway_review_queue,
        value_column="pathway_category",
        reviewed_value_column="reviewed_pathway_category",
    )

    nt_labeled = read_all_tiers(
        args.pathway_national_team_dir, "national_team_tier_{tier}_labeled.csv"
    )
    nt_review_queue = read_csv(args.national_team_review_queue)
    nt_selection_resolved = apply_review_overrides(
        nt_labeled,
        nt_review_queue,
        value_column="any_national_team_selection",
        reviewed_value_column="reviewed_any_national_team_selection",
    )
    nt_categories_resolved = apply_review_overrides(
        nt_labeled,
        nt_review_queue,
        value_column="national_team_categories",
        reviewed_value_column="reviewed_categories",
    )
    nt_categories_by_id = {
        player_id: value for player_id, (value, _source) in nt_categories_resolved.items()
    }

    moved_overseas_by_id = {
        row["source_player_id"]: (row["moved_overseas"], row["moved_overseas_basis"])
        for row in read_csv(args.overseas_outcomes)
    }

    # Wikipedia-derived evidence (docs/data_collection_revision_proposal_
    # 2026-07-07.md items 1-2). Only in_window_match-validated bases are usable
    # for backfill: rows whose extracted year fell in the SFPR01 window and
    # DISAGREED with observed data are excluded as extractor noise.
    wikipedia_j1_debut_by_id: dict[str, str] = {}
    if args.j1_debut_evidence.exists():
        for row in read_csv(args.j1_debut_evidence):
            if row["j1_debut_year"] and row["validation"] != "in_window_mismatch":
                wikipedia_j1_debut_by_id[row["source_player_id"]] = row["j1_debut_year"]

    overseas_wiki_by_id: dict[str, tuple[str, str]] = {}
    if args.overseas_wiki_labels.exists():
        overseas_wiki_by_id = {
            row["source_player_id"]: (row["moved_overseas_wiki"], row["overseas_confidence"])
            for row in read_csv(args.overseas_wiki_labels)
        }

    # Human review of the classifier's needs_review rows (data/manual/
    # overseas_review_queue.csv) overrides the classifier's own value, marked
    # "human_reviewed" so resolve_moved_overseas_final treats it as trusted.
    if args.overseas_review_queue.exists():
        for row in read_csv(args.overseas_review_queue):
            reviewed_value = "yes" if row["reviewed_moved_overseas"] == "1" else "no"
            overseas_wiki_by_id[row["source_player_id"]] = (reviewed_value, "human_reviewed")

    rows = build_player_pathway_outcomes(
        player_summaries,
        pathway_resolved,
        nt_selection_resolved,
        nt_categories_by_id,
        moved_overseas_by_id,
        wikipedia_j1_debut_by_id,
        overseas_wiki_by_id,
    )
    rows.sort(key=lambda row: row["source_player_id"])
    write_csv(args.output, rows)

    print(f"rows={len(rows)}")
    print("pathway_category:")
    for category, count in sorted(Counter(row["pathway_category"] or "(none)" for row in rows).items()):
        print(f"  {category}: {count}")
    print("any_national_team_selection:")
    for selection, count in sorted(
        Counter(row["any_national_team_selection"] or "(none)" for row in rows).items()
    ):
        print(f"  {selection}: {count}")
    print("reached_j1_ever_source:")
    for value, count in sorted(Counter(row["reached_j1_ever_source"] for row in rows).items()):
        print(f"  {value}: {count}")
    print("moved_overseas_final:")
    for value, count in sorted(
        Counter(row["moved_overseas_final"] or "(none)" for row in rows).items()
    ):
        print(f"  {value}: {count}")
    print("moved_overseas_final_source:")
    for value, count in sorted(Counter(row["moved_overseas_final_source"] for row in rows).items()):
        print(f"  {value}: {count}")
    print(f"wrote={args.output}")


def read_all_tiers(directory: Path, pattern: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for tier in TIERS:
        rows.extend(read_csv(directory / pattern.format(tier=tier)))
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=PLAYER_PATHWAY_OUTCOMES_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
