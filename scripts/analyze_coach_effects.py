from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from jfa_talent_analysis.pathway_outcome_analysis import wilson_confidence_interval

# Below this many distinct players, a coach's outcome rate is too noisy to
# report on its own (a single J1 debutant among 3 players swings the rate by
# 33pp) — matches this project's established small-n caution
# (pathway_outcome_analysis.wilson_confidence_interval exists for exactly
# this reason). Rows below the threshold are still counted, just not listed
# individually in the per-coach breakdown.
MIN_PLAYERS_FOR_COACH_ROW = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "First descriptive pass over the player x coach exposure join: "
            "per-coach outcome rates, cross-institution coach movement (the "
            "network edges the design doc's identification strategy relies "
            "on), and within-institution coach comparison. Exploratory only — "
            "see docs/coach_network_design_2026-07-10.md's analytical "
            "cautions on selection-effect confounding before treating any "
            "rate difference here as a causal coach effect."
        )
    )
    parser.add_argument(
        "--exposures",
        type=Path,
        default=Path("data/interim/coach_network/player_coach_exposures.csv"),
    )
    parser.add_argument(
        "--outcomes", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/interim/coach_network")
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    exposures = pd.read_csv(args.exposures, dtype=str)
    outcomes = pd.read_csv(args.outcomes, dtype=str)

    # One row per (player, coach, institution) — a player can appear more than
    # once per coach if the source data has multiple stint rows at the same
    # institution (e.g. a youth-team stint plus a separately-listed pro-
    # registration stint at the same club); collapse to one exposure per
    # (player, coach, normalized_institution) before counting players.
    exposures = exposures.drop_duplicates(
        subset=["source_player_id", "coach_name", "normalized_institution"]
    )

    # Outcome column encodings differ (a historical artifact of how each was
    # built): reached_j1_ever and moved_overseas_final are "1"/"0", while
    # any_national_team_selection is "yes"/"no"/"unclear"/"". Verified against
    # data/processed/player_pathway_outcomes.csv before trusting these.
    merged = exposures.merge(outcomes, on="source_player_id", how="left")
    merged["reached_j1_ever"] = merged["reached_j1_ever"] == "1"
    merged["moved_overseas_final"] = merged["moved_overseas_final"] == "1"
    merged["any_national_team_selection"] = merged["any_national_team_selection"] == "yes"

    print(f"exposure rows (deduplicated)={len(merged)}")
    print(f"distinct players={merged['source_player_id'].nunique()}")
    print(f"distinct coaches={merged['coach_name'].nunique()}")
    print()

    print("=" * 70)
    print(f"Per-coach outcome rates (players >= {MIN_PLAYERS_FOR_COACH_ROW})")
    print("=" * 70)
    coach_stats = (
        merged.groupby("coach_name")
        .agg(
            n_players=("source_player_id", "nunique"),
            n_institutions=("normalized_institution", "nunique"),
            reached_j1_rate=("reached_j1_ever", "mean"),
            overseas_rate=("moved_overseas_final", "mean"),
            national_team_rate=("any_national_team_selection", "mean"),
        )
        .reset_index()
    )
    coach_stats = coach_stats[coach_stats["n_players"] >= MIN_PLAYERS_FOR_COACH_ROW]
    coach_stats = coach_stats.sort_values("reached_j1_rate", ascending=False)
    for _, row in coach_stats.iterrows():
        lo, hi = wilson_confidence_interval(
            int(round(row["reached_j1_rate"] * row["n_players"])), int(row["n_players"])
        )
        print(
            f"  {row['coach_name']:12s} n={int(row['n_players']):3d}  "
            f"institutions={int(row['n_institutions'])}  "
            f"J1={row['reached_j1_rate']:.0%} [{lo:.0%},{hi:.0%}]  "
            f"overseas={row['overseas_rate']:.0%}  "
            f"national_team={row['national_team_rate']:.0%}"
        )
    coach_stats.to_csv(args.output_dir / "coach_effect_summary.csv", index=False)
    print(f"\nwrote={args.output_dir / 'coach_effect_summary.csv'} ({len(coach_stats)} coaches)")

    print()
    print("=" * 70)
    print("Cross-institution coaches (network edges — moved between 2+ institutions)")
    print("=" * 70)
    movers = (
        merged.groupby("coach_name")["normalized_institution"]
        .agg(lambda s: sorted(set(s)))
        .reset_index()
    )
    movers = movers[movers["normalized_institution"].apply(len) >= 2]
    for _, row in movers.iterrows():
        n_players = merged[merged["coach_name"] == row["coach_name"]][
            "source_player_id"
        ].nunique()
        print(f"  {row['coach_name']:12s} n={n_players:3d}  {' <-> '.join(row['normalized_institution'])}")
    print(f"\n{len(movers)} coaches appear at 2+ researched institutions")

    print()
    print("=" * 70)
    print(f"Within-institution coach comparison (each coach n >= {MIN_PLAYERS_FOR_COACH_ROW})")
    print("=" * 70)
    inst_coach = (
        merged.groupby(["normalized_institution", "coach_name"])
        .agg(n_players=("source_player_id", "nunique"), reached_j1_rate=("reached_j1_ever", "mean"))
        .reset_index()
    )
    inst_coach = inst_coach[inst_coach["n_players"] >= MIN_PLAYERS_FOR_COACH_ROW]
    multi_coach_institutions = inst_coach.groupby("normalized_institution").filter(
        lambda g: len(g) >= 2
    )
    for institution, group in multi_coach_institutions.groupby("normalized_institution"):
        group = group.sort_values("reached_j1_rate", ascending=False)
        spread = group["reached_j1_rate"].max() - group["reached_j1_rate"].min()
        print(f"  {institution} (spread={spread:.0%}):")
        for _, row in group.iterrows():
            print(f"    {row['coach_name']:12s} n={int(row['n_players']):3d}  J1={row['reached_j1_rate']:.0%}")


if __name__ == "__main__":
    main()
