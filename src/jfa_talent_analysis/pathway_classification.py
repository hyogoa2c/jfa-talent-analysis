from __future__ import annotations

import re
from dataclasses import dataclass

# Priority order mirrors the pilot's "terminal pre-professional institution" rule
# (docs/pathway_source_pilot_2026-07-03.md): a player is labeled by whichever of
# these stages is reached last before turning pro, so a later/higher stage always
# wins over an earlier one when both appear in the text.
PATHWAY_PRIORITY = ["university", "high_school", "jfa_academy", "j_club_academy", "grassroots_club"]

UNIVERSITY_RE = re.compile(r"大学")

# A bare "高校" immediately followed by a digit is a relative-age reference (e.g.
# "高校2年時", "高校3年次"), not a named school. "高校生" (e.g. "小学生〜高校生年代")
# is likewise an age-bracket phrase, not a school — the Phase 1b measurement-
# equivalence check (docs/measurement_equivalence_phase1b_2026-07-20.md, mechanism B)
# found 福島新太's "小学生〜高校生年代では下部組織に一貫所属" mislabeled high_school
# because 高校生 beat 下部組織 on priority. Both are excluded via the lookahead.
HIGH_SCHOOL_RE = re.compile(r"高等学校|高校(?![\d生])")

# A university-affiliated high school ("○○大学付属△△高校", "日本大学高校", "流通経済
# 大学付属柏高校") carries the substring 大学 that UNIVERSITY_RE spuriously reads as a
# university pathway (measurement-equivalence mechanism A: 三渡洲舞人, 野田恭平).
# The whole school-name span is normalized to "付属高校" before matching so it counts
# as high_school, not university. Contiguity (no sentence break inside) keeps this from
# spanning across an unrelated real university mention.
UNIVERSITY_AFFILIATED_HS_RE = re.compile(
    r"[^\s。、]{0,8}大学(?:[^\s。、]{0,6}(?:付属|附属|系属)[^\s。、]{0,6})?高(?:等学校|校)"
)

# Rising from a J-club's own youth team to its senior/top team ("トップチームに昇格")
# is definitional evidence of club-academy development (SAP §3 addendum 2026-07-20:
# simultaneous U-18-youth + affiliated-high-school attendance is j_club_academy, per
# the era-1/era-2 gold-standard consensus). A high-school recruit joins via 入団/加入,
# never 昇格, so this signal cleanly separates 籾谷真弘/數馬正浩 (youth→top) from a
# genuine high-school pathway.
PROMOTED_TO_TOP_TEAM_RE = re.compile(r"トップ(?:チーム)?(?:に|へ)?昇格")
# But not a *failed* promotion: "トップチームに昇格することはかなわなかった" (端山豪) means
# the player did NOT come up through the academy to the top team. Negation words within a
# short window after 昇格 cancel the signal.
PROMOTION_NEGATION_RE = re.compile(
    r"昇格[^。]{0,12}(?:かなわ|叶わ|できな|できず|ならな|ならず|至らな|至らず|果たせ"
    r"|なれず|逃し|せず|せぬ|しなかった|ぬまま)"
)

# "対○○大学戦" / "△△大学戦" is an opponent university team in a match report, not the
# player's own university (measurement-equivalence mechanism E: 野崎雅也's
# "宮崎産業経営大学戦"). The 大学 there is masked before university matching. "大学選手権"
# / "大学サッカー" (evidence of the player's own university play) is NOT masked — only 大学
# immediately followed by 戦.
OPPONENT_UNIVERSITY_RE = re.compile(r"[^\s。、]{0,10}大学(?=戦)")

# "複数の大学から誘いを受けるが（プロ入りを選んだ）" — a declined university offer that
# UNIVERSITY_RE reads as a university pathway (measurement-equivalence mechanism D:
# 鎌田大地). Detected as 大学 adjacent to invitation/decline language; routed to review
# rather than silently trusting the university label.
DECLINED_UNIVERSITY_RE = re.compile(
    r"大学[^。]{0,20}(?:誘い|オファー|誘われ|から誘|進学せず|進まず|蹴っ|断)"
)
JFA_ACADEMY_RE = re.compile(r"JFAアカデミー")

# A bare "U-18"/"U-15"-style age suffix usually names a J-club's own age-group team
# (e.g. "大分トリニータU-18"), but the same notation also appears in national-team
# youth-tournament mentions (e.g. "U-17日本代表", "AFC U-16選手権") that say nothing
# about a club academy. Exclude those by requiring the match not be immediately
# followed by a national-team/tournament word. "アカデミー" ("XXのアカデミー出身") is a
# very common phrasing for the same thing that a first full-scale run missed
# entirely — it accounted for a third of all "no institution keyword found" rows
# (see docs/pathway_source_pilot_2026-07-03.md's Labeling Phase section).
J_CLUB_ACADEMY_RE = re.compile(
    r"ユース|下部組織|アカデミー|U-?1[2-8](?!\s*(?:日本代表|選手権|ワールドカップ|代表))"
)
GRASSROOTS_RE = re.compile(r"少年団|スポーツ少年団|ジュニア(?!ユース)")

# A pathway spent entirely at foreign clubs (docs/pathway_source_pilot_2026-07-03.md's
# 伊藤遼哉 taxonomy-gap case: FC Zurich/Bayern Munich/Schalke youth, no domestic club
# or school at all) still trips J_CLUB_ACADEMY_RE on words like "ユース"/"下部組織"
# describing a *foreign* club's academy, which this project's 6-category taxonomy has
# no dedicated bucket for. Detect relocation-abroad language so that case is flagged
# for review instead of silently mislabeled as a J-League club academy.
OVERSEAS_RELOCATION_RE = re.compile(r"(?:移住|渡欧|渡米|渡韓|渡伊|渡独|渡仏|留学)")

CATEGORY_PATTERNS = {
    "university": UNIVERSITY_RE,
    "high_school": HIGH_SCHOOL_RE,
    "jfa_academy": JFA_ACADEMY_RE,
    "j_club_academy": J_CLUB_ACADEMY_RE,
    "grassroots_club": GRASSROOTS_RE,
}

SCHOOL_STAGES = {"university", "high_school"}
CLUB_STAGES = {"jfa_academy", "j_club_academy", "grassroots_club"}

# A school stage and a club-academy stage co-occur in a *large fraction* of real
# bios (most players' 来歴 prose names both a childhood/JHS club and a high school
# or university in normal chronological order — see docs/pathway_source_pilot_
# 2026-07-03.md's 森重真人/稲垣祥/etc. cases, all resolved correctly by the plain
# priority rule). Flagging every such co-occurrence for review would swamp a human
# reviewer with mostly-correct labels. The pilot's one real miss (7493 西川周作) had
# a narrower, distinctive signature: the school was framed as incidental
# accommodation for a club-academy stay he'd *already* joined (dormitory living,
# arranged because of distance from the academy's practice ground) rather than an
# independent recruitment — so only flag co-occurrence when that specific framing
# language is present.
INCIDENTAL_SCHOOLING_RE = re.compile(r"寮生活|寮に入|誘われ")

# --- Guards added by the Phase 1b era-1 pilot (2026-07-19). Pre-2014-only players'
# articles are dominated by post-playing careers, which created three silent-wrong
# modes on the 20-player pilot that Phase 1's golden 22 never hit
# (docs/pre2014_pathway_pilot_2026-07-19.md):

# (1) Coaching-role mentions ("U-15監督に就任", "アカデミースタッフ") matched
# J_CLUB_ACADEMY_RE even though they describe the player's later job, not their own
# development. Mask the keyword when a staff-role noun follows within a few chars.
COACHING_ROLE_MASK_RE = re.compile(
    r"(?:ジュニアユース|ユース|アカデミー|スクール|U-?1[2-8])"
    r"(?:の)?(?:監督|コーチ|スタッフ|ダイレクター|ディレクター|GM)"
)

# (2) University entered AFTER first pro entry (released young, then enrolled — a
# common early-2000s career shape: 石原卓 2007 Marinos -> released -> 2009 中京大学).
# When both a pro-entry year and a later university-entry year are present, the
# university is not the pre-professional pathway; flag instead of trusting priority.
PRO_ENTRY_YEAR_RE = re.compile(r"(\d{4})年[^。]{0,25}?(?:入団|加入|昇格|プロ契約)")
UNIVERSITY_ENTRY_YEAR_RE = re.compile(r"(\d{4})年[^。]{0,20}?大学[^。]{0,10}?(?:入学|進学|入部)")

# (3) Dual enrollment written as ユース（○○高校）: the parenthesized school is the
# academy's partner school, not an independent high-school pathway (吉澤佑哉's
# 鹿島アントラーズユース（鹿島高校）). The priority rule alone picks high_school here.
YOUTH_DUAL_ENROLLMENT_RE = re.compile(r"ユース[（(][^（）()]{0,20}高(?:等学校|校)[）)]")


PATHWAY_LABEL_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "wikipedia_title",
    "identity_check",
    "pathway_category",
    "pathway_confidence",
    "pathway_matched_categories",
    "pathway_reason",
]


@dataclass(frozen=True)
class PathwayClassification:
    pathway_category: str
    confidence: str  # "high" or "needs_review"
    matched_categories: tuple[str, ...]
    reason: str


def classify_pathway_category(context: str) -> PathwayClassification:
    """Classify a player's terminal pre-professional pathway stage from Wikipedia
    pathway-context prose (see extract_pathway_context in sources/wikipedia.py).

    This is a heuristic first pass, not a final label: it follows the pilot's
    terminal-institution priority rule (docs/pathway_source_pilot_2026-07-03.md)
    but flags confidence="needs_review" when a school-stage signal (university/
    high_school) co-occurs with a club-stage signal (j_club_academy/jfa_academy/
    grassroots_club) *and* incidental-schooling framing language is present, since
    that combination is what the pilot found actually needs a human to read the
    surrounding sentence — plain co-occurrence alone is the normal, correctly-
    resolved case for most bios and is not flagged.
    """
    # Strip coaching-role phrases first so a later staff job never counts as evidence
    # of the player's own development (guard 1, era-1 pilot).
    context = COACHING_ROLE_MASK_RE.sub("", context)
    # Normalize university-affiliated high-school names so their 大学 substring does not
    # register as a university pathway (measurement-equivalence mechanism A).
    context = UNIVERSITY_AFFILIATED_HS_RE.sub("付属高校", context)
    # Drop opponent-university team names in match reports ("○○大学戦"), mechanism E.
    context = OPPONENT_UNIVERSITY_RE.sub("対戦相手", context)

    matched = tuple(name for name in PATHWAY_PRIORITY if CATEGORY_PATTERNS[name].search(context))

    if not matched:
        return PathwayClassification(
            pathway_category="unknown",
            confidence="needs_review" if context.strip() else "high",
            matched_categories=(),
            reason="no_institution_keyword_found",
        )

    best = matched[0]
    has_school_stage = any(name in SCHOOL_STAGES for name in matched)
    has_club_stage = any(name in CLUB_STAGES for name in matched)

    # Definitional rule (SAP §3 addendum 2026-07-20): a player promoted from a J-club's
    # own youth to its top team is j_club_academy, even when a high school co-occurs
    # (simultaneous U-18-youth + affiliated-school attendance). This overrides the plain
    # priority order, which would otherwise pick the co-occurring high_school/university.
    if (
        best != "j_club_academy"
        and "j_club_academy" in matched
        and PROMOTED_TO_TOP_TEAM_RE.search(context)
        and not PROMOTION_NEGATION_RE.search(context)
    ):
        # When university competes with the youth+promotion signal, the flip is only
        # ~40% correct on the held-out gold (youth→did-not-promote→university→pro is
        # common and hard to separate from youth→top by phrasing alone). Route to review
        # instead of auto-labeling; auto-flip only when the competitor is high_school,
        # where the gold sample found the flip reliably correct.
        if "university" in matched:
            return PathwayClassification(
                pathway_category="university",
                confidence="needs_review",
                matched_categories=matched,
                reason="youth_promotion_vs_university_ambiguous",
            )
        return PathwayClassification(
            pathway_category="j_club_academy",
            confidence="high",
            matched_categories=matched,
            reason="youth_to_top_team_promotion",
        )

    # A declined university offer ("大学から誘いを受けるが（プロ入り）") makes the
    # university label suspect (mechanism D). Route to review rather than trust it.
    if best == "university" and DECLINED_UNIVERSITY_RE.search(context):
        return PathwayClassification(
            pathway_category=best,
            confidence="needs_review",
            matched_categories=matched,
            reason="possible_declined_university_offer",
        )

    if best == "university":
        pro_years = [int(m.group(1)) for m in PRO_ENTRY_YEAR_RE.finditer(context)]
        university_years = [
            int(m.group(1)) for m in UNIVERSITY_ENTRY_YEAR_RE.finditer(context)
        ]
        if pro_years and university_years and min(pro_years) < max(university_years):
            return PathwayClassification(
                pathway_category=best,
                confidence="needs_review",
                matched_categories=matched,
                reason="university_entry_after_pro_entry",
            )

    # "○○ユース（△△高校）" pairs a J-club U-18 youth team with its partner high school:
    # per the SAP §3 addendum this is j_club_academy, not high_school (junior youth pairs
    # with a middle school, so a high school inside the paren means U-18-level youth).
    if best == "high_school" and YOUTH_DUAL_ENROLLMENT_RE.search(context):
        return PathwayClassification(
            pathway_category="j_club_academy",
            confidence="high",
            matched_categories=matched,
            reason="youth_dual_enrollment_school",
        )

    if has_school_stage and has_club_stage and INCIDENTAL_SCHOOLING_RE.search(context):
        return PathwayClassification(
            pathway_category=best,
            confidence="needs_review",
            matched_categories=matched,
            reason="possible_incidental_schooling_around_club_academy",
        )

    if not has_school_stage and OVERSEAS_RELOCATION_RE.search(context):
        return PathwayClassification(
            pathway_category=best,
            confidence="needs_review",
            matched_categories=matched,
            reason="overseas_relocation_language_no_domestic_institution",
        )

    return PathwayClassification(
        pathway_category=best,
        confidence="high",
        matched_categories=matched,
        reason="single_stage_tier_matched",
    )


PATHWAY_REVIEW_QUEUE_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "tier",
    "wikipedia_title",
    "pathway_category",
    "pathway_matched_categories",
    "pathway_reason",
    "wikipedia_pathway_context",
    "reviewed_pathway_category",
    "reviewer_note",
]


def build_pathway_review_queue_rows(
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
            "pathway_category": row["pathway_category"],
            "pathway_matched_categories": row["pathway_matched_categories"],
            "pathway_reason": row["pathway_reason"],
            "wikipedia_pathway_context": context_by_player_id.get(row["source_player_id"], ""),
            "reviewed_pathway_category": "",
            "reviewer_note": "",
        }
        for row in labeled_rows
        if row["pathway_confidence"] == "needs_review"
    ]


def build_pathway_label_rows(
    candidate_rows: list[dict[str, str]], context_column: str
) -> list[dict[str, str]]:
    """Apply classify_pathway_category to every identity-confirmed candidate row.

    Rows whose identity_check is not "confirmed" (see
    scripts/verify_wikipedia_candidate_identity.py) are kept for coverage visibility
    but left unlabeled, the same "keep every row, blank what wasn't resolved"
    convention outcomes.py uses for moved_overseas.
    """
    return [build_pathway_label_row(row, context_column) for row in candidate_rows]


def build_pathway_label_row(row: dict[str, str], context_column: str) -> dict[str, str]:
    identity_check = row.get("identity_check", "")
    if identity_check != "confirmed":
        return {
            "source_player_id": row.get("source_player_id", ""),
            "name_ja": row.get("name_ja", ""),
            "name_en": row.get("name_en", ""),
            "wikipedia_title": row.get("wikipedia_title", ""),
            "identity_check": identity_check,
            "pathway_category": "",
            "pathway_confidence": "",
            "pathway_matched_categories": "",
            "pathway_reason": "identity_not_confirmed",
        }

    result = classify_pathway_category(row.get(context_column, ""))
    return {
        "source_player_id": row.get("source_player_id", ""),
        "name_ja": row.get("name_ja", ""),
        "name_en": row.get("name_en", ""),
        "wikipedia_title": row.get("wikipedia_title", ""),
        "identity_check": identity_check,
        "pathway_category": result.pathway_category,
        "pathway_confidence": result.confidence,
        "pathway_matched_categories": "|".join(result.matched_categories),
        "pathway_reason": result.reason,
    }
