from __future__ import annotations

import math

BIRTH_COHORT_BOUNDS = [1990, 1995, 2000, 2005]

# U15-U19 selection happens at an age that essentially always precedes (or is
# concurrent with, at the very latest) a player's first-team pro debut, so it
# works as an "was this player already recognized as elite talent before/
# around turning pro" signal independent of the pathway/J1-attainment outcomes
# themselves. U20+ and A are deliberately excluded: those categories are
# frequently awarded *because of* strong J1/pro performance, which would make
# them a post-treatment variable (a consequence of the outcome, not a cause
# available for control) rather than an early-ability signal.
YOUTH_NATIONAL_TEAM_CATEGORIES = {"U15", "U16", "U17", "U18", "U19"}


def has_youth_national_team_selection(national_team_categories: str) -> bool:
    """True if national_team_categories (a "|"-joined string, e.g. "U17|A")
    contains any U15-U19 category — see YOUTH_NATIONAL_TEAM_CATEGORIES."""
    if not national_team_categories:
        return False
    categories = set(national_team_categories.split("|"))
    return bool(categories & YOUTH_NATIONAL_TEAM_CATEGORIES)


def parse_birth_year(birth_date: str) -> int | None:
    """Parse a "YYYY/MM/DD" birth_date into a birth year, or None if blank/malformed."""
    if not birth_date:
        return None
    year_text = birth_date.split("/")[0]
    try:
        return int(year_text)
    except ValueError:
        return None


def birth_cohort(birth_year: int | None) -> str:
    """Bucket a birth year into the cohort labels used throughout this analysis.

    Bounds follow docs/data_collection_plan.md's sensitivity-cohort boundaries
    (1990/1995/2000, with 2005 added since the primary analytical cohort
    definition itself uses 2005 as a U-15-in-2005 cutoff).
    """
    if birth_year is None:
        return "unknown"
    if birth_year < BIRTH_COHORT_BOUNDS[0]:
        return f"<{BIRTH_COHORT_BOUNDS[0]}"
    for lower, upper in zip(BIRTH_COHORT_BOUNDS, BIRTH_COHORT_BOUNDS[1:], strict=False):
        if lower <= birth_year < upper:
            return f"{lower}-{upper - 1}"
    return f"{BIRTH_COHORT_BOUNDS[-1]}+"


def wilson_confidence_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score confidence interval for a binomial proportion.

    More reliable than a normal approximation for the small-n pathway
    categories (jfa_academy, grassroots_club) that appear throughout this
    project's descriptive tables.
    """
    if n == 0:
        return (0.0, 0.0)
    phat = successes / n
    denominator = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    spread = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * n)) / n)
    lower = (center - spread) / denominator
    upper = (center + spread) / denominator
    return (max(0.0, lower), min(1.0, upper))
