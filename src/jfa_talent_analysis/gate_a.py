"""Gate A's measurement conditions, computed from gold (SAP §6b-3).

Everything here is a function of the gold label and the pipeline's label. No
outcome is involved, which is why Gate A can be settled while H1b-2 stays
blinded.

Two views of the same rows are produced on purpose. §6b-3 states its condition
as a Wilson 95% interval, which is a binomial statement about the rows actually
verified, so the gate is judged on unweighted counts exactly as pre-specified.
§6b-2b separately requires weighting back to the population by the inverse of
the sampling probability, because the holdout deliberately over-samples the
strata where an error would move the estimate most. Reporting only the first
would overstate how common the over-sampled strata's errors are; reporting only
the second would answer a question the gate did not ask.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

MAIN_PATHWAYS = ("j_club_academy", "high_school", "university")

# Below this many verified rows a cell is 判定不能, not 合格 (external review Q2).
MIN_CELL_FOR_VALIDITY = 10
VALIDITY_THRESHOLD = 0.80
SILENT_WRONG_GAP_TRIGGER_PP = 5.0


@dataclass(frozen=True)
class GoldPair:
    """One holdout row: what the gold says, and what the pipeline said."""

    worksheet_id: str
    era: str
    gold: str
    label: str
    human_reviewed: bool
    weight: float


def wilson_interval(hits: int, total: int) -> tuple[float, float]:
    """95% Wilson interval, which behaves at the 100%-correct cells this hits."""
    if total == 0:
        return (0.0, 1.0)
    z = 1.959963984540054
    phat = hits / total
    denominator = 1 + z**2 / total
    centre = (phat + z**2 / (2 * total)) / denominator
    spread = z * math.sqrt(phat * (1 - phat) / total + z**2 / (4 * total**2)) / denominator
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def confusion(pairs: list[GoldPair], era: str) -> dict[tuple[str, str], int]:
    """Counts of gold pathway -> assigned label, for the three main pathways."""
    matrix: dict[tuple[str, str], int] = defaultdict(int)
    for pair in pairs:
        if pair.era != era:
            continue
        matrix[(pair.gold, pair.label)] += 1
    return dict(matrix)


def per_pathway_validity(pairs: list[GoldPair]) -> dict[tuple[str, str, str], tuple[int, int]]:
    """Sensitivity and PPV per era and pathway, as (hits, total).

    Sensitivity conditions on the gold pathway, PPV on the assigned label: one
    asks how often a true academy player is found, the other how often an
    academy label is true, and it is the second that moves the reference
    category's baseline risk.
    """
    result: dict[tuple[str, str, str], tuple[int, int]] = {}
    for era in sorted({pair.era for pair in pairs}):
        rows = [pair for pair in pairs if pair.era == era]
        for pathway in MAIN_PATHWAYS:
            truth = [pair for pair in rows if pair.gold == pathway]
            assigned = [pair for pair in rows if pair.label == pathway]
            result[(era, "感度", pathway)] = (
                sum(1 for pair in truth if pair.label == pathway),
                len(truth),
            )
            result[(era, "PPV", pathway)] = (
                sum(1 for pair in assigned if pair.gold == pathway),
                len(assigned),
            )
    return result


def per_pathway_validity_weighted(
    pairs: list[GoldPair],
) -> dict[tuple[str, str, str], tuple[float, float]]:
    """The same quantities weighted back to the population (SAP §6b-2b)."""
    result: dict[tuple[str, str, str], tuple[float, float]] = {}
    for era in sorted({pair.era for pair in pairs}):
        rows = [pair for pair in pairs if pair.era == era]
        for pathway in MAIN_PATHWAYS:
            truth = [pair for pair in rows if pair.gold == pathway]
            assigned = [pair for pair in rows if pair.label == pathway]
            result[(era, "感度", pathway)] = (
                sum(pair.weight for pair in truth if pair.label == pathway),
                sum(pair.weight for pair in truth),
            )
            result[(era, "PPV", pathway)] = (
                sum(pair.weight for pair in assigned if pair.gold == pathway),
                sum(pair.weight for pair in assigned),
            )
    return result


def silent_wrong(pairs: list[GoldPair]) -> dict[str, tuple[int, int]]:
    """Labels that were wrong without any human ever being asked.

    A row a reviewer adjudicated is not silent even when it is wrong: the
    failure mode Gate A's condition 2 is about is the pipeline being
    confidently mistaken, and an era difference in *that* biases the era
    comparison.
    """
    result: dict[str, tuple[int, int]] = {}
    for era in sorted({pair.era for pair in pairs}):
        auto = [pair for pair in pairs if pair.era == era and not pair.human_reviewed]
        result[era] = (sum(1 for pair in auto if pair.label != pair.gold), len(auto))
    return result


def silent_wrong_weighted(pairs: list[GoldPair]) -> dict[str, tuple[float, float]]:
    result: dict[str, tuple[float, float]] = {}
    for era in sorted({pair.era for pair in pairs}):
        auto = [pair for pair in pairs if pair.era == era and not pair.human_reviewed]
        result[era] = (
            sum(pair.weight for pair in auto if pair.label != pair.gold),
            sum(pair.weight for pair in auto),
        )
    return result


def cell_state(hits: int, total: int) -> str:
    """合格 / 不合格 / 判定不能 for one validity cell, by §6b-3's own thresholds.

    §6b-3 fires on either outcome, but they are not the same finding and the
    2026-07-27 run conflated them. A cell so small that even a perfect score
    leaves the Wilson bound under 80% (roughly n < 16) says nothing about the
    label -- that is 判定不能. A cell large enough to have passed and did not is
    a measured failure -- 不合格. Reporting the second as "undetermined" would
    hide a label that is genuinely inaccurate behind a word about sample size.
    """
    if total < MIN_CELL_FOR_VALIDITY:
        return "判定不能"
    if wilson_interval(total, total)[0] < VALIDITY_THRESHOLD:
        return "判定不能"
    low, _ = wilson_interval(hits, total)
    return "合格" if low >= VALIDITY_THRESHOLD else "不合格"


def silent_wrong_gap_pp(counts: dict[str, tuple[int, int]]) -> float | None:
    """The era difference in silent-wrong rate, in percentage points."""
    rates = [wrong / total for wrong, total in counts.values() if total]
    if len(rates) < 2:
        return None
    return (max(rates) - min(rates)) * 100


def _gap(counts: dict[str, tuple[int, int]], added_wrong: dict[str, float], added: dict[str, int]):
    rates = {
        era: (wrong + added_wrong.get(era, 0.0)) / (total + added.get(era, 0))
        for era, (wrong, total) in counts.items()
        if total + added.get(era, 0)
    }
    return (max(rates.values()) - min(rates.values())) * 100


def unverified_sensitivity(
    counts: dict[str, tuple[int, int]], unverified: dict[str, int]
) -> dict[str, float]:
    """What the silent-wrong gap becomes if the rows gold could not verify differ.

    Validity is measured only where gold reached a verdict, and gold reaches one
    far less often in era1 -- the era whose sources are thinner. That is exactly
    the shape of missingness that can hide an era difference, so the gate's
    result is reported next to what it would take to overturn it, rather than
    on its own.
    """
    worst = _gap(counts, {era: float(n) for era, n in unverified.items()}, unverified)
    best = _gap(counts, {}, unverified)
    like_verified = _gap(
        counts,
        {
            era: unverified.get(era, 0) * (wrong / total if total else 0)
            for era, (wrong, total) in counts.items()
        },
        unverified,
    )
    return {"最良（全部正しい）": best, "検証済みと同率": like_verified, "最悪（全部誤り）": worst}


def wrong_needed_to_trigger(
    counts: dict[str, tuple[int, int]], unverified: dict[str, int], era: str
) -> int | None:
    """How many of one era's unverified rows must be wrong to fire condition 2."""
    others = {
        other: unverified.get(other, 0) * (wrong / total if total else 0)
        for other, (wrong, total) in counts.items()
        if other != era
    }
    for extra in range(unverified.get(era, 0) + 1):
        if _gap(counts, {**others, era: float(extra)}, unverified) > SILENT_WRONG_GAP_TRIGGER_PP:
            return extra
    return None
