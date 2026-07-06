from __future__ import annotations

import re
from dataclasses import dataclass

# Categories per docs/data_collection_plan.md's national_team_selections schema.
KNOWN_YOUTH_BRACKETS = {"15", "16", "17", "18", "19", "20", "23"}

U_NUMBER_RE = re.compile(r"U-?(\d{2})")
UNIVERSITY_SELECT_RE = re.compile(r"大学選抜")
A_TEAM_LINE_RE = re.compile(r"^日本代表$|A代表|国際Aマッチ")

# Negation/near-miss language: a name appearing next to one of these means the
# player was *not* actually selected (dropped from a squad, fell short of a
# call-up), the opposite of a confirmed selection. Wikipedia prose narrates both
# outcomes in the same paragraph (docs/national_team_pilot_2026-07-03.md's
# 中谷進之介 case: "2013 FIFA U-17ワールドカップのメンバーからは落選した"), so this
# has to be checked per-line/sentence, not just "does 代表 appear anywhere".
NEGATION_RE = re.compile(r"落選|選外|メンバー入りを逃|メンバーから外れ|選ばれなかった|に漏れ|入れなかった")

# "候補"(candidate/nominee) language records interest or a shortlist mention, not
# a confirmed squad call-up (docs/national_team_pilot_2026-07-03.md's 西村遥己
# case: "U-18日本代表候補に選出された" is deliberately not a "yes").
CANDIDATE_RE = re.compile(r"候補")

SENTENCE_SPLIT_RE = re.compile(r"[。\n]")


NATIONAL_TEAM_LABEL_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "wikipedia_title",
    "identity_check",
    "any_national_team_selection",
    "national_team_categories",
    "national_team_confidence",
    "national_team_reason",
]


@dataclass(frozen=True)
class NationalTeamClassification:
    any_national_team_selection: str  # "yes" / "no" / "unclear"
    categories: tuple[str, ...]
    confidence: str  # "high" or "needs_review"
    reason: str


def classify_national_team_selection(context: str) -> NationalTeamClassification:
    """Classify national-team selection evidence from Wikipedia national-team-context
    prose (see extract_national_team_context in sources/wikipedia.py).

    This is a heuristic first pass, not a final label. `categories` is best-effort:
    reliable for the clean list-style format many infobox-derived sections use
    (one "U-XX日本代表" mention per line) but not for dense narrative prose that
    mixes confirmed selections with near-misses in the same paragraph — any
    negation or candidate-only language anywhere in the context downgrades
    confidence to "needs_review" rather than trying to resolve it automatically.
    """
    sentences = [s for s in SENTENCE_SPLIT_RE.split(context) if s.strip()]

    categories: set[str] = set()
    any_yes = False
    any_unclear = False
    has_negation = False
    has_candidate = False

    for sentence in sentences:
        negated = bool(NEGATION_RE.search(sentence))
        candidate_only = bool(CANDIDATE_RE.search(sentence))
        # A negation/candidate word only matters here if the same sentence is
        # actually about a national-team-ish selection (e.g. "落選" describing a
        # *club* academy trial, 福森直也's "ガンバ大阪ジュニアユースのセレクション
        # を受けるが落選", says nothing about the national team) — otherwise it
        # would flag needs_review on an unrelated sentence elsewhere in the bio.
        sentence_is_relevant = "代表" in sentence or bool(UNIVERSITY_SELECT_RE.search(sentence))
        has_negation = has_negation or (negated and sentence_is_relevant)
        has_candidate = has_candidate or (candidate_only and sentence_is_relevant)

        if negated:
            continue

        # A bare "U-15"/"U-18" etc. commonly names a *club's own* youth age-group
        # team (e.g. "U-18には昇格せず" — failed to be promoted to the club's own
        # U-18 team), not a national-team call-up. Only count it here if "代表"
        # appears somewhere in the same sentence, the same disambiguation
        # PATHWAY_PRIORITY's J_CLUB_ACADEMY_RE avoids in the sibling classifier.
        matched_here = False
        if "代表" in sentence:
            for match in U_NUMBER_RE.finditer(sentence):
                bracket = match.group(1)
                if bracket in KNOWN_YOUTH_BRACKETS:
                    categories.add(f"U{int(bracket)}")
                else:
                    categories.add("other")
                matched_here = True

        if UNIVERSITY_SELECT_RE.search(sentence):
            categories.add("university")
            matched_here = True

        if A_TEAM_LINE_RE.search(sentence.strip()):
            categories.add("A")
            matched_here = True

        if matched_here:
            if candidate_only:
                any_unclear = True
            else:
                any_yes = True

    if any_yes:
        selection = "yes"
    elif any_unclear:
        selection = "unclear"
    else:
        selection = "no"

    needs_review = has_negation or has_candidate
    confidence = "needs_review" if needs_review else "high"
    reason = "negation_or_candidate_language_present" if needs_review else "clean_signal"

    return NationalTeamClassification(
        any_national_team_selection=selection,
        categories=tuple(sorted(categories)),
        confidence=confidence,
        reason=reason,
    )


NATIONAL_TEAM_REVIEW_QUEUE_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "tier",
    "wikipedia_title",
    "any_national_team_selection",
    "national_team_categories",
    "national_team_reason",
    "wikipedia_national_team_context",
    "reviewed_any_national_team_selection",
    "reviewed_categories",
    "reviewer_note",
]


def build_national_team_review_queue_rows(
    labeled_rows: list[dict[str, str]],
    context_by_player_id: dict[str, str],
    tier: str,
) -> list[dict[str, str]]:
    """Build review-queue rows for every needs_review labeled row, joining back
    the original Wikipedia context text (dropped from the labeled CSV to keep it
    small) so a reviewer doesn't have to open a second file per row."""
    return [
        {
            "source_player_id": row["source_player_id"],
            "name_ja": row["name_ja"],
            "name_en": row["name_en"],
            "tier": tier,
            "wikipedia_title": row["wikipedia_title"],
            "any_national_team_selection": row["any_national_team_selection"],
            "national_team_categories": row["national_team_categories"],
            "national_team_reason": row["national_team_reason"],
            "wikipedia_national_team_context": context_by_player_id.get(
                row["source_player_id"], ""
            ),
            "reviewed_any_national_team_selection": "",
            "reviewed_categories": "",
            "reviewer_note": "",
        }
        for row in labeled_rows
        if row["national_team_confidence"] == "needs_review"
    ]


def build_national_team_label_rows(
    candidate_rows: list[dict[str, str]], context_column: str
) -> list[dict[str, str]]:
    """Apply classify_national_team_selection to every identity-confirmed row.

    Rows whose identity_check is not "confirmed" are kept for coverage visibility
    but left unlabeled, the same convention build_pathway_label_rows uses.
    """
    return [build_national_team_label_row(row, context_column) for row in candidate_rows]


def build_national_team_label_row(row: dict[str, str], context_column: str) -> dict[str, str]:
    identity_check = row.get("identity_check", "")
    if identity_check != "confirmed":
        return {
            "source_player_id": row.get("source_player_id", ""),
            "name_ja": row.get("name_ja", ""),
            "name_en": row.get("name_en", ""),
            "wikipedia_title": row.get("wikipedia_title", ""),
            "identity_check": identity_check,
            "any_national_team_selection": "",
            "national_team_categories": "",
            "national_team_confidence": "",
            "national_team_reason": "identity_not_confirmed",
        }

    result = classify_national_team_selection(row.get(context_column, ""))
    return {
        "source_player_id": row.get("source_player_id", ""),
        "name_ja": row.get("name_ja", ""),
        "name_en": row.get("name_en", ""),
        "wikipedia_title": row.get("wikipedia_title", ""),
        "identity_check": identity_check,
        "any_national_team_selection": result.any_national_team_selection,
        "national_team_categories": "|".join(result.categories),
        "national_team_confidence": result.confidence,
        "national_team_reason": result.reason,
    }
