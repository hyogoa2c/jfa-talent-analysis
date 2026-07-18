"""Phase 1 confirmatory analysis primitives (docs/research_plan_phase1.md §6).

Every modeling choice here is pre-specified by the SAP committed on
research/phase1-plan-fixation (0dc078b, amended 4fd9438): exposure =
pathway_category with j_club_academy as the reference, birth-cohort adjustment
via a natural cubic spline, institution-cluster-robust standard errors as the
primary covariance, and reporting of adjusted predicted probabilities and
pathway risk differences alongside odds ratios. Deviations must be logged in
the SAP's 変更履歴 section.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from .coach_network import normalize_institution_name
from .pathway_outcome_analysis import (
    earliest_youth_selection_age,
    has_a_team_selection,
    has_youth_national_team_selection,
    parse_birth_year,
    youth_category_count,
)

MAIN_PATHWAYS = ("j_club_academy", "high_school", "university")
BASE_PATHWAY = "j_club_academy"
BIRTH_YEAR_CENTER = 1995

PATHWAY_TERM = "C(pathway_category, Treatment('j_club_academy'))"
COHORT_SPLINE_TERM = "cr(birth_year_c, df=4)"

POSITION_ORDER = ("GK", "DF", "MF", "FW")


def aggregate_position_mode(positions: pd.Series) -> str | None:
    """Collapse player-season position_master values to one player-level
    position by the SAP §6 rule (最頻値). Ties break by the fixed
    GK→DF→MF→FW order so the aggregation is deterministic."""
    counts = positions.dropna().value_counts()
    if counts.empty:
        return None
    best = counts.max()
    for position in POSITION_ORDER:
        if counts.get(position, 0) == best:
            return position
    return str(counts.idxmax())


def final_dev_institution(stints: pd.DataFrame) -> pd.Series:
    """Final pre-professional institution per player, normalized.

    "Final" = the highest line_index among youth_flag=1 rows (所属クラブ lines
    are chronological). Registration-formality rows (2種登録 etc.) carry
    youth_flag=0 and are excluded twice over. The normalized name is the
    cluster unit for institution-cluster-robust standard errors.
    """
    dev = stints[
        (stints["youth_flag"] == "1") & (stints["registration_formality"] != "1")
    ].copy()
    dev["line_index"] = dev["line_index"].astype(int)
    dev = dev.sort_values(["source_player_id", "line_index"])
    last = dev.groupby("source_player_id").tail(1)
    return pd.Series(
        [normalize_institution_name(name) for name in last["institution"]],
        index=pd.Index(last["source_player_id"].to_numpy(), name="source_player_id"),
        name="final_institution",
    )


def build_analysis_frame(
    outcomes: pd.DataFrame,
    stints: pd.DataFrame | None = None,
    season_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Derive the SAP analysis variables on the player-level outcomes table.

    outcomes must be read with dtype=str so outcome encodings survive
    ("1"/"0" for reached_j1_ever and moved_overseas_final, "yes"/"no"/
    "unclear"/"" for any_national_team_selection).
    """
    df = outcomes.copy()
    df["birth_year"] = df["birth_date"].apply(parse_birth_year)
    df["birth_year_c"] = df["birth_year"] - BIRTH_YEAR_CENTER
    categories = df["national_team_categories"].fillna("")
    df["youth_selected"] = categories.apply(has_youth_national_team_selection).astype(int)
    df["youth_cat_count"] = categories.apply(youth_category_count)
    df["earliest_youth_age"] = categories.apply(earliest_youth_selection_age)
    df["a_team_selected"] = categories.apply(has_a_team_selection).astype(int)
    df["reached_j1"] = pd.to_numeric(df["reached_j1_ever"], errors="coerce")
    df["overseas_yes"] = (df["moved_overseas_final"] == "1").astype(int)
    df["overseas_labeled"] = df["moved_overseas_final"].isin(["1", "0"])
    df["nt_labeled"] = df["any_national_team_selection"].isin(["yes", "no"])
    df["in_main_pathways"] = df["pathway_category"].isin(MAIN_PATHWAYS)
    df["career_minutes_num"] = pd.to_numeric(df["career_minutes"], errors="coerce").fillna(0)
    df["minutes_tier"] = pd.cut(
        df["career_minutes_num"],
        bins=[-1, 499, 2999, np.inf],
        labels=["C", "B", "A"],
    ).astype(str)
    df["identified"] = (df["pathway_category_source"] != "identity_not_confirmed").astype(int)

    if stints is not None:
        institution = final_dev_institution(stints)
        df = df.merge(
            institution.rename("final_institution"),
            how="left",
            left_on="source_player_id",
            right_index=True,
        )
    else:
        df["final_institution"] = pd.NA

    if season_features is not None:
        position = (
            season_features.groupby("source_player_id")["position_master"]
            .apply(aggregate_position_mode)
            .rename("position_mode")
        )
        df = df.merge(position, how="left", left_on="source_player_id", right_index=True)
    else:
        df["position_mode"] = pd.NA

    return df


@dataclass
class FittedLogit:
    label: str
    formula: str
    result: object
    n: int
    cov_type: str
    n_clusters: int | None = None


def fit_logit(
    df: pd.DataFrame,
    formula: str,
    label: str,
    cluster_col: str | None = None,
) -> FittedLogit:
    """Fit a logit; with cluster_col, use cluster-robust covariance grouped by
    that column (rows with a missing cluster value are dropped first).

    The caller must pass complete cases for every formula variable: if patsy
    silently dropped rows, the cluster groups vector would misalign with the
    estimation sample, so a row-count mismatch raises instead.
    """
    if cluster_col is not None:
        data = df[df[cluster_col].notna()].copy()
        model = smf.logit(formula, data=data)
        n_used = int(model.endog.shape[0])
        if n_used != len(data):
            raise ValueError(
                f"{label}: formula dropped {len(data) - n_used} rows; "
                "cluster groups would misalign. Pass complete cases."
            )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = model.fit(
                disp=False,
                maxiter=200,
                cov_type="cluster",
                cov_kwds={"groups": data[cluster_col]},
            )
        _require_convergence(result, label)
        return FittedLogit(
            label=label,
            formula=formula,
            result=result,
            n=int(result.nobs),
            cov_type="cluster",
            n_clusters=int(data[cluster_col].nunique()),
        )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = smf.logit(formula, data=df).fit(disp=False, maxiter=200)
    _require_convergence(result, label)
    return FittedLogit(
        label=label, formula=formula, result=result, n=int(result.nobs), cov_type="nonrobust"
    )


def _acceptably_converged(result, tol: float = 1e-6) -> bool:
    """statsmodels' Newton convergence flag can report False with a gradient
    of ~1e-13 (near-collinear spline columns make the step-size check
    oscillate). Trust the score: at an MLE the gradient is ~0."""
    if result.mle_retvals.get("converged", True):
        return True
    score = result.model.score(result.params)
    return bool(np.max(np.abs(score)) < tol)


def _require_convergence(result, label: str) -> None:
    if not _acceptably_converged(result):
        raise ValueError(f"{label}: logit did not converge (non-zero score at optimum)")


def odds_ratio_table(fit: FittedLogit) -> pd.DataFrame:
    """Coefficient table on the odds-ratio scale (95% CI from the fitted
    covariance, i.e. cluster-robust when the fit is)."""
    result = fit.result
    ci = result.conf_int()
    with np.errstate(over="ignore"):
        table = _odds_ratio_frame(fit, result, ci)
    return table.reset_index(drop=True)


def _odds_ratio_frame(fit: FittedLogit, result, ci) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "model": fit.label,
            "term": result.params.index,
            "odds_ratio": np.exp(result.params.to_numpy()),
            "ci_low": np.exp(ci[0].to_numpy()),
            "ci_high": np.exp(ci[1].to_numpy()),
            "p_value": result.pvalues.to_numpy(),
            "n": fit.n,
            "cov_type": fit.cov_type,
        }
    )


def adjusted_pathway_probabilities(fit: FittedLogit, df: pd.DataFrame) -> dict[str, float]:
    """G-computation: set every player's pathway to each level, average the
    predicted probability over the model's estimation sample (SAP §6 の
    調整済み予測確率)."""
    estimation = df.loc[df.index.intersection(_estimation_index(fit, df))]
    probabilities = {}
    for level in MAIN_PATHWAYS:
        counterfactual = estimation.copy()
        counterfactual["pathway_category"] = level
        probabilities[level] = float(fit.result.predict(counterfactual).mean())
    return probabilities


def _estimation_index(fit: FittedLogit, df: pd.DataFrame) -> pd.Index:
    row_labels = getattr(fit.result.model.data, "row_labels", None)
    if row_labels is not None:
        return pd.Index(row_labels)
    return df.index


def risk_differences(probabilities: dict[str, float]) -> dict[str, float]:
    base = probabilities[BASE_PATHWAY]
    return {
        level: probabilities[level] - base
        for level in MAIN_PATHWAYS
        if level != BASE_PATHWAY
    }


def bootstrap_risk_differences(
    df: pd.DataFrame,
    formula: str,
    cluster_col: str | None = None,
    n_boot: int = 500,
    seed: int = 20260718,
) -> pd.DataFrame:
    """Percentile bootstrap CIs for the pathway risk differences.

    With cluster_col, whole clusters are resampled with replacement (matching
    the cluster-robust covariance's independence assumption); otherwise rows
    are resampled. Non-converging replicates are skipped and counted.
    """
    rng = np.random.default_rng(seed)
    draws: dict[str, list[float]] = {
        level: [] for level in MAIN_PATHWAYS if level != BASE_PATHWAY
    }
    failures = 0
    if cluster_col is not None:
        df = df[df[cluster_col].notna()]
        groups = {key: frame for key, frame in df.groupby(cluster_col)}
        keys = list(groups)
    for _ in range(n_boot):
        if cluster_col is not None:
            chosen = rng.choice(len(keys), size=len(keys), replace=True)
            sample = pd.concat([groups[keys[i]] for i in chosen], ignore_index=True)
        else:
            sample = df.sample(n=len(df), replace=True, random_state=rng.integers(2**32))
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = smf.logit(formula, data=sample).fit(disp=False, maxiter=200)
            if not _acceptably_converged(result):
                failures += 1
                continue
            fit = FittedLogit(
                label="boot",
                formula=formula,
                result=result,
                n=len(sample),
                cov_type="nonrobust",
            )
            probabilities = adjusted_pathway_probabilities(fit, sample)
        except Exception:
            failures += 1
            continue
        for level, value in risk_differences(probabilities).items():
            draws[level].append(value)
    records = []
    for level, values in draws.items():
        arr = np.asarray(values)
        records.append(
            {
                "pathway": level,
                "rd_ci_low": float(np.percentile(arr, 2.5)) if arr.size else np.nan,
                "rd_ci_high": float(np.percentile(arr, 97.5)) if arr.size else np.nan,
                "n_boot_ok": int(arr.size),
                "n_boot_failed": failures,
            }
        )
    return pd.DataFrame(records)
