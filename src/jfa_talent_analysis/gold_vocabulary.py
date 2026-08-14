"""The gold verdict vocabulary, in one place (SAP §6b-2b).

`jfa_academy` was added at v11 to `validate_gold_verdicts.py` and not to
`extract_verdict_rows.py`, which decides whether a line is a verdict by looking
at the category column. A JFA Academy row would have been dropped before the
validator ever saw it -- a rating paid for, silently discarded, and the batch
merely reported as short. The two lists have to be the same list.
"""

from __future__ import annotations

CATEGORIES = frozenset(
    {
        "j_club_academy",
        "jfa_academy",
        "high_school",
        "university",
        "other",
        "unknown",
    }
)

DETERMINATIONS = frozenset({"confirmed", "indeterminate", "unreachable"})

SOURCE_TYPES = frozenset({"official_club", "official_league", "school", "news", "other", ""})

VERDICT_COLUMNS = (
    "worksheet_id",
    "name_ja",
    "gold_pathway_category",
    "gold_final_institution",
    "determination",
    "evidence_url",
    "evidence_quote",
    "evidence_source_type",
    "rater",
    "researched_at",
    "minutes_spent",
    "note",
)
