"""Apply the SAP §1b-4 academy reclassification to resolved pathway labels.

The composite rule (§1b-3) decides *which* pathway a player took. This decides
whether a `j_club_academy` label really is one: the classifier's regex matches a
bare "ユース", so amateur and overseas youth setups land in the reference
category, and the reference category is what every other pathway's odds ratio is
measured against.

Shared by Phase 1 and Phase 1b on purpose. The review asked for one corrected
definition applied to both rather than the same error left in both, and the two
build scripts holding their own copies of a rule is what let Phase 1 keep stale
labels for as long as it did.
"""

from __future__ import annotations

import csv
from pathlib import Path

from jfa_talent_analysis.club_history_pathway import classify_institution, derive_pathway
from jfa_talent_analysis.j_club_registry import Club, classify_academy

QUEUE_PATH = Path("data/manual/academy_reclassification_queue.csv")
DECISIONS_PATH = Path("data/manual/academy_reclassification_decisions.csv")

# Verdicts that leave the label alone. institution_unknown means the career list
# names no institution to check, so there is no evidence to reclassify on -- it
# stays in the reference category and is reported as a residual limitation.
KEEP_ACADEMY = ("j_club_academy", "institution_unknown")


def _reviewed_from(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig") as handle:
        return {
            row["source_player_id"]: row["reviewed_category"].strip()
            for row in csv.DictReader(handle)
            if row.get("reviewed_category", "").strip()
        }


def load_reviewed(
    path: Path = QUEUE_PATH, decisions: Path = DECISIONS_PATH
) -> dict[str, str]:
    """Adjudicated categories by player id. Blank means "agree with auto_verdict".

    Read from the append-only decisions log first, then the working queue. The
    queue alone is not enough: applying a decision moves the label, which drops
    the row from the queue, which loses the decision on the next build -- 3242
    reverted from university to j_club_academy exactly that way.
    """
    return {**_reviewed_from(decisions), **_reviewed_from(path)}


def recorded_years(stints: list[dict[str, str]], institution: str) -> tuple[int, int] | None:
    """The stint's own from/to years, when the career list records them.

    Recorded years beat the window inferred from the birth year: 神戸ユース
    1997-1999 sits entirely inside Kobe's membership while the inferred window
    starts a year earlier and calls it a boundary case. Defined here rather than
    in the reporting script so the queue and the pipeline cannot disagree about
    which evidence they used -- they already did once, and two players silently
    reverted to boundary.
    """
    for row in stints:
        if row["institution"] != institution:
            continue
        start, end = row.get("from_year", ""), row.get("to_year", "")
        if start.isdigit():
            return (int(start), int(end) if end.isdigit() else int(start))
    return None


def reclassify(
    player_id: str,
    category: str,
    stints: list[dict[str, str]],
    birth_year: int | None,
    clubs: list[Club],
    reviewed: dict[str, str],
) -> tuple[str, str]:
    """Return the (category, reason) after the §1b-4 check.

    Only academy labels are touched; everything else passes through untouched.
    """
    if category != "j_club_academy":
        return category, ""

    if player_id in reviewed:
        return reviewed[player_id], "reviewed"

    institution = derive_pathway(stints, birth_year).institution
    if not institution:
        return category, "institution_unknown"
    if classify_institution(institution) not in ("j_club_academy", "jfa_academy", ""):
        # The pathway label itself is wrong rather than the club affiliation. No
        # unreviewed row should reach here, so leave it alone and let Gate A's
        # cell counts show it rather than guessing a replacement.
        return category, "pathway_label_error"
    verdict = classify_academy(
        institution, birth_year, clubs, recorded_years(stints, institution)
    )
    if verdict in KEEP_ACADEMY:
        return category, verdict
    return verdict, verdict
