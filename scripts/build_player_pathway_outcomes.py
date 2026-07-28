from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.academy_reclassification import load_reviewed, reclassify
from jfa_talent_analysis.analysis_dataset import (
    PLAYER_PATHWAY_OUTCOMES_COLUMNS,
    apply_review_overrides,
    build_player_pathway_outcomes,
    collapse_player_season_features,
    usable_wikipedia_j1_debuts,
)
from jfa_talent_analysis.club_history_pathway import derive_pathway_labels
from jfa_talent_analysis.j_club_registry import build_clubs
from jfa_talent_analysis.pooled_dataset import resolve_composite_pathway_labels
from jfa_talent_analysis.review_queues import (
    PATHWAY_REVIEW_QUEUES,
    club_list_aware_ids,
    read_queue_rows,
)

TIERS = ("a", "b", "c")

# SAP §1b-2/§1b-4 apply retroactively to Phase 1, so Phase 1 resolves the exposure
# through the same composite rule and the same queue list as Phase 1b. Reading a
# different set of queues here is what left Phase 1 carrying academy labels that
# Phase 1b had already corrected.
PATHWAY_REVIEW_QUEUE_DEFAULTS = PATHWAY_REVIEW_QUEUES


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
        "--stints",
        type=Path,
        default=Path("data/interim/coach_network/player_institution_stints.csv"),
        help="Parsed 所属クラブ career lists, the second exposure measurement (SAP §1b-3).",
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
        "--observation-end-season",
        type=int,
        default=2025,
        help=(
            "Last season the study can observe. Wikipedia J1 debuts after this are "
            "dropped: they are outside the window, and leaving them in would make the "
            "dataset change every time Wikipedia gains a newer debut."
        ),
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
    if args.pathway_review_queues:
        pathway_review_queue = [row for p in args.pathway_review_queues for row in read_csv(p)]
    else:
        pathway_review_queue = read_queue_rows()

    birth_years = {
        player_id: int(summary["birth_date"][:4])
        for player_id, summary in player_summaries.items()
        if (summary.get("birth_date") or "")[:4].isdigit()
    }
    club_labels = derive_pathway_labels(read_csv(args.stints), birth_years)
    composite = resolve_composite_pathway_labels(
        pathway_labeled, club_labels, pathway_review_queue, club_list_aware_ids()
    )
    clubs = build_clubs()
    reviewed = load_reviewed()
    stint_rows: dict[str, list[dict[str, str]]] = {}
    for row in read_csv(args.stints):
        stint_rows.setdefault(row["source_player_id"], []).append(row)
    pathway_resolved = {}
    for player_id, row in composite.items():
        category, _ = reclassify(
            player_id,
            row["pathway_category"],
            stint_rows.get(player_id, []),
            birth_years.get(player_id),
            clubs,
            reviewed,
        )
        pathway_resolved[player_id] = (category, row["pathway_category_source"])

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
    #
    # A debut after the observation window is not an outcome this study can
    # observe, and Wikipedia keeps getting updated: without the upper bound,
    # re-running this pipeline later silently pulls in newer debuts and changes
    # the canonical numbers. Bound it so the dataset is reproducible.
    wikipedia_j1_debut_by_id: dict[str, str] = {}
    out_of_window = 0
    if args.j1_debut_evidence.exists():
        wikipedia_j1_debut_by_id, out_of_window = usable_wikipedia_j1_debuts(
            read_csv(args.j1_debut_evidence), args.observation_end_season
        )
    if out_of_window:
        print(
            f"excluded {out_of_window} Wikipedia J1 debut(s) after "
            f"{args.observation_end_season} (outside the observation window)"
        )

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
