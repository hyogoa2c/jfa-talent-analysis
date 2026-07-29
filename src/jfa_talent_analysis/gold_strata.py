"""Sampling strata for the holdout gold (SAP §6b-2b, revised at v8).

The v7 strata were read off `pathway_category_source` alone, and that lost the
direction the review cares most about. The composite rule sends
`prose=j_club_academy → club=university/high_school` to human review, so after
adjudication those rows carry source `human_reviewed` — all 21 of them — and the
`disagree_academy` stratum built from `club_list_over_prose` contained none of
the direction that empties the reference category. Strata are therefore defined
from the *stored inputs* to the rule (prose label, club-list label, final label),
not from its output source.

`institution_unknown` gets its own stratum for the same reason: those rows keep
the academy label because no institution could be identified, which makes them
the main residual uncertainty in the reference category, and under the v7 strata
they scattered across `prose_only` and `human_reviewed` where nothing guaranteed
they would be sampled at all.
"""

from __future__ import annotations

MAIN_PATHWAYS = ("j_club_academy", "high_school", "university")
ACADEMY = "j_club_academy"

# Ordered by how much a misclassification there would move the estimate, which
# is also the order the allocation censuses them in.
STRATA = (
    "academy_out",
    "academy_in",
    "institution_unknown",
    "disagree_other",
    "club_list_only",
    "prose_only",
    "human_reviewed_other",
    "both_agree",
)


def _label(value: str) -> str:
    """A pathway claim, with "unknown" read as no claim."""
    return "" if value == "unknown" else value


def stratum(row: dict[str, str], institution_unknown: set[str]) -> str:
    """Which sampling stratum an eligible, main-pathway row belongs to.

    Priority order, not a set of independent tests: a row that both disagrees and
    was reviewed belongs in the disagreement stratum, since that is what makes it
    informative about misclassification.
    """
    if row["source_player_id"] in institution_unknown:
        return "institution_unknown"

    prose = _label(row.get("pathway_prose_category", ""))
    club = _label(row.get("pathway_club_list_category", ""))
    final = row["pathway_category"]

    if prose and club and prose != club:
        if prose == ACADEMY and final != ACADEMY:
            return "academy_out"
        if ACADEMY in (prose, club, final):
            return "academy_in"
        return "disagree_other"
    if club and not prose:
        return "club_list_only"
    if prose and not club:
        return "prose_only"
    if row["pathway_category_source"] == "human_reviewed":
        return "human_reviewed_other"
    return "both_agree"


def load_institution_unknown(rows: list[dict[str, str]]) -> set[str]:
    """Ids whose academy label rests on no identifiable institution (SAP §1b-4)."""
    return {
        row["source_player_id"]
        for row in rows
        if row.get("auto_verdict") == "institution_unknown"
    }
