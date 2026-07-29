"""How much gold is needed before Gate B's DID comparison can be judged.

Gate B asks whether a measurement scenario moves the DID by at least the
robustness tolerance (SAP §6b-6, 3pp). That comparison is only meaningful if the
DID correction is itself pinned down more finely than the tolerance -- otherwise
the answer is dominated by how few players were verified, not by how wrong the
measurement is.

The external review rejected the earlier "100 per era" precisely because the
route from gold counts to that conclusion was never shown
(`review_results_phase1b_sap_v3.md` Q5: required gold is not set by the width of
a single binomial rate; it depends on the counts in each true-pathway and each
misclassification direction, on pathway composition, and on each pathway's
outcome risk). This module is that route, made runnable.

Gold is sampled on the observed label, so what it estimates directly is
P(true | observed). The correction, however, is the classical matrix method on
P(observed | true), applied within outcome strata:

    n_y = Mᵀ m_y     →     m_y = (Mᵀ)⁻¹ n_y ,   M[t][o] = P(o | t)

The predictive-value form is not usable here, and the reason is worth stating
because it is easy to get wrong: applying P(true|observed) inside an outcome
stratum assumes the true-i members of an observed group carry that group's
average risk, which is exactly what the misclassification being corrected for
violates. Under that assumption the "correction" returns the uncorrected risk. A
unit test pins this down. P(observed|true) is recovered from P(true|observed)
and the observed composition by Bayes, so the sampling design is still honoured.

Outcome risks have to be assumed, since Phase 1b's outcomes cannot be looked at.
Phase 1's published risks are the primary input and hypothetical ranges are the
sensitivity, which is the choice the review left open ("a hypothetical risk range
for design purposes, or Phase 1's published risks").
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MAIN_PATHWAYS = ("j_club_academy", "high_school", "university")
REFERENCE = "j_club_academy"

# Jeffreys prior on each row, so a row of all-correct gold still carries
# uncertainty rather than asserting a zero misclassification rate.
PRIOR = 0.5


@dataclass(frozen=True)
class EraInputs:
    """Everything about one era that the correction needs."""

    observed_counts: dict[str, int]
    confusion: dict[str, dict[str, int]]  # observed -> true -> gold count
    true_risks: dict[str, float]

    def scaled_confusion(self, per_cell: int | None) -> dict[str, dict[str, int]]:
        """Confusion counts as they would be with `per_cell` verified per row.

        Scales each row up while holding its shape, which is the assumption a
        design calculation has to make: that more verification of the same strata
        finds the same mix of errors, only measured more precisely.
        """
        if per_cell is None:
            return self.confusion
        scaled = {}
        for observed, row in self.confusion.items():
            total = sum(row.values())
            if total == 0:
                scaled[observed] = dict(row)
                continue
            factor = per_cell / total
            scaled[observed] = {true: count * factor for true, count in row.items()}
        return scaled


def posterior_matrix(
    confusion: dict[str, dict[str, int]], rng: np.random.Generator
) -> dict[str, dict[str, float]]:
    """One draw of P(true | observed), row by row, from a Dirichlet posterior."""
    drawn = {}
    for observed in MAIN_PATHWAYS:
        row = confusion.get(observed, {})
        alpha = np.array([row.get(true, 0) + PRIOR for true in MAIN_PATHWAYS], dtype=float)
        drawn[observed] = dict(zip(MAIN_PATHWAYS, rng.dirichlet(alpha), strict=True))
    return drawn


def exposure_matrix(
    predictive: dict[str, dict[str, float]], observed_counts: dict[str, int]
) -> tuple[np.ndarray, np.ndarray]:
    """P(observed | true) and the true-category counts implied by the data.

    Bayes on the observed composition: the joint J[o][t] = n(o)·P(t|o) is what
    both quantities are read off, so the observed-label sampling design is kept.
    """
    joint = np.array(
        [[observed_counts[o] * predictive[o][t] for t in MAIN_PATHWAYS] for o in MAIN_PATHWAYS]
    )
    true_counts = joint.sum(axis=0)
    matrix = (joint / true_counts).T  # rows = true, columns = observed
    return matrix, true_counts


def observed_by_outcome(
    matrix: np.ndarray, true_counts: np.ndarray, true_risks: dict[str, float]
) -> tuple[np.ndarray, np.ndarray]:
    """Observed counts split by outcome, generated from the true risks."""
    risks = np.array([true_risks[t] for t in MAIN_PATHWAYS])
    cases = (true_counts * risks) @ matrix
    non_cases = (true_counts * (1 - risks)) @ matrix
    return cases, non_cases


def corrected_risks(
    cases: np.ndarray, non_cases: np.ndarray, matrix: np.ndarray
) -> dict[str, float]:
    """Risk per true pathway, by inverting the misclassification within outcome strata."""
    inverse = np.linalg.inv(matrix.T)
    true_cases = inverse @ cases
    true_non_cases = inverse @ non_cases
    total = true_cases + true_non_cases
    with np.errstate(divide="ignore", invalid="ignore"):
        risks = np.where(total > 0, true_cases / total, np.nan)
    return dict(zip(MAIN_PATHWAYS, risks, strict=True))


def risk_differences(risks: dict[str, float]) -> dict[str, float]:
    return {p: risks[p] - risks[REFERENCE] for p in MAIN_PATHWAYS if p != REFERENCE}


def did(era1: dict[str, float], era2: dict[str, float], pathway: str) -> float:
    """Difference in differences: era-1's pathway gap minus era-2's."""
    return risk_differences(era1)[pathway] - risk_differences(era2)[pathway]


def simulate(
    era1: EraInputs,
    era2: EraInputs,
    *,
    pathway: str = "university",
    per_cell: int | None = None,
    draws: int = 2000,
    seed: int = 20260718,
) -> np.ndarray:
    """Distribution of the corrected DID induced by gold sampling uncertainty.

    The data-generating matrix is the posterior mean, so the spread returned is
    what the finite gold sample adds and not a misspecification the design could
    not have avoided.
    """
    rng = np.random.default_rng(seed)
    confusion1 = era1.scaled_confusion(per_cell)
    confusion2 = era2.scaled_confusion(per_cell)

    generated = []
    for era, confusion in ((era1, confusion1), (era2, confusion2)):
        matrix, true_counts = exposure_matrix(mean_matrix(confusion), era.observed_counts)
        generated.append(observed_by_outcome(matrix, true_counts, era.true_risks))

    values = np.empty(draws)
    for index in range(draws):
        era_risks = []
        for era, confusion, (cases, non_cases) in (
            (era1, confusion1, generated[0]),
            (era2, confusion2, generated[1]),
        ):
            drawn, _ = exposure_matrix(
                posterior_matrix(confusion, rng), era.observed_counts
            )
            era_risks.append(corrected_risks(cases, non_cases, drawn))
        values[index] = did(era_risks[0], era_risks[1], pathway)
    return values


def mean_matrix(confusion: dict[str, dict[str, int]]) -> dict[str, dict[str, float]]:
    """Posterior mean of P(true | observed)."""
    matrix = {}
    for observed in MAIN_PATHWAYS:
        row = confusion.get(observed, {})
        alpha = np.array([row.get(true, 0) + PRIOR for true in MAIN_PATHWAYS], dtype=float)
        matrix[observed] = dict(zip(MAIN_PATHWAYS, alpha / alpha.sum(), strict=True))
    return matrix


def half_width(values: np.ndarray) -> float:
    """Half the 95% interval, in percentage points -- the resolution of the correction."""
    low, high = np.percentile(values, [2.5, 97.5])
    return (high - low) / 2 * 100
