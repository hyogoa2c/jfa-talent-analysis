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
from scipy import stats

from jfa_talent_analysis.pathway_outcome_analysis import (
    birth_cohort,
    has_youth_national_team_selection,
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
        "reached_j1_ever",
        "first_j1_year_best",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    df["birth_year"] = df["birth_date"].apply(parse_birth_year)
    df["birth_cohort"] = df["birth_year"].apply(birth_cohort)
    df["pathway_category_filled"] = df["pathway_category"].fillna("").replace("", "no_data")
    df["nt_yes"] = (df["any_national_team_selection"] == "yes").astype(int)
    df["nt_labeled"] = df["any_national_team_selection"].isin(["yes", "no"])
    df["overseas_yes"] = (df["moved_overseas_final"] == "1").astype(int)
    df["overseas_labeled"] = df["moved_overseas_final"].isin(["0", "1"])
    df["youth_selected"] = (
        df["national_team_categories"].fillna("").apply(has_youth_national_team_selection).astype(int)
    )

    # Prefer the Wikipedia-backfill-corrected J1 outcome when present
    # (docs/data_collection_revision_proposal_2026-07-07.md item 1): SFPR01's
    # reached_j1/first_j1_age only see 2014+ debuts. first_j1_age_final is
    # year-precision (first_j1_year_best - birth_year, ignores birth month) so
    # that observed and backfilled debuts carry a uniform precision instead of
    # mixing month-aware and year-only ages.
    if "reached_j1_ever" in df.columns:
        df["reached_j1_final"] = df["reached_j1_ever"].fillna(df["reached_j1"])
        df["first_j1_age_final"] = df["first_j1_year_best"] - df["birth_year"]
    else:
        df["reached_j1_final"] = df["reached_j1"]
        df["first_j1_age_final"] = df["first_j1_age"]
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
    sections.append(additional_modeling_section(df))
    sections.append(early_ability_signal_section(df))

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
    lines.append("| pathway_category | n | J1 attainment | overseas move (Wikipedia classifier, full population) | national-team selection |")
    lines.append("|---|---|---|---|---|")
    for category in PATHWAY_ORDER:
        sub = df[df["pathway_category"] == category]
        n = len(sub)
        if n == 0:
            continue
        j1_rate, j1_ci = rate_with_ci(sub["reached_j1_final"] == 1)
        overseas_labeled = sub[sub["moved_overseas_final"].notna() & (sub["moved_overseas_final"] != "")]
        if len(overseas_labeled) > 0:
            overseas_rate, overseas_ci = rate_with_ci(overseas_labeled["moved_overseas_final"] == "1")
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
    reached = df[df["reached_j1_final"] == 1]
    for category in PATHWAY_ORDER:
        sub = reached[reached["pathway_category"] == category]
        if len(sub) == 0:
            continue
        lines.append(f"| {category} | {len(sub)} | {sub['first_j1_age_final'].median():.1f} |")
    lines.append("")

    make_bar_chart(
        df,
        output_dir / "j1_attainment_by_pathway.png",
        title="J1 attainment rate by pathway_category",
        rate_column_fn=lambda sub: (sub["reached_j1_final"] == 1),
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
        "reached_j1_final ~ C(pathway_category, Treatment(reference='j_club_academy')) + birth_year_c",
        data=model_df,
    ).fit(disp=0)
    lines.append(format_logit_summary(j1_model, model_df, "reached_j1_final"))
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
    lines.append("")

    lines.append("### Overseas move ~ pathway_category + birth_year")
    lines.append("")
    lines.append(
        "`moved_overseas_final` now covers the full population: a heuristic "
        "classifier over Wikipedia career prose (validated 32/32 against a "
        "pilot golden set and cross-checked against the pre-existing 33-player "
        "manually-reviewed queue), with its 196 needs_review rows human-reviewed "
        "(`data/manual/overseas_review_queue.csv`, see "
        "`docs/overseas_needs_review_2026-07-09.md`) — the same confidence "
        "standard as the pathway/national-team labels above."
    )
    lines.append("")
    overseas_model_df = model_df[model_df["overseas_labeled"]]
    overseas_model = smf.logit(
        "overseas_yes ~ C(pathway_category, Treatment(reference='j_club_academy')) + birth_year_c",
        data=overseas_model_df,
    ).fit(disp=0)
    lines.append(format_logit_summary(overseas_model, overseas_model_df, "overseas_yes"))

    return "\n".join(lines)


def additional_modeling_section(df: pd.DataFrame) -> str:
    lines = ["## Additional Modeling", ""]

    model_df = df[df["pathway_category"].isin(MAIN_PATHWAYS) & df["birth_year"].notna()].copy()
    model_df["pathway_category"] = pd.Categorical(
        model_df["pathway_category"], categories=MAIN_PATHWAYS
    )
    model_df["birth_year_c"] = model_df["birth_year"] - BIRTH_YEAR_REFERENCE

    # --- Mediation check: does pathway still predict overseas move once J1
    # attainment is controlled for, or does pathway operate entirely THROUGH
    # reaching J1 first (the much more common route to being scouted abroad)?
    lines.append("### Overseas move ~ pathway_category + reached_j1 + birth_year (mediation check)")
    lines.append("")
    lines.append(
        "The plain overseas model above cannot distinguish \"pathway predicts "
        "overseas moves directly\" from \"pathway predicts J1 attainment, and J1 "
        "attainment is what actually gets players scouted abroad.\" Adding "
        "`reached_j1_final` as a covariate tests this: if the pathway "
        "coefficients shrink toward 1.0 and lose significance once J1 "
        "attainment is in the model, the pathway's overseas association is "
        "mostly *mediated by* reaching J1 first, not a separate direct effect."
    )
    lines.append("")
    mediation_df = model_df[model_df["overseas_labeled"]]
    mediation_model = smf.logit(
        "overseas_yes ~ C(pathway_category, Treatment(reference='j_club_academy')) "
        "+ reached_j1_final + birth_year_c",
        data=mediation_df,
    ).fit(disp=0)
    lines.append(format_logit_summary(mediation_model, mediation_df, "overseas_yes"))
    lines.append("")

    # --- Interaction: has the pathway effect on J1 attainment shifted across
    # birth cohorts (e.g. as club academies professionalized further)?
    lines.append("### J1 attainment ~ pathway_category * birth_year (era interaction)")
    lines.append("")
    lines.append(
        "Tests whether the pathway gap is stable over time or has widened/"
        "narrowed across birth cohorts, by adding a pathway"
        "×birth_year_c interaction term to the plain J1-attainment model. A "
        "significant interaction term means the university/high_school "
        "penalty (relative to j_club_academy) is not constant across "
        "generations."
    )
    lines.append("")
    interaction_model = smf.logit(
        "reached_j1_final ~ C(pathway_category, Treatment(reference='j_club_academy')) "
        "* birth_year_c",
        data=model_df,
    ).fit(disp=0)
    lines.append(format_logit_summary(interaction_model, model_df, "reached_j1_final"))
    lines.append("")
    lr_stat = 2 * (interaction_model.llf - smf.logit(
        "reached_j1_final ~ C(pathway_category, Treatment(reference='j_club_academy')) + birth_year_c",
        data=model_df,
    ).fit(disp=0).llf)
    lr_p = stats.chi2.sf(lr_stat, df=2)
    lines.append(
        f"Likelihood-ratio test for the two interaction terms jointly: "
        f"LR stat={lr_stat:.2f}, df=2, p={lr_p:.4f} "
        f"({'significant — the pathway effect does change across cohorts' if lr_p < 0.05 else 'not significant at the 0.05 level — no evidence the pathway effect differs by era in this data'})."
    )

    return "\n".join(lines)


def early_ability_signal_section(df: pd.DataFrame) -> str:
    """Adds youth_selected (any U15-U19 national-team call-up) as a control,
    as a first attempt at separating a pre-existing-ability selection effect
    (clubs' academies recruit already-promising kids) from a pathway effect —
    see docs/initial_analysis_interpretation_2026-07-09.md section 5's causal
    warning. This reuses data already collected (national_team_categories),
    no new data collection needed.
    """
    lines = ["## Early-Ability-Signal Control (youth_selected = any U15-U19 call-up)", ""]

    model_df = df[df["pathway_category"].isin(MAIN_PATHWAYS) & df["birth_year"].notna()].copy()
    model_df["pathway_category"] = pd.Categorical(
        model_df["pathway_category"], categories=MAIN_PATHWAYS
    )
    model_df["birth_year_c"] = model_df["birth_year"] - BIRTH_YEAR_REFERENCE

    lines.append("### youth_selected rate by pathway_category")
    lines.append("")
    lines.append(
        "If academies really do recruit already-recognized talent, "
        "`j_club_academy` players should show a higher youth-national-team "
        "call-up rate than `university` players *even before* any pro-career "
        "outcome is considered — a direct check of the selection-effect "
        "hypothesis."
    )
    lines.append("")
    lines.append("| pathway_category | n | youth_selected rate |")
    lines.append("|---|---|---|")
    for category in MAIN_PATHWAYS:
        sub = model_df[model_df["pathway_category"] == category]
        rate, ci = rate_with_ci(sub["youth_selected"] == 1)
        lines.append(f"| {category} | {len(sub)} | {fmt_pct(rate)} (CI {fmt_pct(ci[0])}-{fmt_pct(ci[1])}) |")
    lines.append("")

    lines.append("### J1 attainment ~ pathway_category + birth_year + youth_selected")
    lines.append("")
    lines.append(
        "Compare the pathway odds ratios here to the plain J1-attainment model "
        "above: if they shrink substantially toward 1.0, much of the raw "
        "pathway association is explained by pre-existing ability that both "
        "the pathway choice and the outcome reflect, not by the pathway "
        "itself."
    )
    lines.append("")
    j1_signal_model = smf.logit(
        "reached_j1_final ~ C(pathway_category, Treatment(reference='j_club_academy')) "
        "+ birth_year_c + youth_selected",
        data=model_df,
    ).fit(disp=0)
    lines.append(format_logit_summary(j1_signal_model, model_df, "reached_j1_final"))
    lines.append("")

    lines.append(
        "### Overseas move ~ pathway_category + reached_j1 + birth_year + youth_selected"
    )
    lines.append("")
    overseas_signal_df = model_df[model_df["overseas_labeled"]]
    overseas_signal_model = smf.logit(
        "overseas_yes ~ C(pathway_category, Treatment(reference='j_club_academy')) "
        "+ reached_j1_final + birth_year_c + youth_selected",
        data=overseas_signal_df,
    ).fit(disp=0)
    lines.append(format_logit_summary(overseas_signal_model, overseas_signal_df, "overseas_yes"))

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
        lambda row: row["first_j1_age_final"]
        if row["reached_j1_final"] == 1
        else (study_end_season - row["birth_year"]),
        axis=1,
    )
    model_df["event"] = model_df["reached_j1_final"]
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
    km_plateaus = {}
    for category in MAIN_PATHWAYS:
        sub = model_df[model_df["pathway_category"] == category]
        kmf = KaplanMeierFitter()
        kmf.fit(sub["duration"], event_observed=sub["event"], label=category)
        kmf.plot_survival_function(ax=ax)
        median_ages.append((category, kmf.median_survival_time_, len(sub)))
        km_plateaus[category] = 1 - kmf.survival_function_.iloc[-1, 0]
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
    raw_university_rate = (
        df.loc[df["pathway_category"] == "university", "reached_j1_final"].eq(1).mean() * 100
    )
    lines.append(
        f"Note: the KM curve's long-run plateau (~{km_plateaus['university'] * 100:.0f}% for "
        f"`university`) is somewhat higher than that pathway's raw observed J1 "
        f"attainment rate in the descriptive table above ({raw_university_rate:.1f}%) "
        "— this is expected, not a contradiction. KM reweights by how long each "
        "player has actually been followed; many `university`-pathway players "
        "are still young and under observation, so the raw rate understates how "
        "many will eventually reach J1 if followed to the same age as older "
        "cohorts."
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
    labeled = df[df["moved_overseas_final"].notna() & (df["moved_overseas_final"] != "")]
    manual = df[df["moved_overseas_final_source"] == "manual_review"]
    human_reviewed = df[
        df["moved_overseas_final_source"].isin(
            ["human_reviewed", "human_reviewed_over_gap_scoped_review"]
        )
    ]
    auto_only = df[df["moved_overseas_final_source"] == "wikipedia_classifier"]
    lines = [
        "## Overseas Move: Coverage Note",
        "",
        f"`moved_overseas_final` now covers {len(labeled)} of {len(df)} players "
        f"({len(labeled) / len(df) * 100:.1f}%), up from the 33-player (0.8%) "
        "manually-reviewed-only coverage this report originally shipped with "
        "(see `docs/data_collection_revision_proposal_2026-07-07.md` item 2, "
        "`docs/jfa_national_team_spot_check_2026-07-08.md`'s sibling work, and "
        "`docs/overseas_needs_review_2026-07-09.md` for the classifier's "
        "needs_review pass). "
        f"{len(manual)} rows carry the original, narrowly-scoped 2023-2025 "
        f"reappearance-gap manual review; {len(human_reviewed)} more come from "
        "the classifier's needs_review rows after human review; the remaining "
        f"{len(auto_only)} are the classifier's high-confidence, unreviewed "
        "output. The logistic regression above uses this expanded column, not "
        "the original 33-row `moved_overseas` field.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
