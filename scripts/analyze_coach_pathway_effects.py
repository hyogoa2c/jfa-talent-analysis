from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from jfa_talent_analysis.pathway_outcome_analysis import parse_birth_year

# "Mature cohort" birth-year window. Players born after this reached fewer of
# their J1-eligible years inside the SFPR01 observation window (2014-2025) and
# are right-censored — which matters here because ex-top-flight coaches
# systematically coach LATER-born players (median birth 1997 vs 1995), so an
# uncontrolled comparison confounds "coach quality" with "player not old enough
# to have reached J1 yet." Restricting to this window is a blunt but transparent
# control; the lower bound keeps it to the modern (J.League-era) game.
MATURE_COHORT_MIN = 1988
MATURE_COHORT_MAX = 1998

# Outcome column encodings (verified against player_pathway_outcomes.csv, and
# the source of an earlier bug): reached_j1_ever / moved_overseas_final are
# "1"/"0"; any_national_team_selection is "yes"/"no"/"unclear"/"".
OUTCOMES = {
    "reached_j1_ever": lambda s: s == "1",
    "moved_overseas_final": lambda s: s == "1",
    "any_national_team_selection": lambda s: s == "yes",
}

# Coach playing-background attributes to test as "treatments".
COACH_ATTRS = ["played_top_flight", "played_overseas", "own_national_team", "played_professionally"]

MIN_CELL = 10  # don't report an outcome rate computed on fewer than this many players


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Phase C3: does a player's PRIMARY development coach's own playing "
            "background (top-flight / overseas / national-team) relate to that "
            "player's outcomes? Marginal comparison, then a within-institution "
            "comparison that holds the institution (and thus much of the "
            "selection/prestige confounding) constant. Exploratory — a positive "
            "association is not a causal coach effect; see the design doc's "
            "cautions."
        )
    )
    parser.add_argument(
        "--primary",
        type=Path,
        default=Path("data/interim/coach_network/player_primary_dev_coach.csv"),
    )
    parser.add_argument(
        "--attributes",
        type=Path,
        default=Path("data/interim/coach_network/coach_attributes.csv"),
    )
    parser.add_argument(
        "--outcomes", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    return parser.parse_args()


def marginal_comparison(df: pd.DataFrame) -> None:
    for attr in COACH_ATTRS:
        col = f"coach_{attr}"
        print(f"  Marginal by primary coach's {attr} (known for "
              f"{df[col].isin(['yes', 'no']).sum()}/{len(df)} players):")
        known = df[df[col].isin(["yes", "no"])]
        for outcome in OUTCOMES:
            cells = []
            for value in ("yes", "no"):
                mask = known[col] == value
                n = int(mask.sum())
                if n >= MIN_CELL:
                    rate = known[outcome][mask].mean()
                    cells.append(f"{value}={rate:.0%}(n={n})")
                else:
                    cells.append(f"{value}=n/a(n={n})")
            print(f"    {outcome:28s} {'  '.join(cells)}")
        print()


def within_institution_top_flight(df: pd.DataFrame) -> None:
    print("  Within-institution reached_j1 by coach top_flight "
          "(institutions with >=10 players under each type):")
    known = df[df["coach_played_top_flight"].isin(["yes", "no"])].copy()
    diffs = []
    for institution, group in known.groupby("primary_dev_institution"):
        yes = group[group["coach_played_top_flight"] == "yes"]
        no = group[group["coach_played_top_flight"] == "no"]
        if len(yes) < MIN_CELL or len(no) < MIN_CELL:
            continue
        yes_rate = yes["reached_j1_ever"].mean()
        no_rate = no["reached_j1_ever"].mean()
        diffs.append(yes_rate - no_rate)
        print(
            f"    {institution:20s} top_flight n={len(yes):3d} J1={yes_rate:4.0%}  |  "
            f"other n={len(no):3d} J1={no_rate:4.0%}  |  diff={yes_rate - no_rate:+.0%}"
        )
    if diffs:
        print(f"    -> {len(diffs)} institutions, mean J1-rate diff "
              f"(top_flight − other): {sum(diffs) / len(diffs):+.1%}")
    else:
        print("    (no institution had >=10 players under both coach types)")
    print()


def run_analysis(df: pd.DataFrame, label: str) -> None:
    print("#" * 72)
    print(f"# {label}  (n={len(df)} players)")
    print("#" * 72)
    marginal_comparison(df)
    within_institution_top_flight(df)


def main() -> None:
    args = parse_args()
    primary = pd.read_csv(args.primary, dtype=str)
    attributes = pd.read_csv(args.attributes, dtype=str)
    outcomes = pd.read_csv(args.outcomes, dtype=str)

    primary = primary[primary["primary_dev_coach"].fillna("") != ""].copy()
    df = primary.merge(
        attributes.add_prefix("coach_"),
        left_on="primary_dev_coach",
        right_on="coach_coach_name",
        how="left",
    ).merge(outcomes, on="source_player_id", how="left")

    for column, decoder in OUTCOMES.items():
        df[column] = decoder(df[column])
    df["birth_year"] = df["birth_date"].map(lambda b: parse_birth_year(b) if isinstance(b, str) else None)

    print(f"players with a primary development coach: {len(df)}")
    print(f"  whose primary coach has an attribute row: {df['coach_coach_name'].notna().sum()}")
    print()

    run_analysis(df, "ALL COHORTS (uncontrolled — biased by right-censoring)")

    mature = df[
        df["birth_year"].notna()
        & (df["birth_year"] >= MATURE_COHORT_MIN)
        & (df["birth_year"] <= MATURE_COHORT_MAX)
    ]
    run_analysis(
        mature,
        f"MATURE COHORT birth {MATURE_COHORT_MIN}-{MATURE_COHORT_MAX} "
        "(censoring-controlled: old enough to have reached J1)",
    )


if __name__ == "__main__":
    main()
