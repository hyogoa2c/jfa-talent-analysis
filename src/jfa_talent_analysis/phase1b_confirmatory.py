"""H1b-2: the pathway x era interaction, on the risk-difference scale (SAP §6).

The estimand is a difference of differences: within each era, how much lower is
the chance of reaching J1 by 25 for a university or high-school player than for
a club-academy player, and is that gap different between the eras. Odds ratios
are reported because the model produces them, but the gate, the tolerance and
the conclusion are all in percentage points, which is why g-computation and not
the coefficient is the primary quantity.

Nothing here reads a file. The sealed run (`scripts/run_phase1b_confirmatory.py`)
does the reading, once; keeping the statistics in a module is what let this be
written and tested while the outcome was still unseen.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

MAIN_PATHWAYS = ("j_club_academy", "high_school", "university")
BASE_PATHWAY = "j_club_academy"
CONTRASTS = tuple(p for p in MAIN_PATHWAYS if p != BASE_PATHWAY)
ERAS = ("era1", "era2")

PATHWAY_TERM = "C(pathway_category, Treatment('j_club_academy'))"
ERA_TERM = "C(era, Treatment('era1'))"
OUTCOME = "reached_j1_by_age25"

BOOTSTRAP_SEED = 20260718
BOOTSTRAP_DRAWS = 500
MONTE_CARLO_SEED = 20260718
MONTE_CARLO_DRAWS = 2000


@dataclass(frozen=True)
class Spec:
    """One birth-year adjustment from §6's pre-specified battery."""

    label: str
    birth_year_term: str

    def formula(self) -> str:
        terms = [f"{PATHWAY_TERM}*{ERA_TERM}"]
        if self.birth_year_term:
            terms.append(self.birth_year_term)
        return f"{OUTCOME} ~ " + " + ".join(terms)

    def null_formula(self) -> str:
        """The same model without the interaction: the joint test's null."""
        terms = [PATHWAY_TERM, ERA_TERM]
        if self.birth_year_term:
            terms.append(self.birth_year_term)
        return f"{OUTCOME} ~ " + " + ".join(terms)


def specs(spline_term: str) -> tuple[Spec, ...]:
    """§6's four adjustments, main first.

    The spline term is built from the data's own quantiles, so it is passed in
    rather than hard-coded -- but its knots are fixed before the run, at the
    five-year quantiles §6 names.
    """
    return (
        Spec("era内中心化線形（主）", "within_era_birth_year"),
        Spec("無調整", ""),
        Spec("era別線形", f"within_era_birth_year:{ERA_TERM}"),
        Spec("全域RCS", spline_term),
    )


def quintile_knots(birth_year: pd.Series) -> list[float]:
    """Knots at the five-year quantiles §6 pre-specifies, as plain numbers."""
    return [float(v) for v in np.quantile(birth_year.to_numpy(float), [0.2, 0.4, 0.6, 0.8])]


def spline_term(knots: list[float]) -> str:
    inner = ", ".join(f"{k:.4f}" for k in knots)
    return f"cr(birth_year, knots=[{inner}])"


def build_frame(pooled: pd.DataFrame) -> pd.DataFrame:
    """The confirmatory analysis sample (§3): eligible, era1/era2, main pathways.

    `within_era_birth_year` is the birth year centred on its own era's median,
    which is what makes the linear adjustment comparable across eras instead of
    extrapolating one era's trend into the other's range.
    """
    frame = pooled[
        (pooled["eligible_confirmatory"].astype(str) == "1")
        & (pooled["era"].isin(ERAS))
        & (pooled["pathway_category"].isin(MAIN_PATHWAYS))
    ].copy()
    frame["birth_year"] = frame["birth_year"].astype(float)
    frame[OUTCOME] = frame[OUTCOME].astype(float)
    centre = frame.groupby("era")["birth_year"].transform("median")
    frame["within_era_birth_year"] = frame["birth_year"] - centre
    return frame.reset_index(drop=True)


def _fit(df: pd.DataFrame, formula: str, weights_col: str | None = None):
    """The logit, or its weighted GLM twin when a scenario carries weights.

    S8 reweights players by how likely their label was to be resolved at all, so
    it needs a weighted fit; everything else uses the plain logit. Both are the
    same likelihood, and `predict` behaves identically, so g-computation
    downstream does not need to know which one ran.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if weights_col is None:
            return smf.logit(formula, data=df).fit(disp=False, maxiter=200)
        return smf.glm(
            formula,
            data=df,
            family=sm.families.Binomial(),
            freq_weights=df[weights_col].to_numpy(float),
        ).fit()


def joint_interaction_test(df: pd.DataFrame, spec: Spec) -> dict[str, float]:
    """The single confirmatory test: a two-sided joint LR test of pathway x era."""
    full = _fit(df, spec.formula())
    null = _fit(df, spec.null_formula())
    statistic = 2 * (full.llf - null.llf)
    df_diff = int(full.df_model - null.df_model)
    return {
        "lr_statistic": float(statistic),
        "df": df_diff,
        "p_value": float(stats.chi2.sf(statistic, df_diff)),
        "n": int(full.nobs),
    }


def standardized_risks(df: pd.DataFrame, formula: str, weights_col: str | None = None) -> pd.DataFrame:
    """G-computation: each era's risk under each pathway, holding the era's own
    covariate distribution fixed.

    Standardising within era and not over the pooled sample is the point: the
    estimand compares each era's internal gap, so each era's counterfactual has
    to be taken over that era's own players.
    """
    fit = _fit(df, formula, weights_col)
    records = []
    for era in ERAS:
        block = df[df["era"] == era]
        for pathway in MAIN_PATHWAYS:
            counterfactual = block.copy()
            counterfactual["pathway_category"] = pathway
            records.append(
                {
                    "era": era,
                    "pathway": pathway,
                    "risk": float(fit.predict(counterfactual).mean()),
                    "n": len(block),
                }
            )
    return pd.DataFrame(records)


def risk_differences(risks: pd.DataFrame) -> pd.DataFrame:
    """Each era's pathway gap against the club-academy reference."""
    records = []
    for era in ERAS:
        block = risks[risks["era"] == era].set_index("pathway")["risk"]
        for pathway in CONTRASTS:
            records.append(
                {"era": era, "pathway": pathway, "risk_difference": block[pathway] - block[BASE_PATHWAY]}
            )
    return pd.DataFrame(records)


def did(differences: pd.DataFrame) -> dict[str, float]:
    """era2 gap minus era1 gap, per pathway. Positive = the gap narrowed."""
    table = differences.pivot(index="pathway", columns="era", values="risk_difference")
    return {pathway: float(table.loc[pathway, "era2"] - table.loc[pathway, "era1"]) for pathway in CONTRASTS}


def point_estimates(
    df: pd.DataFrame, formula: str, weights_col: str | None = None
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    risks = standardized_risks(df, formula, weights_col)
    differences = risk_differences(risks)
    return risks, differences, did(differences)


def bootstrap_did(
    df: pd.DataFrame,
    formula: str,
    n_boot: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> pd.DataFrame:
    """Percentile intervals for the DID, resampling players within era.

    Resampling within era keeps each era's size fixed, so the interval reflects
    uncertainty in the gaps rather than in how many players each era happened to
    contribute.
    """
    rng = np.random.default_rng(seed)
    draws: dict[str, list[float]] = {pathway: [] for pathway in CONTRASTS}
    failures = 0
    blocks = {era: df[df["era"] == era] for era in ERAS}
    for _ in range(n_boot):
        sample = pd.concat(
            [block.sample(n=len(block), replace=True, random_state=int(rng.integers(2**32))) for block in blocks.values()],
            ignore_index=True,
        )
        try:
            _, _, values = point_estimates(sample, formula)
        except Exception:
            failures += 1
            continue
        for pathway, value in values.items():
            draws[pathway].append(value)
    records = []
    for pathway, values in draws.items():
        array = np.asarray(values)
        records.append(
            {
                "pathway": pathway,
                "did_ci_low": float(np.percentile(array, 2.5)) if array.size else np.nan,
                "did_ci_high": float(np.percentile(array, 97.5)) if array.size else np.nan,
                "n_boot_ok": int(array.size),
                "n_boot_failed": failures,
            }
        )
    return pd.DataFrame(records)
