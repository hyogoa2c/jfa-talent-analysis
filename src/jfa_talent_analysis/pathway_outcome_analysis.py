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


def youth_category_count(national_team_categories: str) -> int:
    """How many distinct U15-U19 categories the player was selected for (0-5).

    A finer early-ability signal than the binary has_youth_national_team_
    selection: a player called up across three youth age brackets was more
    consistently rated than one with a single U18 camp appearance."""
    if not national_team_categories:
        return 0
    categories = set(national_team_categories.split("|"))
    return len(categories & YOUTH_NATIONAL_TEAM_CATEGORIES)


# Sentinel age for "never selected at youth level" in earliest_youth_selection_age.
# Tree models split numerically, so any value clearly above the real 15-19 range
# works; 25 keeps the column readable in plots without stretching the axis.
NO_YOUTH_SELECTION_AGE = 25


def earliest_youth_selection_age(national_team_categories: str) -> int:
    """The age bracket of the player's EARLIEST U15-U19 selection (15-19), or
    NO_YOUTH_SELECTION_AGE if never selected at youth level.

    Earlier first selection is a stronger early-ability signal: a U15 call-up
    means the player was already nationally rated at 14-15, while a first
    call-up at U19 can reflect later development."""
    if not national_team_categories:
        return NO_YOUTH_SELECTION_AGE
    categories = set(national_team_categories.split("|"))
    ages = [int(cat[1:]) for cat in categories & YOUTH_NATIONAL_TEAM_CATEGORIES]
    return min(ages) if ages else NO_YOUTH_SELECTION_AGE


def has_a_team_selection(national_team_categories: str) -> bool:
    """True if the player was ever selected for the senior A team.

    Used as the national-team OUTCOME in exploratory modeling instead of
    any_national_team_selection: the youth-selection features above are derived
    from the same national_team_categories string, so predicting "any selection"
    with them would leak the outcome into the features (a youth-only selection
    satisfies both). A-team selection is temporally downstream of the youth
    signals, making it a legitimate prediction target."""
    if not national_team_categories:
        return False
    return "A" in national_team_categories.split("|")


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
