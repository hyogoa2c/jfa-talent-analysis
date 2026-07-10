from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import PartialDependenceDisplay, permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from jfa_talent_analysis.pathway_outcome_analysis import (
    earliest_youth_selection_age,
    has_a_team_selection,
    has_youth_national_team_selection,
    parse_birth_year,
    youth_category_count,
)

MAIN_PATHWAYS = ["j_club_academy", "high_school", "university"]

# Pre-career features only. Career-performance columns (career_minutes,
# seasons_observed, career_j1_minutes...) are deliberately excluded: they are
# consequences of the outcomes being predicted, and models fed them would
# "discover" only that playing a lot correlates with succeeding a lot.
FEATURE_COLUMNS = [
    "birth_year",
    "youth_selected",
    "youth_cat_count",
    "earliest_youth_age",
    "pathway_high_school",
    "pathway_university",
]

RANDOM_STATE = 20260710


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exploratory Random Forest modeling of the three outcomes "
            "(docs/data_collection_plan.md's 'Later Modeling'), using permutation "
            "importance and partial dependence in place of SHAP (the shap "
            "package's numba dependency does not support this project's Python "
            "3.13). The goal is discovering nonlinearity/interactions the "
            "logistic models might miss — a similar AUC between RF and logistic "
            "is itself a finding (no hidden structure)."
        )
    )
    parser.add_argument(
        "--input", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/generated"))
    return parser.parse_args()


def load_model_frame(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df["birth_year"] = df["birth_date"].apply(parse_birth_year)
    df["national_team_categories"] = df["national_team_categories"].fillna("")
    df["youth_selected"] = (
        df["national_team_categories"].apply(has_youth_national_team_selection).astype(int)
    )
    df["youth_cat_count"] = df["national_team_categories"].apply(youth_category_count)
    df["earliest_youth_age"] = df["national_team_categories"].apply(earliest_youth_selection_age)
    df["a_team_selected"] = df["national_team_categories"].apply(has_a_team_selection).astype(int)
    df["reached_j1_ever"] = pd.to_numeric(df["reached_j1_ever"], errors="coerce")
    df["overseas_yes"] = (df["moved_overseas_final"] == "1").astype(int)
    df["overseas_labeled"] = df["moved_overseas_final"].isin(["0", "1"])
    df["nt_labeled"] = df["any_national_team_selection"].isin(["yes", "no"])

    df = df[df["pathway_category"].isin(MAIN_PATHWAYS) & df["birth_year"].notna()].copy()
    df["pathway_high_school"] = (df["pathway_category"] == "high_school").astype(int)
    df["pathway_university"] = (df["pathway_category"] == "university").astype(int)
    # sklearn's partial dependence rejects integer dtypes (implicit-rounding
    # hazard); floats are equivalent for tree splits.
    for column in FEATURE_COLUMNS:
        df[column] = df[column].astype(float)
    return df


def outcome_frames(df: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, pd.Series]]:
    """The three modeling targets, each restricted to rows where that outcome
    is actually labeled (never treating missing evidence as a negative)."""
    j1 = df[df["reached_j1_ever"].notna()]
    # A-team outcome needs the national-team label resolved; youth features are
    # legitimate predictors because the A team is temporally downstream of
    # youth call-ups (see has_a_team_selection's docstring for the leakage
    # reasoning that rules out any_national_team_selection here).
    a_team = df[df["nt_labeled"]]
    overseas = df[df["overseas_labeled"]]
    return {
        "reached_j1": (j1[FEATURE_COLUMNS], j1["reached_j1_ever"].astype(int)),
        "a_team_selected": (a_team[FEATURE_COLUMNS], a_team["a_team_selected"]),
        "moved_overseas": (overseas[FEATURE_COLUMNS], overseas["overseas_yes"]),
    }


def evaluate_models(features: pd.DataFrame, outcome: pd.Series) -> dict[str, object]:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    forest = RandomForestClassifier(
        n_estimators=500,
        min_samples_leaf=20,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    logistic = LogisticRegression(max_iter=2000)

    forest_auc = cross_val_score(forest, features, outcome, cv=cv, scoring="roc_auc")
    logistic_auc = cross_val_score(logistic, features, outcome, cv=cv, scoring="roc_auc")

    train_x, test_x, train_y, test_y = train_test_split(
        features, outcome, test_size=0.3, stratify=outcome, random_state=RANDOM_STATE
    )
    forest.fit(train_x, train_y)
    importance = permutation_importance(
        forest, test_x, test_y, scoring="roc_auc", n_repeats=20, random_state=RANDOM_STATE
    )

    return {
        "n": len(outcome),
        "positive_rate": float(outcome.mean()),
        "forest_auc_mean": float(forest_auc.mean()),
        "forest_auc_std": float(forest_auc.std()),
        "logistic_auc_mean": float(logistic_auc.mean()),
        "logistic_auc_std": float(logistic_auc.std()),
        "importance_mean": importance.importances_mean,
        "importance_std": importance.importances_std,
        "fitted_forest": forest,
        "train_x": train_x,
    }


def plot_importances(results: dict[str, dict], output_dir: Path) -> None:
    fig, axes = plt.subplots(1, len(results), figsize=(5.5 * len(results), 4.5), sharey=True)
    for ax, (name, result) in zip(axes, results.items(), strict=True):
        order = np.argsort(result["importance_mean"])
        ax.barh(
            [FEATURE_COLUMNS[i] for i in order],
            result["importance_mean"][order],
            xerr=result["importance_std"][order],
        )
        ax.set_title(name)
        ax.set_xlabel("permutation importance (AUC drop)")
    fig.tight_layout()
    fig.savefig(output_dir / "rf_permutation_importance.png", dpi=120)
    plt.close(fig)


def plot_partial_dependence(results: dict[str, dict], output_dir: Path) -> None:
    pd_features = ["birth_year", "earliest_youth_age"]
    fig, axes = plt.subplots(
        len(results), len(pd_features), figsize=(5.5 * len(pd_features), 3.8 * len(results))
    )
    for row, (name, result) in enumerate(results.items()):
        display = PartialDependenceDisplay.from_estimator(
            result["fitted_forest"],
            result["train_x"],
            pd_features,
            ax=axes[row],
            kind="average",
        )
        for ax in np.atleast_1d(display.axes_).ravel():
            if ax is not None:
                ax.set_title(name, fontsize=9)
    fig.tight_layout()
    fig.savefig(output_dir / "rf_partial_dependence.png", dpi=120)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    df = load_model_frame(args.input)

    results: dict[str, dict] = {}
    for name, (features, outcome) in outcome_frames(df).items():
        results[name] = evaluate_models(features, outcome)
        print(
            f"{name}: n={results[name]['n']} "
            f"RF AUC={results[name]['forest_auc_mean']:.3f}±{results[name]['forest_auc_std']:.3f} "
            f"logit AUC={results[name]['logistic_auc_mean']:.3f}±{results[name]['logistic_auc_std']:.3f}"
        )

    plot_importances(results, args.output_dir)
    plot_partial_dependence(results, args.output_dir)

    lines = [
        "# Exploratory Modeling Report (Random Forest vs Logistic)",
        "",
        "Features are pre-career only (pathway, birth_year, youth national-team "
        "signals); career-performance columns are deliberately excluded as "
        "post-outcome. The national-team outcome is **A-team selection** (not "
        "any-selection) to avoid leaking the youth-selection features into the "
        "target. Permutation importance and partial dependence stand in for "
        "SHAP (whose numba dependency lacks Python 3.13 support).",
        "",
        "| outcome | n | positive rate | RF AUC (5-fold CV) | Logistic AUC (5-fold CV) |",
        "|---|---|---|---|---|",
    ]
    for name, result in results.items():
        lines.append(
            f"| {name} | {result['n']} | {result['positive_rate'] * 100:.1f}% "
            f"| {result['forest_auc_mean']:.3f} ± {result['forest_auc_std']:.3f} "
            f"| {result['logistic_auc_mean']:.3f} ± {result['logistic_auc_std']:.3f} |"
        )
    lines += [
        "",
        "## Permutation importance (held-out 30% test set, AUC drop when shuffled)",
        "",
        "Chart: `rf_permutation_importance.png`",
        "",
    ]
    for name, result in results.items():
        lines.append(f"### {name}")
        lines.append("")
        lines.append("| feature | importance (mean ± std) |")
        lines.append("|---|---|")
        order = np.argsort(result["importance_mean"])[::-1]
        for i in order:
            lines.append(
                f"| {FEATURE_COLUMNS[i]} | {result['importance_mean'][i]:.4f} "
                f"± {result['importance_std'][i]:.4f} |"
            )
        lines.append("")
    lines += [
        "## Partial dependence (birth_year, earliest_youth_age)",
        "",
        "Chart: `rf_partial_dependence.png`",
    ]

    report_path = args.output_dir / "exploratory_modeling_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote={report_path}")


if __name__ == "__main__":
    main()
