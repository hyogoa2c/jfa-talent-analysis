from __future__ import annotations

PLAYER_SUMMARY_COLUMNS = [
    "source_player_id",
    "name_ja",
    "name_en",
    "birth_date",
    "first_observed_season",
    "last_observed_season",
    "seasons_observed",
    "career_minutes",
    "career_j1_minutes",
    "reached_j1",
    "first_j1_season",
    "first_j1_age",
]

PLAYER_PATHWAY_OUTCOMES_COLUMNS = [
    *PLAYER_SUMMARY_COLUMNS,
    "pathway_category",
    "pathway_category_source",
    "any_national_team_selection",
    "national_team_categories",
    "national_team_selection_source",
    "moved_overseas",
    "moved_overseas_basis",
]


def collapse_player_season_features(season_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    """Collapse player-season rows (one row per player per season) into one
    summary row per source_player_id.

    reached_j1 becomes "ever reached J1 by the end of the observed window"
    rather than a per-season snapshot; career_minutes/career_j1_minutes sum
    across every observed season rather than tracking a single season.
    """
    by_player: dict[str, list[dict[str, str]]] = {}
    for row in season_rows:
        by_player.setdefault(row["source_player_id"], []).append(row)

    return {
        player_id: summarize_player_seasons(player_id, rows)
        for player_id, rows in by_player.items()
    }


def summarize_player_seasons(player_id: str, rows: list[dict[str, str]]) -> dict[str, str]:
    seasons = sorted(row["season"] for row in rows if row["season"])
    reached_j1_rows = [row for row in rows if row.get("reached_j1") == "1"]
    first_j1_season = next((row["first_j1_season"] for row in rows if row.get("first_j1_season")), "")
    first_j1_age = next((row["first_j1_age"] for row in rows if row.get("first_j1_age")), "")

    return {
        "source_player_id": player_id,
        "name_ja": rows[0].get("name_ja", ""),
        "name_en": rows[0].get("name_en", ""),
        "birth_date": rows[0].get("birth_date", ""),
        "first_observed_season": seasons[0] if seasons else "",
        "last_observed_season": seasons[-1] if seasons else "",
        "seasons_observed": str(len(rows)),
        "career_minutes": str(sum(parse_int(row.get("minutes")) for row in rows)),
        "career_j1_minutes": str(sum(parse_int(row.get("j1_minutes")) for row in rows)),
        "reached_j1": "1" if reached_j1_rows else "0",
        "first_j1_season": first_j1_season,
        "first_j1_age": first_j1_age,
    }


def parse_int(value: str | None) -> int:
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def apply_review_overrides(
    labeled_rows: list[dict[str, str]],
    review_queue_rows: list[dict[str, str]],
    *,
    value_column: str,
    reviewed_value_column: str,
) -> dict[str, tuple[str, str]]:
    """Resolve a final value per player_id, preferring a non-blank reviewed
    value over the labeled (auto-classified) value.

    Returns {player_id: (final_value, source)} where source is one of
    "human_reviewed" (a needs_review row, whether or not the reviewer changed
    the auto value — a blank reviewed_* column means "confirmed as-is", per
    docs/pathway_national_team_review_instructions_2026-07-05.md's rule),
    "auto_high_confidence" (never needed review), or "identity_not_confirmed"
    (value_column was blank because identity_check wasn't "confirmed").
    """
    reviewed_by_id = {row["source_player_id"]: row for row in review_queue_rows}
    resolved: dict[str, tuple[str, str]] = {}
    for row in labeled_rows:
        player_id = row["source_player_id"]
        auto_value = row.get(value_column, "")
        review_row = reviewed_by_id.get(player_id)

        if review_row is not None:
            reviewed_value = review_row.get(reviewed_value_column, "").strip()
            resolved[player_id] = (reviewed_value or auto_value, "human_reviewed")
        elif auto_value:
            resolved[player_id] = (auto_value, "auto_high_confidence")
        else:
            resolved[player_id] = ("", "identity_not_confirmed")
    return resolved


def build_player_pathway_outcomes(
    player_summaries: dict[str, dict[str, str]],
    pathway_resolved: dict[str, tuple[str, str]],
    national_team_resolved: dict[str, tuple[str, str]],
    national_team_categories_by_id: dict[str, str],
    moved_overseas_by_id: dict[str, tuple[str, str]],
) -> list[dict[str, str]]:
    """Join per-player season summaries with resolved pathway/national-team
    labels and moved_overseas outcomes into one analysis-ready row per player.

    Every player in player_summaries is kept even if a given outcome has no
    resolved value (blank rather than assumed-negative), consistent with this
    project's established caution against reading missing evidence as a
    confirmed negative.
    """
    rows = []
    for player_id, summary in player_summaries.items():
        pathway_category, pathway_source = pathway_resolved.get(player_id, ("", ""))
        selection, selection_source = national_team_resolved.get(player_id, ("", ""))
        moved_overseas, moved_overseas_basis = moved_overseas_by_id.get(player_id, ("", ""))

        rows.append(
            {
                **summary,
                "pathway_category": pathway_category,
                "pathway_category_source": pathway_source,
                "any_national_team_selection": selection,
                "national_team_categories": national_team_categories_by_id.get(player_id, ""),
                "national_team_selection_source": selection_source,
                "moved_overseas": moved_overseas,
                "moved_overseas_basis": moved_overseas_basis,
            }
        )
    return rows
