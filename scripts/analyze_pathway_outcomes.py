from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.formula.api as smf
from lifelines import CoxPHFitter, KaplanMeierFitter

from jfa_talent_analysis.pathway_outcome_analysis import (
    birth_cohort,
    parse_birth_year,
    wilson_confidence_interval,
)

MAIN_PATHWAYS = ["j_club_academy", "high_school", "university"]
PATHWAY_ORDER = ["j_club_academy", "high_school", "university", "jfa_academy", "grassroots_club", "unknown"]
# Centers birth_year for the logistic regressions so the intercept means "an
# average-birth-year j_club_academy player" instead of a nonsensical
# extrapolation to birth_year=0 (which blows up exp(intercept) into a
# meaningless, enormous odds ratio).
BIRTH_YEAR_REFERENCE = 1995


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initial descriptive/regression/survival analysis of player_pathway_outcomes.csv."
    )
    parser.add_argument(
        "--input", type=Path, default=Path("data/processed/player_pathway_outcomes.csv")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/generated"))
    parser.add_argument(
        "--min-birth-year",
        type=int,
        default=None,
        help=(
            "Restrict to players born in this year or later. Used as a sensitivity "
            "check for the pre-2014 J1-debut truncation problem "
            "(docs/data_collection_revision_proposal_2026-07-07.md item 1): older "
            "cohorts were mostly already mid-career when the 2014 SFPR01 window "
            "opens, so their reached_j1/first_j1_age are unreliable."
        ),
    )
    return parser.parse_args()


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    numeric_columns = [
        "seasons_observed",
        "career_minutes",
        "career_j1_minutes",
        "reached_j1",
        "first_j1_age",
        "first_observed_season",
        "last_observed_season",
        "first_j1_season",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["birth_year"] = df["birth_date"].apply(parse_birth_year)
    df["birth_cohort"] = df["birth_year"].apply(birth_cohort)
    df["pathway_category_filled"] = df["pathway_category"].fillna("").replace("", "no_data")
    df["nt_yes"] = (df["any_national_team_selection"] == "yes").astype(int)
    df["nt_labeled"] = df["any_national_team_selection"].isin(["yes", "no"])
    return df


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    df = load_data(args.input)

    sections: list[str] = []
    if args.min_birth_year is not None:
        df = df[df["birth_year"].notna() & (df["birth_year"] >= args.min_birth_year)]
        sections.append(
            f"# Sensitivity run: restricted to birth_year >= {args.min_birth_year} "
            f"(n={len(df)})"
        )
    sections.append(descriptive_section(df, args.output_dir))
    sections.append(logistic_regression_section(df))
    sections.append(survival_section(df, args.output_dir))
    sections.append(overseas_caveat_section(df))

    report_path = args.output_dir / "initial_analysis_report.md"
    report_path.write_text("\n\n".join(sections), encoding="utf-8")
    print(f"wrote={report_path}")


def fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def descriptive_section(df: pd.DataFrame, output_dir: Path) -> str:
    lines = ["# Initial Analysis Report", "", "## Descriptive Analysis", ""]

    # (a) pathway distribution by birth cohort
    lines.append("### Pathway distribution by birth cohort")
    lines.append("")
    cohort_order = ["<1990", "1990-1994", "1995-1999", "2000-2004", "2005+"]
    labeled = df[df["pathway_category"].notna() & (df["pathway_category"] != "")]
    crosstab = pd.crosstab(labeled["birth_cohort"], labeled["pathway_category"], normalize="index")
    crosstab = crosstab.reindex(index=[c for c in cohort_order if c in crosstab.index])
    crosstab = crosstab[[c for c in PATHWAY_ORDER if c in crosstab.columns]]
    counts = pd.crosstab(labeled["birth_cohort"], labeled["pathway_category"])
    counts = counts.reindex(index=[c for c in cohort_order if c in counts.index])
    lines.append("| birth cohort | n | " + " | ".join(crosstab.columns) + " |")
    lines.append("|---|---|" + "---|" * len(crosstab.columns))
    for cohort in crosstab.index:
        n = counts.loc[cohort].sum()
        row_pcts = " | ".join(fmt_pct(crosstab.loc[cohort, col]) for col in crosstab.columns)
        lines.append(f"| {cohort} | {n} | {row_pcts} |")
    lines.append("")

    # (b)-(d) outcome rates by pathway, with Wilson 95% CI
    lines.append("### Outcome rates by primary pathway (with 95% Wilson CI)")
    lines.append("")
    lines.append("| pathway_category | n | J1 attainment | overseas move (labeled subset only) | national-team selection |")
    lines.append("|---|---|---|---|---|")
    for category in PATHWAY_ORDER:
        sub = df[df["pathway_category"] == category]
        n = len(sub)
        if n == 0:
            continue
        j1_rate, j1_ci = rate_with_ci(sub["reached_j1"] == 1)
        overseas_labeled = sub[sub["moved_overseas"].notna() & (sub["moved_overseas"] != "")]
        if len(overseas_labeled) > 0:
            overseas_rate, overseas_ci = rate_with_ci(overseas_labeled["moved_overseas"] == "1")
            overseas_text = f"{fmt_pct(overseas_rate)} (n={len(overseas_labeled)}, CI {fmt_pct(overseas_ci[0])}-{fmt_pct(overseas_ci[1])})"
        else:
            overseas_text = "n/a"
        nt_labeled_sub = sub[sub["nt_labeled"]]
        nt_rate, nt_ci = rate_with_ci(nt_labeled_sub["nt_yes"] == 1)
        lines.append(
            f"| {category} | {n} | {fmt_pct(j1_rate)} (CI {fmt_pct(j1_ci[0])}-{fmt_pct(j1_ci[1])}) "
            f"| {overseas_text} "
            f"| {fmt_pct(nt_rate)} (n={len(nt_labeled_sub)}, CI {fmt_pct(nt_ci[0])}-{fmt_pct(nt_ci[1])}) |"
        )
    lines.append("")

    # (e) median J1 debut age by pathway
    lines.append("### Median J1 debut age by pathway (among players who reached J1)")
    lines.append("")
    lines.append("| pathway_category | n reached J1 | median first_j1_age |")
    lines.append("|---|---|---|")
    reached = df[df["reached_j1"] == 1]
    for category in PATHWAY_ORDER:
        sub = reached[reached["pathway_category"] == category]
        if len(sub) == 0:
            continue
        lines.append(f"| {category} | {len(sub)} | {sub['first_j1_age'].median():.1f} |")
    lines.append("")

    make_bar_chart(
        df,
        output_dir / "j1_attainment_by_pathway.png",
        title="J1 attainment rate by pathway_category",
        rate_column_fn=lambda sub: (sub["reached_j1"] == 1),
    )
    make_bar_chart(
        df,
        output_dir / "national_team_selection_by_pathway.png",
        title="National-team selection rate by pathway_category",
        rate_column_fn=lambda sub: (sub[sub["nt_labeled"]]["nt_yes"] == 1),
        filter_fn=lambda sub: sub[sub["nt_labeled"]],
    )
    lines.append("Charts: `j1_attainment_by_pathway.png`, `national_team_selection_by_pathway.png`")

    return "\n".join(lines)


def rate_with_ci(bool_series: pd.Series) -> tuple[float, tuple[float, float]]:
    n = len(bool_series)
    successes = int(bool_series.sum())
    rate = successes / n if n else 0.0
    ci = wilson_confidence_interval(successes, n)
    return rate, ci


def make_bar_chart(df, path, *, title, rate_column_fn, filter_fn=None):
    categories = [c for c in PATHWAY_ORDER if c in df["pathway_category"].unique()]
    rates = []
    for category in categories:
        sub = df[df["pathway_category"] == category]
        if filter_fn is not None:
            sub = filter_fn(sub)
        bool_series = rate_column_fn(df[df["pathway_category"] == category])
        rate, _ = rate_with_ci(bool_series)
        rates.append(rate * 100)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(categories, rates)
    ax.set_ylabel("%")
    ax.set_title(title)
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, rotation=30, ha="right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def logistic_regression_section(df: pd.DataFrame) -> str:
    lines = ["## Logistic Regression", ""]

    model_df = df[df["pathway_category"].isin(MAIN_PATHWAYS) & df["birth_year"].notna()].copy()
    model_df["pathway_category"] = pd.Categorical(
        model_df["pathway_category"], categories=MAIN_PATHWAYS
    )
    model_df["birth_year_c"] = model_df["birth_year"] - BIRTH_YEAR_REFERENCE

    lines.append(
        f"Restricted to the three well-populated pathway categories "
        f"({', '.join(MAIN_PATHWAYS)}, n={len(model_df)} of {len(df)} total players); "
        f"`jfa_academy`/`grassroots_club` (n=20 combined) are too small for stable "
        f"coefficient estimates and `unknown`/blank rows carry no real pathway "
        f"signal. Reference category is `j_club_academy`. `birth_year` (centered "
        f"on {BIRTH_YEAR_REFERENCE}, so the intercept reads as an "
        f"average-birth-year player rather than an uninterpretable extrapolation "
        f"to birth_year=0) is included as a control because younger cohorts have "
        f"had less time to reach J1 or be selected — without it, a pathway that "
        f"happens to skew younger would look artificially worse."
    )
    lines.append("")

    lines.append("### J1 attainment ~ pathway_category + birth_year")
    lines.append("")
    j1_model = smf.logit(
        "reached_j1 ~ C(pathway_category, Treatment(reference='j_club_academy')) + birth_year_c",
        data=model_df,
    ).fit(disp=0)
    lines.append(format_logit_summary(j1_model, model_df, "reached_j1"))
    lines.append("")

    lines.append("### National-team selection ~ pathway_category + birth_year")
    lines.append("")
    lines.append(
        "`nt_yes`=1 only for a confirmed `yes`; `unclear` and unlabeled rows are "
        "excluded from this model rather than treated as a negative."
    )
    lines.append("")
    nt_model_df = model_df[model_df["nt_labeled"]]
    nt_model = smf.logit(
        "nt_yes ~ C(pathway_category, Treatment(reference='j_club_academy')) + birth_year_c",
        data=nt_model_df,
    ).fit(disp=0)
    lines.append(format_logit_summary(nt_model, nt_model_df, "nt_yes"))

    return "\n".join(lines)


def format_logit_summary(model, model_df: pd.DataFrame, outcome_column: str) -> str:
    params = model.params
    conf_int = model.conf_int()
    pvalues = model.pvalues

    lines = [
        f"n={int(model.nobs)}, outcome positive rate={model_df[outcome_column].mean() * 100:.1f}%, "
        f"pseudo R-squared={model.prsquared:.3f}",
        "",
        "| term | odds ratio | 95% CI | p-value |",
        "|---|---|---|---|",
    ]
    for term in params.index:
        or_value = math.exp(params[term])
        ci_low = math.exp(conf_int.loc[term, 0])
        ci_high = math.exp(conf_int.loc[term, 1])
        p = pvalues[term]
        lines.append(f"| {term} | {or_value:.2f} | {ci_low:.2f}-{ci_high:.2f} | {p:.4f} |")
    return "\n".join(lines)


def survival_section(df: pd.DataFrame, output_dir: Path) -> str:
    lines = ["## Survival Analysis: Time to J1 Debut", ""]

    # Non-reached players must be censored at a common administrative cutoff
    # (the end of the 2014-2025 data collection window), not at their own
    # last_observed_season: a player who stops appearing in J1/J2/J3 data in,
    # say, 2016 usually left the league (retired, went amateur/regional) —
    # that departure is itself evidence they didn't reach J1, not a neutral
    # "we stopped watching" point. Using last_observed_season as the censoring
    # time confounds "still under study" with "still an active pro player" and
    # made the KM curve implausibly cross 50% for university-pathway players
    # despite only 37.7% of them ever reaching J1 in the raw data.
    study_end_season = int(df["last_observed_season"].max())
    model_df = df[df["pathway_category"].isin(MAIN_PATHWAYS) & df["birth_year"].notna()].copy()
    model_df["duration"] = model_df.apply(
        lambda row: row["first_j1_age"]
        if row["reached_j1"] == 1
        else (study_end_season - row["birth_year"]),
        axis=1,
    )
    model_df["event"] = model_df["reached_j1"]
    model_df = model_df[model_df["duration"].notna() & (model_df["duration"] > 0)]

    lines.append(
        f"Duration is age (years since birth); event=1 at first_j1_age for "
        f"players who reached J1, right-censored at `{study_end_season} - "
        f"birth_year` (a common administrative end-of-study cutoff, not each "
        f"player's own last_observed_season — see code comment for why) for "
        f"players who haven't. n={len(model_df)}."
    )
    lines.append("")

    fig, ax = plt.subplots(figsize=(7, 5))
    median_ages = []
    for category in MAIN_PATHWAYS:
        sub = model_df[model_df["pathway_category"] == category]
        kmf = KaplanMeierFitter()
        kmf.fit(sub["duration"], event_observed=sub["event"], label=category)
        kmf.plot_survival_function(ax=ax)
        median_ages.append((category, kmf.median_survival_time_, len(sub)))
    ax.set_xlabel("Age")
    ax.set_ylabel("Proportion not yet reached J1")
    ax.set_title("Kaplan-Meier: time to J1 debut by pathway_category")
    fig.tight_layout()
    fig.savefig(output_dir / "km_time_to_j1_debut.png", dpi=120)
    plt.close(fig)

    lines.append("| pathway_category | n | median age at J1 debut (KM estimate) |")
    lines.append("|---|---|---|")
    for category, median_age, n in median_ages:
        if median_age == median_age and math.isfinite(median_age):
            median_text = f"{median_age:.1f}"
        else:
            median_text = "not reached (>50% never debut by end of study)"
        lines.append(f"| {category} | {n} | {median_text} |")
    lines.append("")
    lines.append("Chart: `km_time_to_j1_debut.png`")
    lines.append("")
    lines.append(
        "Note: the KM curve's long-run plateau (e.g. ~52% for `university`) is "
        "somewhat higher than that pathway's raw observed J1 attainment rate in "
        "the descriptive table above (37.7%) — this is expected, not a "
        "contradiction. KM reweights by how long each player has actually been "
        "followed; many `university`-pathway players are still young and "
        "under observation, so the raw rate understates how many will "
        "eventually reach J1 if followed to the same age as older cohorts."
    )
    lines.append("")

    lines.append("### Cox proportional hazards")
    lines.append("")
    cox_df = model_df[["duration", "event", "pathway_category"]].copy()
    cox_df = pd.get_dummies(cox_df, columns=["pathway_category"], drop_first=False)
    cox_df = cox_df.drop(columns=["pathway_category_j_club_academy"])
    cpf = CoxPHFitter()
    cpf.fit(cox_df, duration_col="duration", event_col="event")
    summary = cpf.summary[["coef", "exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]]
    lines.append(
        "Reference category is `j_club_academy`; a hazard ratio above 1 means "
        "*faster* time to J1 debut (higher instantaneous debut rate at a given age)."
    )
    lines.append("")
    lines.append("| term | hazard ratio | 95% CI | p-value |")
    lines.append("|---|---|---|---|")
    for term, row in summary.iterrows():
        lines.append(
            f"| {term} | {row['exp(coef)']:.2f} | "
            f"{row['exp(coef) lower 95%']:.2f}-{row['exp(coef) upper 95%']:.2f} | {row['p']:.4f} |"
        )

    return "\n".join(lines)


def overseas_caveat_section(df: pd.DataFrame) -> str:
    labeled = df[df["moved_overseas"].notna() & (df["moved_overseas"] != "")]
    lines = [
        "## Overseas Move: Not Modeled",
        "",
        f"`moved_overseas` is populated for only {len(labeled)} of {len(df)} players "
        "(0.8%), all drawn from the 2023-2025 observed-reappearance-gap candidate "
        "queue — players who were *already flagged* as plausible overseas movers by "
        "a multi-season absence pattern, not a random or representative sample of "
        "the full population. Fitting a logistic regression or survival model on "
        "this subset would estimate a **selection effect**, not a **pathway "
        "effect** (e.g. any pathway category could look artificially associated "
        "with overseas moves just because that category happens to be "
        "over-represented among *candidates who were already suspected* of moving "
        "abroad). No regression or survival model is reported for this outcome. "
        "See the accompanying data-collection revision proposal for how to extend "
        "coverage before this outcome can be modeled.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
