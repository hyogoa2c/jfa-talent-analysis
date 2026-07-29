"""Derive pathway_category from the Wikipedia 所属クラブ career list.

The prose classifier reads 来歴-style sections only (PRE_PRO_SECTION_HEADINGS),
so it never sees the `== 所属クラブ ==` list even though that list is usually the
cleanest statement of a player's schooling. Reviewers had been consulting it by
hand; this derives the same reading uniformly.

The list is ordered chronologically, which is the signal the prose lacks: the
pathway is the last development institution appearing *before* the first
professional entry. That ordering is what separates "youth -> university -> pro"
from "youth -> pro -> university" (Nakamachi: Takasaki HS -> Shonan 2004 -> Keio
2008, where the prose alone reads as a university pathway).

This module derives a candidate label only. Whether it is trusted, used to fill
unknowns, or merely cross-checked against the prose classifier is a measurement
decision recorded in the SAP, not something decided here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from jfa_talent_analysis.pathway_classification import (
    GRASSROOTS_RE,
    HIGH_SCHOOL_RE,
    J_CLUB_ACADEMY_RE,
    JFA_ACADEMY_RE,
    UNIVERSITY_AFFILIATED_HS_RE,
    UNIVERSITY_RE,
)

# Stages below high school say nothing about the final pre-professional pathway.
PRE_HIGH_SCHOOL_RE = re.compile(r"小学校|中学校|少年団|ジュニアユース|Jr\.?ユース|U-?1[2-5]")

# A pro contract before this age does not happen; entries this early are
# childhood clubs that carry a year, not professional entries.
MIN_PRO_ENTRY_AGE = 16


# Plausible age at entry for each stage, year-granular so the bounds are loose.
# JFA Academy and some club academies intake at U-13, hence the low floor; the
# upper bounds allow repeated years and late entry.
ENTRY_AGE_WINDOWS = {
    "high_school": (14, 19),
    "university": (17, 24),
    "j_club_academy": (12, 19),
    "jfa_academy": (12, 19),
    "grassroots_club": (6, 19),
}


@dataclass(frozen=True)
class StintPathway:
    pathway_category: str
    confidence: str
    reason: str
    institution: str


def entry_age_plausible(category: str, from_year: str, birth_year: int | None) -> bool | None:
    """Does the entry year fit the stage's age window? None when uncheckable.

    The club list carries years, so unlike the prose path this can be asserted
    at all. On the 2014-2025 sample it flags essentially nothing, which is the
    point: it is a parse-quality signal that works on every row rather than only
    the handful with a gold label, and era-1's list formatting is the thing we
    cannot otherwise check at scale.
    """
    window = ENTRY_AGE_WINDOWS.get(category)
    if window is None or birth_year is None or not from_year.isdigit():
        return None
    low, high = window
    return low <= int(from_year) - birth_year <= high


def classify_institution(name: str) -> str:
    """Map one institution name to a pathway category, or "" if it is not one.

    Order matters: a university-affiliated high school carries 大学 in its name,
    so it has to be recognised before the university test (the same mechanism-A
    problem the prose classifier fixes by masking).
    """
    if JFA_ACADEMY_RE.search(name):
        return "jfa_academy"
    if UNIVERSITY_AFFILIATED_HS_RE.search(name) or HIGH_SCHOOL_RE.search(name):
        return "high_school"
    if UNIVERSITY_RE.search(name):
        return "university"
    if J_CLUB_ACADEMY_RE.search(name):
        return "j_club_academy"
    if GRASSROOTS_RE.search(name):
        return "grassroots_club"
    return ""


def is_developmental(name: str) -> bool:
    return bool(classify_institution(name)) and not PRE_HIGH_SCHOOL_RE.search(name)


def first_pro_index(stints: list[dict[str, str]], birth_year: int | None) -> int | None:
    """Index of the first entry that is a professional club, if identifiable.

    Excluded: development institutions, and 特別指定/2種登録 rows, which are
    pro-club registrations held *during* the youth years and would otherwise cut
    the career at the wrong point.
    """
    for index, stint in enumerate(stints):
        if stint.get("registration_formality") == "1":
            continue
        name = stint["institution"]
        if is_developmental(name) or PRE_HIGH_SCHOOL_RE.search(name):
            continue
        year = stint.get("from_year", "")
        if not year.isdigit():
            continue
        if birth_year is not None and int(year) - birth_year < MIN_PRO_ENTRY_AGE:
            continue
        return index
    return None


def derive_pathway(stints: list[dict[str, str]], birth_year: int | None) -> StintPathway:
    """Last development institution before the first professional entry."""
    if not stints:
        return StintPathway("", "no_data", "no_club_history", "")

    ordered = sorted(stints, key=lambda s: int(s["line_index"]))
    cut = first_pro_index(ordered, birth_year)
    before = ordered[:cut] if cut is not None else ordered

    developmental = [s for s in before if is_developmental(s["institution"])]
    if not developmental:
        # Either the list starts at the professional career, or every entry is
        # junior-high or earlier. Both are absence of evidence, not high_school.
        return StintPathway(
            "",
            "no_data",
            "no_development_stage_before_pro" if cut is not None else "no_development_stage",
            "",
        )

    last = developmental[-1]
    category = classify_institution(last["institution"])
    plausible = entry_age_plausible(category, last.get("from_year", ""), birth_year)
    if plausible is False:
        # The stage and the year disagree about how old the player was, so
        # either the list was mis-parsed or it is not this player's article.
        return StintPathway(category, "needs_review", "entry_age_implausible", last["institution"])
    return StintPathway(
        category,
        "high" if cut is not None else "needs_review",
        "last_stage_before_pro_entry" if cut is not None else "pro_entry_not_identified",
        last["institution"],
    )


def derive_pathway_labels(
    stint_rows: list[dict[str, str]], birth_years: dict[str, int | None]
) -> dict[str, StintPathway]:
    """Run the derivation over every player present in the stint table.

    Players with no parsed club list are absent from the result rather than
    carrying a blank: "we never saw a list" and "the list showed no development
    stage" are different states, and Gate A reports them separately.
    """
    by_player: dict[str, list[dict[str, str]]] = {}
    for row in stint_rows:
        by_player.setdefault(row["source_player_id"], []).append(row)
    return {
        player_id: derive_pathway(rows, birth_years.get(player_id))
        for player_id, rows in by_player.items()
    }
