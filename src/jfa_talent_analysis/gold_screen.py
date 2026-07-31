"""Which single-rated rows need a second rater (SAP §6b-2b-screen, v12).

The reliability subsample caught rater A twice, both the same way: a player who
went club academy, then university, then pro, filed under the academy. The rule
it broke ("the last institution before turning pro") was already in the prompt,
and A's own notes named the university it had skipped -- 「法政大学経由で加入」,
「関西大学を経てプロ入り」. That is what makes the mistake screenable: the row
carries its own contradiction, so a second rater can be spent on exactly the rows
that show one instead of on all 305.

Only a later university can override an academy or a high-school label, so those
are the only categories worth screening; a `university` row has nothing above it
to be wrong about. Two things named 大学 are *not* a later stage and must not
flag: the institution already recorded, and a high school the university runs
(東海大学付属望星高校), where the rule already says the club or school side wins.

A flag is a request for a second opinion, never a verdict. False positives -- a
university the player attended *after* turning pro, which the quote lists anyway
-- cost one re-rating and are the side to err on.
"""

from __future__ import annotations

import re

# Categories a later university would override. Screening `university`, `other`
# or `unknown` rows would only re-rate rows the error mode cannot touch.
SCREENED_CATEGORIES = ("j_club_academy", "jfa_academy", "high_school")

# 大学付属○○高校: when 高 follows this closely, the 大学 names the school, not a
# stage after it. The window covers 付属望星高 (5) and 大学付属柏高 with room to
# spare, and stops well short of reaching the next career step.
AFFILIATED_SCHOOL_WINDOW = 6

_UNIVERSITY = re.compile(r"大学校?")

# Career lines abbreviate: 桐蔭横浜大, 法大. Requiring a delimiter after 大 keeps
# 大宮東高等学校 and 中京大中京高 (where 大 is followed by another name character)
# from matching.
_ABBREVIATED_UNIVERSITY = re.compile(r"(?<=[一-鿿])大(?=$|[)）、。，,\s→\-ー－/／|])")

_CONTEXT = 12


def _without_institution(text: str, institution: str) -> str:
    """The evidence with the recorded institution blanked out."""
    return text.replace(institution, " ") if institution.strip() else text


def _snippet(text: str, start: int, end: int) -> str:
    return text[max(0, start - _CONTEXT) : end + _CONTEXT].strip()


def screen_reason(category: str, institution: str, quote: str, note: str) -> str:
    """Why this row needs a second rater, or "" if nothing in it suggests one.

    The reason is written for the person reading the queue, not parsed.
    """
    if category not in SCREENED_CATEGORIES:
        return ""

    text = _without_institution(f"{quote} {note}", institution)
    for match in _UNIVERSITY.finditer(text):
        tail = text[match.end() : match.end() + AFFILIATED_SCHOOL_WINDOW]
        if "高" in tail:
            continue
        return f"大学への言及: …{_snippet(text, match.start(), match.end())}…"

    match = _ABBREVIATED_UNIVERSITY.search(text)
    if match:
        return f"大学（略記）への言及: …{_snippet(text, match.start(), match.end())}…"

    return ""


def screen_rows(rows: list[dict[str, str]]) -> list[tuple[dict[str, str], str]]:
    """Verdict rows that need a second rater, each with its reason."""
    flagged = []
    for row in rows:
        reason = screen_reason(
            row.get("gold_pathway_category", ""),
            row.get("gold_final_institution", ""),
            row.get("evidence_quote", ""),
            row.get("note", ""),
        )
        if reason:
            flagged.append((row, reason))
    return flagged
