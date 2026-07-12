from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from jfa_talent_analysis.pathway_outcome_analysis import wilson_confidence_interval

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


def rate_line(label: str, mask: pd.Series, outcome: pd.Series) -> str:
    n = int(mask.sum())
    if n < MIN_CELL:
        return f"    {label:22s} n={n:4d}  (too few to report)"
    successes = int(outcome[mask].sum())
    lo, hi = wilson_confidence_interval(successes, n)
    return f"    {label:22s} n={n:4d}  rate={successes / n:5.0%}  [{lo:.0%},{hi:.0%}]"


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

    print(f"players with a primary development coach: {len(df)}")
    print(f"  whose primary coach has an attribute row: {df['coach_coach_name'].notna().sum()}")
    print()

    # --- Marginal comparison: outcome rate by coach attribute (yes vs no) ---
    for attr in COACH_ATTRS:
        col = f"coach_{attr}"
        print("=" * 72)
        print(f"Marginal: player outcomes by primary coach's {attr}")
        print("=" * 72)
        known = df[df[col].isin(["yes", "no"])]
        coverage = len(known)
        print(f"  (coach attribute known for {coverage} of {len(df)} players)")
        for outcome in OUTCOMES:
            print(f"  outcome = {outcome}:")
            for value in ("yes", "no"):
                mask = known[col] == value
                print(rate_line(f"{attr}={value}", mask, known[outcome]))
        print()

    # --- Within-institution comparison (holds institution constant) ---
    print("=" * 72)
    print("Within-institution: reached_j1 rate by primary coach top_flight,")
    print("only institutions that have BOTH top-flight and non-top-flight coaches")
    print("=" * 72)
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
            f"  {institution:20s} top_flight-coached n={len(yes):3d} J1={yes_rate:4.0%}  |  "
            f"other n={len(no):3d} J1={no_rate:4.0%}  |  diff={yes_rate - no_rate:+.0%}"
        )
    if diffs:
        avg = sum(diffs) / len(diffs)
        print(f"\n  institutions compared: {len(diffs)}")
        print(f"  mean within-institution J1-rate difference (top_flight − other): {avg:+.1%}")
        print("  (positive => players under an ex-top-flight coach reached J1 more often,")
        print("   holding the institution constant; still not causal — era/cohort uncontrolled)")
    else:
        print("  (no institution had >=10 players under both coach types — expected until")
        print("   J-youth academies are added; university institutions dominate so far)")


if __name__ == "__main__":
    main()
