"""Gate B: what measurement error could do to the DID (SAP §6b-6).

The question is not "is the label accurate" -- Gate A answered that -- but
"could the labelling error, at the rates gold actually measured, manufacture the
era difference we are about to report". So every scenario ends in the same
number the main analysis ends in, a DID in percentage points, and the gate
compares those numbers rather than their confidence intervals (§6b-6 is explicit
that CI overlap is not the criterion).

Two families live here. S1-S5 redraw each player's *true* pathway from the gold
confusion matrix and refit, propagating the verification sample's own
uncertainty through a Dirichlet. S6-S10 are deterministic re-analyses of a
different label or a different subsample. Both report the same way.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .phase1b_confirmatory import CONTRASTS, ERAS, MAIN_PATHWAYS, point_estimates

# Jeffreys prior on each row of the matrix, so a cell gold never saw is unlikely
# rather than impossible.
JEFFREYS = 0.5

TOLERANCE_PP = 3.0
AUXILIARY_TOLERANCE_PP = 5.0

# §6b-6 S5, operationalised at v14: the strata where the two procedures disagree
# or no institution could be identified.
HARD_STRATA = ("disagree_other", "club_list_only", "institution_unknown")
HARD_CASE_ERROR_RATE = 0.40

# §6b-6 S3/S4 stress multipliers, given as explicit assumptions rather than as
# anything the gold posterior supports.
STRESS_MULTIPLIER = 2.0


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    description: str
    did: dict[str, float]
    did_low: dict[str, float]
    did_high: dict[str, float]
    n: int


def true_given_observed(
    pairs: pd.DataFrame, era: str, weighted: bool = True
) -> dict[str, dict[str, float]]:
    """Weighted gold counts of the true pathway within each observed label.

    Conditioning on the observed label is what the design supports: the holdout
    was drawn by observed stratum, so "given the pipeline said X, what was the
    truth" is estimated directly, without needing a separate prior over the
    truth's prevalence.
    """
    block = pairs[pairs["era"] == era]
    counts: dict[str, dict[str, float]] = {}
    for observed in MAIN_PATHWAYS:
        column = block[block["label"] == observed]
        weights = column["weight"] if weighted else pd.Series(1.0, index=column.index)
        cell = {}
        for true in MAIN_PATHWAYS:
            cell[true] = float(weights[column["gold"] == true].sum())
        # Scale the weighted mass back to how many rows were actually verified,
        # so the Dirichlet's spread reflects the verification effort and not the
        # population the weights represent.
        total_weight = sum(cell.values())
        scale = (len(column) / total_weight) if total_weight else 0.0
        counts[observed] = {true: value * scale for true, value in cell.items()}
    return counts


def _draw_matrix(
    counts: dict[str, dict[str, float]], rng: np.random.Generator
) -> dict[str, np.ndarray]:
    return {
        observed: rng.dirichlet([counts[observed][true] + JEFFREYS for true in MAIN_PATHWAYS])
        for observed in MAIN_PATHWAYS
    }


def _reassign(
    df: pd.DataFrame, matrices: dict[str, dict[str, np.ndarray]], rng: np.random.Generator
) -> pd.DataFrame:
    """Redraw every player's pathway from P(true | observed) for their era."""
    redrawn = df.copy()
    values = redrawn["pathway_category"].to_numpy(object)
    eras = redrawn["era"].to_numpy(object)
    for era in ERAS:
        for observed in MAIN_PATHWAYS:
            mask = (eras == era) & (values == observed)
            size = int(mask.sum())
            if not size:
                continue
            values[mask] = rng.choice(MAIN_PATHWAYS, size=size, p=matrices[era][observed])
    redrawn["pathway_category"] = values
    return redrawn


def _stress(counts: dict[str, dict[str, float]], multiplier: float) -> dict[str, dict[str, float]]:
    """Multiply the off-diagonal mass, i.e. assume more error than gold saw."""
    stressed = {}
    for observed, row in counts.items():
        stressed[observed] = {
            true: (value * multiplier if true != observed else value) for true, value in row.items()
        }
    return stressed


def _stress_into_academy(
    counts: dict[str, dict[str, float]], multiplier: float
) -> dict[str, dict[str, float]]:
    """Stress only the direction that empties the reference category.

    §6b-6 requires an asymmetric scenario because a one-way error into
    `j_club_academy` changes the baseline risk the whole DID is measured
    against, and a symmetric assumption cannot reproduce that.
    """
    stressed = {observed: dict(row) for observed, row in counts.items()}
    for observed in MAIN_PATHWAYS:
        if observed == "j_club_academy":
            continue
        stressed[observed]["j_club_academy"] *= multiplier
    return stressed


def monte_carlo_scenario(
    df: pd.DataFrame,
    formula: str,
    matrices_counts: dict[str, dict[str, dict[str, float]]],
    draws: int,
    seed: int,
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Median and 2.5/97.5 percentile DID over redrawn true-pathway labels."""
    rng = np.random.default_rng(seed)
    collected: dict[str, list[float]] = {pathway: [] for pathway in CONTRASTS}
    for _ in range(draws):
        matrices = {era: _draw_matrix(matrices_counts[era], rng) for era in ERAS}
        try:
            _, _, values = point_estimates(_reassign(df, matrices, rng), formula)
        except Exception:
            continue
        for pathway, value in values.items():
            collected[pathway].append(value)
    median, low, high = {}, {}, {}
    for pathway, values in collected.items():
        array = np.asarray(values)
        median[pathway] = float(np.median(array)) if array.size else float("nan")
        low[pathway] = float(np.percentile(array, 2.5)) if array.size else float("nan")
        high[pathway] = float(np.percentile(array, 97.5)) if array.size else float("nan")
    return median, low, high


def stopping_conditions(
    main: dict[str, float], scenarios: list[ScenarioResult], tolerance_pp: float = TOLERANCE_PP
) -> pd.DataFrame:
    """§6b-6's four stopping conditions, applied to the whole envelope.

    Condition 3 ("the envelope contains both zero and an important effect in the
    opposite direction") is read as: some scenario's DID sits on each side of
    zero by at least the tolerance.
    """
    records = []
    for pathway in CONTRASTS:
        values = [s.did[pathway] for s in scenarios if not np.isnan(s.did[pathway])]
        main_value = main[pathway]
        sign_flip = [s.scenario for s in scenarios if np.sign(s.did[pathway]) != np.sign(main_value)]
        exceeds = [
            s.scenario
            for s in scenarios
            if abs(s.did[pathway] - main_value) * 100 >= tolerance_pp
        ]
        both_sides = (
            max(values) * 100 >= tolerance_pp and min(values) * 100 <= -tolerance_pp
            if values
            else False
        )
        records.append(
            {
                "pathway": pathway,
                "main_did_pp": main_value * 100,
                "envelope_low_pp": min(values) * 100 if values else np.nan,
                "envelope_high_pp": max(values) * 100 if values else np.nan,
                "条件1_符号反転": ", ".join(sign_flip) or "なし",
                "条件2_差が許容差以上": ", ".join(exceeds) or "なし",
                "条件3_両側に重要な値": "該当" if both_sides else "なし",
            }
        )
    return pd.DataFrame(records)


def tipping_point(
    df: pd.DataFrame,
    formula: str,
    counts: dict[str, dict[str, dict[str, float]]],
    main: dict[str, float],
    seed: int,
    multipliers: tuple[float, ...] = (1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0),
) -> pd.DataFrame:
    """How much worse than measured the era1 error must be to move the DID.

    §6b-6 condition 4 asks for a tipping point inside a plausible range, which
    is a different question from the posterior: it multiplies era1's measured
    off-diagonal mass and reports where the conclusion changes.
    """
    rng_seed = seed
    records = []
    for multiplier in multipliers:
        stressed = {"era1": _stress(counts["era1"], multiplier), "era2": counts["era2"]}
        median, _, _ = monte_carlo_scenario(df, formula, stressed, draws=200, seed=rng_seed)
        rng_seed += 1
        row = {"era1_誤分類倍率": multiplier}
        for pathway in CONTRASTS:
            row[f"{pathway}_did_pp"] = median[pathway] * 100
            row[f"{pathway}_主推定との差_pp"] = (median[pathway] - main[pathway]) * 100
            row[f"{pathway}_符号反転"] = np.sign(median[pathway]) != np.sign(main[pathway])
        records.append(row)
    return pd.DataFrame(records)
