from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from jfa_talent_analysis.pathway_outcome_analysis import (
    birth_cohort,
    parse_birth_year,
    wilson_confidence_interval,
)

# A coach-at-institution unit needs enough players for its rate to carry signal;
# below this the unit is dropped (not pooled into a pseudo-coach, which would
# manufacture a fake "other" coach with a mixed-era roster).
MIN_PLAYERS_PER_UNIT = 10

OUTCOME_DECODERS = {
    "reached_j1_ever": lambda s: (s == "1").astype(int),
    "any_national_team_selection": lambda s: (s == "yes").astype(int),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Do development coaches differ in player outcomes beyond what the "
            "institution and the player's birth cohort explain? Tests coach "
            "fixed effects two ways: a likelihood-ratio test (logit with "
            "coach-at-institution dummies, nested against institution+cohort) "
            "and a permutation test that shuffles coach labels within "
            "institution x cohort cells — the cleaner answer when some coach "
            "cells are small or separated. If coach effects are real, also "
            "prints an adjusted value-added ranking (observed minus the "
            "institution+cohort model's expectation)."
        )
    )
    parser.add_argument(
        "--primary",
        type=Path,
        default=Path("data/interim/coach_network/player_primary_dev_coach.csv"),
    )
    parser.add_argument(
        "--outcomes", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    parser.add_argument("--permutations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260716)
    return parser.parse_args()


def load_sample(primary_path: Path, outcomes_path: Path) -> pd.DataFrame:
    primary = pd.read_csv(primary_path, dtype=str)
    outcomes = pd.read_csv(outcomes_path, dtype=str)
    df = primary[primary["primary_dev_coach"].fillna("") != ""].merge(
        outcomes, on="source_player_id", how="left"
    )
    df["birth_year"] = df["birth_date"].map(
        lambda b: parse_birth_year(b) if isinstance(b, str) else None
    )
    df = df[df["birth_year"].notna()].copy()
    df["cohort"] = df["birth_year"].map(birth_cohort)
    # Coach-at-institution unit: a mover (same coach, two institutions) becomes
    # two units, keeping coach effects strictly nested inside institution
    # effects so the LR test's degrees of freedom are well-defined.
    df["coach_unit"] = df["primary_dev_institution"] + "×" + df["primary_dev_coach"]

    unit_sizes = df.groupby("coach_unit")["source_player_id"].nunique()
    df = df[df["coach_unit"].map(unit_sizes) >= MIN_PLAYERS_PER_UNIT]
    # Identification needs within-institution contrast: institutions with a
    # single surviving coach unit contribute nothing to the coach-vs-institution
    # comparison and are dropped.
    units_per_inst = df.groupby("primary_dev_institution")["coach_unit"].nunique()
    df = df[df["primary_dev_institution"].map(units_per_inst) >= 2]
    return df


def fit_deviance(y: np.ndarray, dummies: pd.DataFrame) -> float:
    """Deviance of a logit fit (statsmodels GLM keeps going under the perfect-
    separation cells a permuted draw can produce, unlike Logit's MLE)."""
    X = sm.add_constant(dummies, has_constant="add")
    model = sm.GLM(y, X, family=sm.families.Binomial())
    return model.fit(maxiter=200, tol=1e-8).deviance


def coach_lr_statistic(df: pd.DataFrame, outcome: str) -> tuple[float, int]:
    y = df[outcome].to_numpy()
    base = pd.get_dummies(
        df[["primary_dev_institution", "cohort"]], drop_first=True, dtype=float
    )
    full = pd.get_dummies(
        df[["coach_unit", "cohort"]], drop_first=True, dtype=float
    )
    lr = fit_deviance(y, base) - fit_deviance(y, full)
    extra_df = df["coach_unit"].nunique() - df["primary_dev_institution"].nunique()
    return lr, extra_df


def permutation_test(
    df: pd.DataFrame, outcome: str, observed_lr: float, n_permutations: int, seed: int
) -> float:
    """Null: within an institution (and cohort cell), which coach a player got
    is exchangeable. Shuffling coach_unit labels inside institution x cohort
    cells preserves both margins, so anything that survives is coach-specific."""
    rng = np.random.default_rng(seed)
    work = df.copy()
    exceed = 0
    for _ in range(n_permutations):
        work["coach_unit"] = df.groupby(
            ["primary_dev_institution", "cohort"], group_keys=False
        )["coach_unit"].transform(rng.permutation)
        lr, _ = coach_lr_statistic(work, outcome)
        if lr >= observed_lr:
            exceed += 1
    return (exceed + 1) / (n_permutations + 1)


def value_added_ranking(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """Observed unit rate minus the institution+cohort model's expectation for
    that unit's actual roster — the transparent 'did this coach's players beat
    the rate their school and era predicted' number."""
    y = df[outcome].to_numpy()
    base = pd.get_dummies(
        df[["primary_dev_institution", "cohort"]], drop_first=True, dtype=float
    )
    X = sm.add_constant(base, has_constant="add")
    expected = sm.GLM(y, X, family=sm.families.Binomial()).fit(maxiter=200).mu
    work = df.assign(expected=expected)
    rows = []
    for unit, group in work.groupby("coach_unit"):
        n = len(group)
        observed = group[outcome].mean()
        lo, hi = wilson_confidence_interval(int(group[outcome].sum()), n)
        rows.append(
            {
                "coach_unit": unit,
                "n": n,
                "observed": observed,
                "expected": group["expected"].mean(),
                "value_added": observed - group["expected"].mean(),
                "obs_ci": f"[{lo:.0%},{hi:.0%}]",
            }
        )
    return pd.DataFrame(rows).sort_values("value_added", ascending=False)


def main() -> None:
    args = parse_args()
    df = load_sample(args.primary, args.outcomes)
    print(
        f"analysis sample: {len(df)} players, "
        f"{df['coach_unit'].nunique()} coach-units across "
        f"{df['primary_dev_institution'].nunique()} institutions "
        f"(units with >={MIN_PLAYERS_PER_UNIT} players, institutions with >=2 units)"
    )

    for outcome, decode in OUTCOME_DECODERS.items():
        work = df.copy()
        work[outcome] = decode(work[outcome].fillna(""))
        print("\n" + "=" * 72)
        print(f"OUTCOME: {outcome}")
        print("=" * 72)

        observed_lr, extra_df = coach_lr_statistic(work, outcome)
        p_chi2 = stats.chi2.sf(observed_lr, extra_df)
        print(f"  LR statistic (coach FE vs institution+cohort): {observed_lr:.1f} "
              f"on {extra_df} df -> chi2 p={p_chi2:.4f}")

        p_perm = permutation_test(work, outcome, observed_lr, args.permutations, args.seed)
        print(f"  permutation p (coach labels shuffled within institution x cohort, "
              f"{args.permutations} draws): p={p_perm:.4f}")

        ranking = value_added_ranking(work, outcome)
        print("\n  Value-added ranking (observed − institution+cohort expectation):")
        print("  --- top 10 ---")
        for _, r in ranking.head(10).iterrows():
            print(f"    {r['coach_unit']:40s} n={r['n']:3d} obs={r['observed']:4.0%} "
                  f"{r['obs_ci']:12s} exp={r['expected']:4.0%} VA={r['value_added']:+.0%}")
        print("  --- bottom 5 ---")
        for _, r in ranking.tail(5).iterrows():
            print(f"    {r['coach_unit']:40s} n={r['n']:3d} obs={r['observed']:4.0%} "
                  f"{r['obs_ci']:12s} exp={r['expected']:4.0%} VA={r['value_added']:+.0%}")


if __name__ == "__main__":
    main()
