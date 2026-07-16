from __future__ import annotations

from dataclasses import dataclass


# Map a normalized institution name to the development stage it represents, so a
# player's exposures can be filtered to the stage that matches their terminal
# pathway_category. Mirrors the stage logic used when building the university
# target list (a name containing 大学 that isn't a high school is a university).
def institution_stage(normalized_institution: str) -> str:
    if "大学" in normalized_institution and "高等学校" not in normalized_institution:
        return "university"
    if "高等学校" in normalized_institution or "高校" in normalized_institution:
        return "high_school"
    return "j_club_academy"


# pathway_category values (from player_pathway_outcomes.csv) mapped to the
# institution stage that represents that pathway. jfa_academy and
# grassroots_club have no coach-tenure coverage and are treated as j_club_academy-
# adjacent only in that they are not university/high_school; they will rarely
# match and that is expected (documented as absence, not error).
PATHWAY_TO_STAGE = {
    "university": "university",
    "high_school": "high_school",
    "j_club_academy": "j_club_academy",
    "jfa_academy": "j_club_academy",
    "grassroots_club": "j_club_academy",
}


def year_overlap(
    stint_from: int | None,
    stint_to: int | None,
    tenure_from: int | None,
    tenure_to: int | None,
) -> int:
    """Number of overlapping years between a player's stint and a coach's
    tenure. Only measurable when BOTH the stint and the tenure contribute at
    least one year bound; if either side is fully yearless (e.g. a yearless
    childhood-club stint, per club_history_extraction) the overlap can't be
    computed and is counted as a weak (present-but-unmeasured) overlap of 1 —
    enough to rank a year-known overlap above a year-unknown one without
    letting the unknown side's own span masquerade as overlap."""
    stint_has_bound = stint_from is not None or stint_to is not None
    tenure_has_bound = tenure_from is not None or tenure_to is not None
    if not (stint_has_bound and tenure_has_bound):
        return 1
    lo_candidates = [y for y in (stint_from, tenure_from) if y is not None]
    hi_candidates = [y for y in (stint_to, tenure_to) if y is not None]
    if not lo_candidates or not hi_candidates:
        return 1  # both ranges open on the same side; overlap present but unbounded
    return max(0, min(hi_candidates) - max(lo_candidates) + 1)


# Head-coach roles outrank director/assistant roles when picking the single
# "primary" development coach among equally-overlapping candidates: the player's
# development is most directly attributable to whoever ran the team on the field.
ROLE_PRIORITY = {
    "監督": 3,
    "アカデミーダイレクター兼監督": 3,
    "育成部長兼監督": 3,
    "監督代行": 2,
    "ヘッドコーチ": 2,
    "総監督": 1,
}


def role_rank(role_type: str) -> int:
    return ROLE_PRIORITY.get(role_type, 0)


@dataclass(frozen=True)
class PrimaryDevCoach:
    coach_name: str
    institution: str
    role_type: str
    overlap_years: int


def select_primary_dev_coach(
    stage_exposures: list[dict[str, str]],
) -> PrimaryDevCoach | None:
    """Pick the single most attributable development coach from a player's
    stage-matching exposures: greatest stint×tenure year overlap, breaking ties
    toward the head-coach role, then (stably) the first seen. Returns None if
    the player has no exposure at their pathway stage."""
    if not stage_exposures:
        return None

    def sort_key(exposure: dict[str, str]) -> tuple[int, int]:
        overlap = year_overlap(
            _int(exposure["stint_from_year"]),
            _int(exposure["stint_to_year"]),
            _int(exposure["tenure_from_year"]),
            _int(exposure["tenure_to_year"]),
        )
        return (overlap, role_rank(exposure["role_type"]))

    best = max(stage_exposures, key=sort_key)
    overlap = year_overlap(
        _int(best["stint_from_year"]),
        _int(best["stint_to_year"]),
        _int(best["tenure_from_year"]),
        _int(best["tenure_to_year"]),
    )
    return PrimaryDevCoach(
        coach_name=best["coach_name"],
        institution=best["normalized_institution"],
        role_type=best["role_type"],
        overlap_years=overlap,
    )


def _int(value: str) -> int | None:
    return int(value) if value else None
