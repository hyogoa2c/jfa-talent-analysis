"""Design-based simulation of the holdout, replacing the scaled-counts version.

The v7 calculation scaled each observed-pathway row's existing confusion counts
up to the target size, which assumes the sample is drawn proportionally within
the row. The planned allocation does the opposite: it censuses the disagreement
strata and takes `both_agree` thinly, so the raw counts are not proportional and
the estimate is inverse-probability weighted. The review's point is that
re-weighting after collection gives a point estimate but not a pre-collection
guarantee, because the variance contributed by heavily weighted strata, the
finite-population correction inside censused strata, and indeterminate
adjudications never entered the calculation.

So this simulates the plan instead of approximating it: draw the sample the
allocation actually prescribes, decide each drawn player's true label from a
pre-specified error model, let some adjudications fail, build the weighted
confusion matrix, and carry it through to both DIDs. The spread across
replications is then the uncertainty the *planned design* produces.

The error model is per stratum rather than global, and for the disagreement
strata an error is not "some other pathway" but specifically the other candidate
the two procedures were arguing about, which the dataset stores.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from jfa_talent_analysis.gold_requirement import corrected_risks, did
from jfa_talent_analysis.gold_strata import ACADEMY, MAIN_PATHWAYS

# Fraction of sampled players whose true pathway cannot be settled even with
# external sources. They leave the confusion matrix and are reported, rather
# than being silently treated as agreements.
INDETERMINATE_RATE = 0.10  # planning assumption; the pilot measured 16.7% (SAP §6b-2b-ext)


@dataclass(frozen=True)
class Player:
    player_id: str
    era: str
    observed: str
    stratum: str
    prose: str
    club_list: str

    def alternative(self) -> str:
        """The pathway the other procedure claimed, when they disagreed.

        For disagreement strata an error means the rule chose the wrong one of
        two named candidates, so the alternative is known rather than arbitrary.
        """
        for candidate in (self.prose, self.club_list):
            if candidate in MAIN_PATHWAYS and candidate != self.observed:
                return candidate
        return ""


@dataclass(frozen=True)
class Scenario:
    """Per-stratum probability that the assigned label is wrong."""

    name: str
    error_rates: dict[str, float] = field(default_factory=dict)
    default_rate: float = 0.0

    def rate(self, stratum: str) -> float:
        return self.error_rates.get(stratum, self.default_rate)


def true_label(player: Player, scenario: Scenario, rng: np.random.Generator) -> str:
    """The player's true pathway under this scenario."""
    if rng.random() >= scenario.rate(player.stratum):
        return player.observed
    alternative = player.alternative()
    if alternative:
        return alternative
    others = [p for p in MAIN_PATHWAYS if p != player.observed]
    return others[int(rng.integers(len(others)))]


def draw_sample(
    population: list[Player], allocation: dict[tuple[str, str, str], int], rng: np.random.Generator
) -> list[tuple[Player, float]]:
    """Sampled players with their inverse sampling weights.

    A censused stratum has weight 1 and contributes no sampling variance, which
    is the point of censusing the strata where misclassification lives.
    """
    by_stratum: dict[tuple[str, str, str], list[Player]] = {}
    for player in population:
        by_stratum.setdefault((player.era, player.observed, player.stratum), []).append(player)

    sampled: list[tuple[Player, float]] = []
    for key, members in by_stratum.items():
        take = allocation.get(key, 0)
        if take <= 0:
            continue
        take = min(take, len(members))
        chosen = rng.choice(len(members), size=take, replace=False)
        weight = len(members) / take
        sampled.extend((members[index], weight) for index in chosen)
    return sampled


def weighted_confusion(
    sampled: list[tuple[Player, float]],
    scenario: Scenario,
    rng: np.random.Generator,
    era: str,
    indeterminate_rate: float = INDETERMINATE_RATE,
) -> tuple[dict[str, dict[str, float]], int, int]:
    """P(true | observed) from the drawn sample, weighted back to the population."""
    totals = {o: dict.fromkeys(MAIN_PATHWAYS, 0.0) for o in MAIN_PATHWAYS}
    adjudicated = indeterminate = 0
    for player, weight in sampled:
        if player.era != era:
            continue
        if rng.random() < indeterminate_rate:
            indeterminate += 1
            continue
        adjudicated += 1
        totals[player.observed][true_label(player, scenario, rng)] += weight

    predictive = {}
    for observed in MAIN_PATHWAYS:
        row = totals[observed]
        total = sum(row.values())
        if total == 0:
            predictive[observed] = {t: 1.0 if t == observed else 0.0 for t in MAIN_PATHWAYS}
        else:
            predictive[observed] = {t: row[t] / total for t in MAIN_PATHWAYS}
    return predictive, adjudicated, indeterminate


@dataclass
class Diagnostics:
    negative_counts: int = 0
    out_of_range: int = 0
    ill_conditioned: int = 0
    replications: int = 0
    indeterminate: int = 0


def simulate_design(
    population: list[Player],
    allocation: dict[tuple[str, str, str], int],
    observed_counts: dict[str, dict[str, int]],
    true_risks: dict[str, float],
    scenario: Scenario,
    *,
    draws: int = 1000,
    seed: int = 20260718,
    condition_limit: float = 1e4,
    indeterminate_rate: float = INDETERMINATE_RATE,
) -> tuple[dict[str, np.ndarray], Diagnostics]:
    """Corrected DID for both pathways, over replications of the planned design."""
    from jfa_talent_analysis.gold_requirement import exposure_matrix, observed_by_outcome

    rng = np.random.default_rng(seed)
    diagnostics = Diagnostics()
    results = {p: [] for p in MAIN_PATHWAYS if p != ACADEMY}

    # Truth used to generate the observed outcome counts: the scenario's own
    # error model, applied to the whole population rather than to a sample.
    generated = {}
    for era in ("era1", "era2"):
        truth_rng = np.random.default_rng(seed + 1)
        totals = {o: dict.fromkeys(MAIN_PATHWAYS, 0.0) for o in MAIN_PATHWAYS}
        for player in population:
            if player.era == era:
                totals[player.observed][true_label(player, scenario, truth_rng)] += 1.0
        predictive = {
            o: {t: (totals[o][t] / s if (s := sum(totals[o].values())) else 0.0) for t in MAIN_PATHWAYS}
            for o in MAIN_PATHWAYS
        }
        matrix, counts = exposure_matrix(predictive, observed_counts[era])
        generated[era] = observed_by_outcome(matrix, counts, true_risks)

    for _ in range(draws):
        diagnostics.replications += 1
        sampled = draw_sample(population, allocation, rng)
        era_risks = {}
        skip = False
        for era in ("era1", "era2"):
            predictive, _, indeterminate = weighted_confusion(
                sampled, scenario, rng, era, indeterminate_rate
            )
            diagnostics.indeterminate += indeterminate
            matrix, _ = exposure_matrix(predictive, observed_counts[era])
            if np.linalg.cond(matrix.T) > condition_limit:
                diagnostics.ill_conditioned += 1
                skip = True
                break
            cases, non_cases = generated[era]
            inverse = np.linalg.inv(matrix.T)
            if ((inverse @ cases) < 0).any() or ((inverse @ non_cases) < 0).any():
                diagnostics.negative_counts += 1
            risks = corrected_risks(cases, non_cases, matrix)
            values = np.array(list(risks.values()))
            if np.isnan(values).any() or (values < 0).any() or (values > 1).any():
                diagnostics.out_of_range += 1
                skip = True
                break
            era_risks[era] = risks
        if skip:
            continue
        for pathway in results:
            results[pathway].append(did(era_risks["era1"], era_risks["era2"], pathway))

    return {p: np.array(v) for p, v in results.items()}, diagnostics
