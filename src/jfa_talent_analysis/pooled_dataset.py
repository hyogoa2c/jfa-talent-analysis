"""Pooled 1999-2025 analysis dataset (Phase 1b SAP §0/§3/§5).

Phase 1's universe is players observed in 2014-2025, which conditions the
born 1981-89 cohort on having *survived* into the 2014 window. The 1999-2013
backfill removes that condition, so the pooled dataset is what era-1 estimates
have to be built from.

This module only assembles the dataset. It deliberately contains no
pathway-by-outcome estimation: until the external review answers Q6 of
docs/review_request_phase1_corrigendum.md, looking at the pathway x era x
outcome table would spend the confirmatory status of H1b-2.
"""

from __future__ import annotations

from collections import defaultdict

from jfa_talent_analysis.club_history_pathway import StintPathway
from jfa_talent_analysis.composite_pathway import resolve_composite_pathway

# Era boundaries are the SAP §0 development-age rule: the era containing the
# year the player turned 15 (birth year + 15).
ERA_1_BIRTH_YEARS = (1981, 1989)
ERA_2_BIRTH_YEARS = (1990, 1999)

OUTCOME_HORIZON_AGE = 25
OBSERVATION_END_SEASON = 2025

POOLED_OUTCOMES_COLUMNS = [
    "source_player_id",
    "birth_year",
    "era",
    "first_observed_season",
    "last_observed_season",
    "seasons_observed",
    "career_appearances",
    "career_minutes",
    "observed_pre2014",
    "observed_2014_plus",
    "reached_j1_by_age25",
    "reached_j1_ever",
    "first_j1_season",
    "horizon_complete",
    "eligible_confirmatory",
    "pathway_category",
    "pathway_category_source",
    # Both inputs to the SAP §1b-3 composite rule are kept alongside its output
    # so per-source validity can be reported, and so a reviewer can see which
    # procedure supplied a label without re-running the pipeline.
    "pathway_prose_category",
    "pathway_club_list_category",
    "pathway_composite_reason",
    "any_national_team_selection",
    "national_team_categories",
    "national_team_selection_source",
]


def assign_era(birth_year: int) -> str:
    if ERA_1_BIRTH_YEARS[0] <= birth_year <= ERA_1_BIRTH_YEARS[1]:
        return "era1"
    if ERA_2_BIRTH_YEARS[0] <= birth_year <= ERA_2_BIRTH_YEARS[1]:
        return "era2"
    if birth_year > ERA_2_BIRTH_YEARS[1]:
        return "era3"
    return "pre_era1"


def parse_int(value: str) -> int:
    value = (value or "").replace(",", "").strip()
    return int(value) if value.lstrip("-").isdigit() else 0


def collapse_career_seasons(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """One row per player from career_league_seasons_1999_2025.csv.

    reached_j1_by_age25 follows SAP §5: a J1 league appearance in any season
    where `season - birth_year <= 25`. Year-granular data means this tolerates
    up to one year of slack around the birthday, which the SAP accepts as a
    uniform rule rather than trying to resolve per player.
    """
    by_player: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_player[row["source_player_id"]].append(row)

    summaries: dict[str, dict[str, str]] = {}
    for player_id, player_rows in by_player.items():
        birth_date = next((r["birth_date"] for r in player_rows if r["birth_date"]), "")
        if len(birth_date) < 4 or not birth_date[:4].isdigit():
            continue
        birth_year = int(birth_date[:4])

        played = [r for r in player_rows if parse_int(r["appearances"]) > 0]
        if not played:
            # Registration-only rows: not league participation, so not eligible.
            continue

        seasons = sorted({int(r["season"]) for r in played})
        j1_seasons = sorted({int(r["season"]) for r in played if r["division"] == "J1"})
        j1_by_25 = [s for s in j1_seasons if s - birth_year <= OUTCOME_HORIZON_AGE]
        horizon_complete = birth_year + OUTCOME_HORIZON_AGE <= OBSERVATION_END_SEASON
        era = assign_era(birth_year)

        summaries[player_id] = {
            "source_player_id": player_id,
            "birth_year": str(birth_year),
            "era": era,
            "first_observed_season": str(seasons[0]),
            "last_observed_season": str(seasons[-1]),
            "seasons_observed": str(len(seasons)),
            "career_appearances": str(sum(parse_int(r["appearances"]) for r in played)),
            "career_minutes": str(sum(parse_int(r["minutes"]) for r in played)),
            "observed_pre2014": "1" if seasons[0] < 2014 else "0",
            "observed_2014_plus": "1" if seasons[-1] >= 2014 else "0",
            "reached_j1_by_age25": "1" if j1_by_25 else "0",
            "reached_j1_ever": "1" if j1_seasons else "0",
            "first_j1_season": str(j1_seasons[0]) if j1_seasons else "",
            "horizon_complete": "1" if horizon_complete else "0",
            # SAP §3: born >= 1981, league appearances > 0, age-25 horizon complete.
            # era3 is excluded from the confirmatory comparison by SAP §0/§5.
            "eligible_confirmatory": "1"
            if horizon_complete and era in ("era1", "era2")
            else "0",
        }
    return summaries


def resolve_composite_pathway_labels(
    labeled_rows: list[dict[str, str]],
    club_labels: dict[str, StintPathway],
    review_queue_rows: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    """Apply the SAP §1b-3 composite rule across every labeled player.

    labeled_rows is the concatenation of both collection universes: the rule has
    to be identical across eras, since an era-differential rule would manufacture
    the very interaction H1b-2 tests for.
    """
    reviewed_by_id = {row["source_player_id"]: row for row in review_queue_rows}
    resolved: dict[str, dict[str, str]] = {}

    for row in labeled_rows:
        player_id = row["source_player_id"]
        club = club_labels.get(player_id)
        review_row = reviewed_by_id.get(player_id)
        label = resolve_composite_pathway(
            prose_category=row.get("pathway_category", ""),
            prose_confidence=row.get("pathway_confidence", ""),
            club_category=club.pathway_category if club else "",
            club_confidence=club.confidence if club else "",
            reviewed_category=(
                review_row.get("reviewed_pathway_category", "").strip() if review_row else ""
            ),
            in_review_queue=review_row is not None,
            identity_confirmed=row.get("identity_check", "") == "confirmed",
        )
        resolved[player_id] = {
            "pathway_category": label.category,
            "pathway_category_source": label.source,
            "pathway_prose_category": row.get("pathway_category", ""),
            "pathway_club_list_category": club.pathway_category if club else "",
            "pathway_composite_reason": label.reason,
        }
    return resolved


def merge_label_sources(
    *resolved: dict[str, tuple[str, str]],
) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Combine per-universe label resolutions into one lookup.

    The 2014-2025 tiers and the pre-2014 priority files are meant to be disjoint
    universes (a player is in the backfill only if they never appeared from 2014
    on), so an overlap means one of the collections drifted. Returns the merged
    map plus the overlapping ids so the caller can report rather than silently
    pick a winner.
    """
    merged: dict[str, tuple[str, str]] = {}
    overlaps: list[str] = []
    for resolution in resolved:
        for player_id, value in resolution.items():
            if player_id in merged and merged[player_id] != value:
                overlaps.append(player_id)
            merged[player_id] = value
    return merged, sorted(set(overlaps))
