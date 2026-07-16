from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from jfa_talent_analysis.pathway_outcome_analysis import (
    birth_cohort,
    parse_birth_year,
    wilson_confidence_interval,
)

MATURE_COHORT_MIN = 1988
MATURE_COHORT_MAX = 1998


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Lineage x outcomes: does a primary development coach having "
            "himself been developed under a researched coach (an in-lineage "
            "coach) relate to his players' outcomes? Also pools each mentor's "
            "'grand-students' (players of the coaches he developed) to show "
            "per-lineage outcome profiles. Descriptive; mentor edges exist "
            "only where the tenure table covers the coach's own playing era, "
            "so in-lineage is partly a 'famous long-reign mentor' proxy."
        )
    )
    parser.add_argument(
        "--edges",
        type=Path,
        default=Path("data/interim/coach_network/coach_lineage_edges.csv"),
    )
    parser.add_argument(
        "--primary",
        type=Path,
        default=Path("data/interim/coach_network/player_primary_dev_coach.csv"),
    )
    parser.add_argument(
        "--outcomes", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    return parser.parse_args()


def rate(sub: pd.DataFrame, column: str) -> str:
    n = len(sub)
    if n == 0:
        return "n=0"
    successes = int(sub[column].sum())
    lo, hi = wilson_confidence_interval(successes, n)
    return f"{successes / n:4.0%} [{lo:.0%},{hi:.0%}] (n={n})"


def main() -> None:
    args = parse_args()
    edges = pd.read_csv(args.edges, dtype=str)
    primary = pd.read_csv(args.primary, dtype=str)
    outcomes = pd.read_csv(args.outcomes, dtype=str)

    mentored = edges[edges["edge_type"] == "mentored_by"]
    mentors_of: dict[str, list[str]] = (
        mentored.groupby("coach_name")["related_coach"].agg(list).to_dict()
    )

    df = primary[primary["primary_dev_coach"].fillna("") != ""].merge(
        outcomes, on="source_player_id", how="left"
    )
    df["reached_j1"] = (df["reached_j1_ever"] == "1").astype(int)
    df["birth_year"] = df["birth_date"].map(
        lambda b: parse_birth_year(b) if isinstance(b, str) else None
    )
    df["cohort"] = df["birth_year"].map(birth_cohort)
    df["in_lineage"] = df["primary_dev_coach"].isin(mentors_of)

    in_lineage_coaches = sorted(set(df["primary_dev_coach"]) & set(mentors_of))
    print(
        f"in-lineage primary coaches (their own developer is in our tenure table): "
        f"{len(in_lineage_coaches)} of {df['primary_dev_coach'].nunique()}"
    )
    for coach in in_lineage_coaches:
        print(f"  {coach} <- {', '.join(sorted(set(mentors_of[coach])))}")

    print("\nreached_j1 by whether the primary coach is in-lineage:")
    for label, sub in (
        ("all cohorts", df),
        (
            f"mature cohort {MATURE_COHORT_MIN}-{MATURE_COHORT_MAX}",
            df[
                df["birth_year"].notna()
                & df["birth_year"].between(MATURE_COHORT_MIN, MATURE_COHORT_MAX)
            ],
        ),
    ):
        print(f"  [{label}]")
        print(f"    in-lineage coach:  {rate(sub[sub['in_lineage']], 'reached_j1')}")
        print(f"    other coach:       {rate(sub[~sub['in_lineage']], 'reached_j1')}")

    print("\nPer-mentor 'grand-student' outcomes (players of the coaches he developed):")
    student_to_mentors = {
        coach: sorted(set(mentor_list)) for coach, mentor_list in mentors_of.items()
    }
    rows = []
    for mentor in sorted({m for ms in student_to_mentors.values() for m in ms}):
        students = [c for c, ms in student_to_mentors.items() if mentor in ms]
        grand = df[df["primary_dev_coach"].isin(students)]
        if len(grand) == 0:
            continue
        rows.append((mentor, grand))
    rows.sort(key=lambda r: -len(r[1]))
    for mentor, grand in rows:
        print(f"  {mentor} — student-coaches with attributed players: "
              f"{', '.join(sorted(set(grand['primary_dev_coach'])))}")
        print(f"    grand-students reached_j1: {rate(grand, 'reached_j1')}")


if __name__ == "__main__":
    main()
