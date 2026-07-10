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
    # Wikipedia-backfilled J1 debut evidence (docs/data_collection_revision_
    # proposal_2026-07-07.md item 1): SFPR01's reached_j1/first_j1_season only
    # see 2014+, so pre-2014 debuts need Wikipedia's 出場歴 lines.
    "wikipedia_j1_debut_year",
    "reached_j1_ever",
    "reached_j1_ever_source",
    "first_j1_year_best",
    # Full-population overseas outcome (proposal item 2): classifier over
    # Wikipedia career prose, overridden by the manually-reviewed queue rows.
    "moved_overseas_wiki",
    "moved_overseas_wiki_confidence",
    "moved_overseas_final",
    "moved_overseas_final_source",
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


def resolve_reached_j1(
    summary: dict[str, str], wikipedia_j1_debut_year: str
) -> tuple[str, str, str]:
    """Combine SFPR01's in-window reached_j1 with Wikipedia debut-line evidence.

    Returns (reached_j1_ever, source, first_j1_year_best). Wikipedia evidence can
    only ADD a J1 debut SFPR01 couldn't see (pre-2014, or a name-matching gap) —
    it never demotes an SFPR01-observed J1 appearance. first_j1_year_best takes
    the EARLIER of the two years, since SFPR01's first_j1_season for a pre-2014
    debutant is really a later return/continuation season, not the debut.
    """
    sfpr01_reached = summary.get("reached_j1") == "1"
    sfpr01_year = summary.get("first_j1_season", "")
    wiki_year = wikipedia_j1_debut_year

    if sfpr01_reached and wiki_year:
        source = "both"
    elif sfpr01_reached:
        source = "sfpr01"
    elif wiki_year:
        source = "wikipedia_backfill"
    else:
        return ("0", "no_evidence", "")

    years = [int(float(year)) for year in (sfpr01_year, wiki_year) if year]
    return ("1", source, str(min(years)) if years else "")


TRUSTED_WIKI_CONFIDENCES = {"high", "human_reviewed"}


def resolve_moved_overseas_final(
    manual_value: str, wiki_value: str, wiki_confidence: str
) -> tuple[str, str]:
    """Combine the manually-reviewed queue decision (33 reappearance-gap players,
    highest authority where present) with the full-population Wikipedia
    classifier — whose needs_review rows have themselves been human-reviewed
    (data/manual/overseas_review_queue.csv, 196 rows; wiki_confidence=
    "human_reviewed" for those, on par with the classifier's own "high"
    confidence, see docs/overseas_needs_review_2026-07-09.md).

    Note the definitions differ slightly: the manual queue judged a specific
    reappearance gap, the classifier judges the whole career — a queue "0"
    with a classifier "yes" therefore prefers the classifier only when its
    confidence is trusted (the queue player may have moved abroad OUTSIDE the
    reviewed gap, a real corpus case: 片岡爽 moved to Australia in 2024 after his
    reviewed gap)."""
    if manual_value == "1":
        return ("1", "manual_review")
    if manual_value == "0":
        if wiki_value == "yes" and wiki_confidence in TRUSTED_WIKI_CONFIDENCES:
            source = (
                "human_reviewed_over_gap_scoped_review"
                if wiki_confidence == "human_reviewed"
                else "wikipedia_classifier_over_gap_scoped_review"
            )
            return ("1", source)
        return ("0", "manual_review")
    wiki_source = "human_reviewed" if wiki_confidence == "human_reviewed" else "wikipedia_classifier"
    if wiki_value == "yes":
        return ("1", wiki_source)
    if wiki_value == "no":
        return ("0", wiki_source)
    return ("", "no_evidence")


def build_player_pathway_outcomes(
    player_summaries: dict[str, dict[str, str]],
    pathway_resolved: dict[str, tuple[str, str]],
    national_team_resolved: dict[str, tuple[str, str]],
    national_team_categories_by_id: dict[str, str],
    moved_overseas_by_id: dict[str, tuple[str, str]],
    wikipedia_j1_debut_by_id: dict[str, str] | None = None,
    overseas_wiki_by_id: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Join per-player season summaries with resolved pathway/national-team
    labels and moved_overseas outcomes into one analysis-ready row per player.

    Every player in player_summaries is kept even if a given outcome has no
    resolved value (blank rather than assumed-negative), consistent with this
    project's established caution against reading missing evidence as a
    confirmed negative.
    """
    wikipedia_j1_debut_by_id = wikipedia_j1_debut_by_id or {}
    overseas_wiki_by_id = overseas_wiki_by_id or {}

    rows = []
    for player_id, summary in player_summaries.items():
        pathway_category, pathway_source = pathway_resolved.get(player_id, ("", ""))
        selection, selection_source = national_team_resolved.get(player_id, ("", ""))
        moved_overseas, moved_overseas_basis = moved_overseas_by_id.get(player_id, ("", ""))

        wiki_j1_year = wikipedia_j1_debut_by_id.get(player_id, "")
        reached_ever, reached_source, first_j1_best = resolve_reached_j1(summary, wiki_j1_year)

        wiki_overseas, wiki_overseas_confidence = overseas_wiki_by_id.get(player_id, ("", ""))
        overseas_final, overseas_final_source = resolve_moved_overseas_final(
            moved_overseas, wiki_overseas, wiki_overseas_confidence
        )

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
                "wikipedia_j1_debut_year": wiki_j1_year,
                "reached_j1_ever": reached_ever,
                "reached_j1_ever_source": reached_source,
                "first_j1_year_best": first_j1_best,
                "moved_overseas_wiki": wiki_overseas,
                "moved_overseas_wiki_confidence": wiki_overseas_confidence,
                "moved_overseas_final": overseas_final,
                "moved_overseas_final_source": overseas_final_source,
            }
        )
    return rows
