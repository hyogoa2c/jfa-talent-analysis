from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from jfa_talent_analysis.analysis_dataset import apply_review_overrides
from jfa_talent_analysis.pooled_dataset import (
    POOLED_OUTCOMES_COLUMNS,
    collapse_career_seasons,
    merge_label_sources,
)

TIERS = ("a", "b", "c")
PRIORITIES = ("1", "2")

# Labels come from two disjoint collection universes: the 2014-2025 tiers and
# the 1999-2013 backfill. Both must be labeled by the SAME classifier version --
# an era-differential classifier would manufacture exactly the interaction
# Phase 1b is testing for (SAP §6b).
PATHWAY_QUEUES = (
    Path("data/manual/pathway_review_queue.csv"),
    Path("data/manual/phase1_pathway_youth_vs_university_review_queue.csv"),
    Path("data/manual/pre2014_pathway_review_queue.csv"),
    Path("data/manual/pre2014_pathway_review_queue_p2.csv"),
    Path("data/manual/pre2014_pathway_review_queue_supplement.csv"),
)
NATIONAL_TEAM_QUEUES = (
    Path("data/manual/national_team_review_queue.csv"),
    Path("data/manual/pre2014_national_team_review_queue.csv"),
    Path("data/manual/pre2014_national_team_review_queue_p2.csv"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the pooled 1999-2025 analysis dataset (Phase 1b SAP §0/§3/§5): "
            "one row per player with reached_j1_by_age25, era assignment, and the "
            "resolved pathway/national-team exposure labels from both collection "
            "universes. Assembly only -- no pathway-by-outcome estimation, which "
            "would spend H1b-2's confirmatory status before the external review "
            "answers Q6 of docs/review_request_phase1_corrigendum.md."
        )
    )
    parser.add_argument(
        "--career-seasons",
        type=Path,
        default=Path("data/processed/career_league_seasons_1999_2025.csv"),
    )
    parser.add_argument(
        "--pathway-national-team-dir",
        type=Path,
        default=Path("data/interim/pathway_national_team"),
    )
    parser.add_argument("--pre2014-dir", type=Path, default=Path("data/interim/pre2014"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/pooled_player_outcomes_1999_2025.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    summaries = collapse_career_seasons(read_csv(args.career_seasons))

    pathway_queue_rows = concat(PATHWAY_QUEUES)
    nt_queue_rows = concat(NATIONAL_TEAM_QUEUES)

    pathway_resolved, pathway_overlaps = merge_label_sources(
        apply_review_overrides(
            read_tiers(args.pathway_national_team_dir, "pathway_tier_{key}_labeled.csv", TIERS),
            pathway_queue_rows,
            value_column="pathway_category",
            reviewed_value_column="reviewed_pathway_category",
        ),
        apply_review_overrides(
            read_tiers(args.pre2014_dir, "priority{key}_pathway_labeled.csv", PRIORITIES),
            pathway_queue_rows,
            value_column="pathway_category",
            reviewed_value_column="reviewed_pathway_category",
        ),
    )

    nt_labeled_2014 = read_tiers(
        args.pathway_national_team_dir, "national_team_tier_{key}_labeled.csv", TIERS
    )
    nt_labeled_pre2014 = read_tiers(args.pre2014_dir, "priority{key}_nt_labeled.csv", PRIORITIES)
    nt_resolved, nt_overlaps = merge_label_sources(
        *(
            apply_review_overrides(
                labeled,
                nt_queue_rows,
                value_column="any_national_team_selection",
                reviewed_value_column="reviewed_any_national_team_selection",
            )
            for labeled in (nt_labeled_2014, nt_labeled_pre2014)
        )
    )
    nt_categories, _ = merge_label_sources(
        *(
            apply_review_overrides(
                labeled,
                nt_queue_rows,
                value_column="national_team_categories",
                reviewed_value_column="reviewed_categories",
            )
            for labeled in (nt_labeled_2014, nt_labeled_pre2014)
        )
    )

    rows = []
    for player_id, summary in summaries.items():
        pathway, pathway_source = pathway_resolved.get(player_id, ("", "not_collected"))
        selection, nt_source = nt_resolved.get(player_id, ("", "not_collected"))
        categories, _ = nt_categories.get(player_id, ("", ""))
        rows.append(
            {
                **summary,
                "pathway_category": pathway,
                "pathway_category_source": pathway_source,
                "any_national_team_selection": selection,
                "national_team_categories": categories,
                "national_team_selection_source": nt_source,
            }
        )
    rows.sort(key=lambda row: int(row["source_player_id"]))
    write_csv(args.output, rows)

    report(rows, pathway_overlaps, nt_overlaps)
    print(f"wrote={args.output}")


def report(rows: list[dict[str, str]], pathway_overlaps: list[str], nt_overlaps: list[str]) -> None:
    """Outcome-free summary only -- see the module docstring on the firewall.

    Reporting the outcome rate by era is fine (SAP §9 declines to interpret the
    era main effect); reporting it by pathway is not.
    """
    print(f"players={len(rows)}")
    if pathway_overlaps:
        print(f"  WARNING pathway label collisions across universes: {len(pathway_overlaps)}")
    if nt_overlaps:
        print(f"  WARNING national-team label collisions: {len(nt_overlaps)}")

    eligible = [row for row in rows if row["eligible_confirmatory"] == "1"]
    print(f"eligible for the era1-vs-era2 comparison: {len(eligible)}")
    for era in ("era1", "era2"):
        in_era = [row for row in eligible if row["era"] == era]
        labeled = [row for row in in_era if row["pathway_category"]]
        backfill = sum(1 for row in in_era if row["observed_2014_plus"] == "0")
        print(f"\n{era}: n={len(in_era)} (backfill-only, absent from the Phase 1 universe: {backfill})")
        print(f"  pathway label coverage: {len(labeled)}/{len(in_era)} ({share(len(labeled), len(in_era))})")
        for value, count in Counter(row["pathway_category"] or "(none)" for row in in_era).most_common():
            print(f"    {value}: {count}")
        for value, count in Counter(row["pathway_category_source"] for row in in_era).most_common():
            print(f"    source {value}: {count}")


def share(numerator: int, denominator: int) -> str:
    return f"{numerator / denominator:.1%}" if denominator else "n/a"


def concat(paths: tuple[Path, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        if path.exists():
            rows.extend(read_csv(path))
    return rows


def read_tiers(directory: Path, pattern: str, keys: tuple[str, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for key in keys:
        rows.extend(read_csv(directory / pattern.format(key=key)))
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(10_000_000)
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=POOLED_OUTCOMES_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
