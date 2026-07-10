from jfa_talent_analysis.analysis_dataset import (
    apply_review_overrides,
    build_player_pathway_outcomes,
    collapse_player_season_features,
    resolve_moved_overseas_final,
    resolve_reached_j1,
)


def season_row(**overrides: str) -> dict[str, str]:
    row = {
        "source_player_id": "1",
        "name_ja": "山田 太郎",
        "name_en": "Taro YAMADA",
        "birth_date": "1995/01/01",
        "season": "2015",
        "minutes": "500",
        "j1_minutes": "0",
        "reached_j1": "0",
        "first_j1_season": "",
        "first_j1_age": "",
    }
    row.update(overrides)
    return row


def test_collapse_player_season_features_sums_minutes_across_seasons():
    summaries = collapse_player_season_features(
        [
            season_row(season="2015", minutes="500", j1_minutes="0"),
            season_row(season="2016", minutes="900", j1_minutes="300", reached_j1="1",
                       first_j1_season="2016", first_j1_age="21"),
        ]
    )
    summary = summaries["1"]
    assert summary["career_minutes"] == "1400"
    assert summary["career_j1_minutes"] == "300"
    assert summary["reached_j1"] == "1"
    assert summary["first_j1_season"] == "2016"
    assert summary["first_observed_season"] == "2015"
    assert summary["last_observed_season"] == "2016"
    assert summary["seasons_observed"] == "2"


def test_collapse_player_season_features_never_reaching_j1():
    summaries = collapse_player_season_features(
        [season_row(season="2015"), season_row(season="2016")]
    )
    assert summaries["1"]["reached_j1"] == "0"
    assert summaries["1"]["first_j1_season"] == ""


def labeled_row(player_id: str, value: str, reason: str = "single_stage_tier_matched") -> dict[str, str]:
    return {
        "source_player_id": player_id,
        "pathway_category": value,
        "pathway_reason": reason,
    }


def review_row(player_id: str, reviewed_value: str) -> dict[str, str]:
    return {"source_player_id": player_id, "reviewed_pathway_category": reviewed_value}


def test_apply_review_overrides_prefers_reviewed_value():
    resolved = apply_review_overrides(
        [labeled_row("1", "high_school")],
        [review_row("1", "j_club_academy")],
        value_column="pathway_category",
        reviewed_value_column="reviewed_pathway_category",
    )
    assert resolved["1"] == ("j_club_academy", "human_reviewed")


def test_apply_review_overrides_blank_reviewed_value_means_confirmed_as_is():
    resolved = apply_review_overrides(
        [labeled_row("1", "university")],
        [review_row("1", "")],
        value_column="pathway_category",
        reviewed_value_column="reviewed_pathway_category",
    )
    assert resolved["1"] == ("university", "human_reviewed")


def test_apply_review_overrides_high_confidence_row_never_reviewed():
    resolved = apply_review_overrides(
        [labeled_row("1", "university")],
        [],
        value_column="pathway_category",
        reviewed_value_column="reviewed_pathway_category",
    )
    assert resolved["1"] == ("university", "auto_high_confidence")


def test_apply_review_overrides_identity_not_confirmed_stays_blank():
    resolved = apply_review_overrides(
        [labeled_row("1", "")],
        [],
        value_column="pathway_category",
        reviewed_value_column="reviewed_pathway_category",
    )
    assert resolved["1"] == ("", "identity_not_confirmed")


def test_build_player_pathway_outcomes_joins_every_source():
    player_summaries = {
        "1": {"source_player_id": "1", "name_ja": "山田 太郎", "reached_j1": "1"},
        "2": {"source_player_id": "2", "name_ja": "佐藤 次郎", "reached_j1": "0"},
    }
    rows = build_player_pathway_outcomes(
        player_summaries,
        pathway_resolved={"1": ("university", "auto_high_confidence")},
        national_team_resolved={"1": ("yes", "human_reviewed")},
        national_team_categories_by_id={"1": "A|U23"},
        moved_overseas_by_id={"1": ("1", "confirmed_foreign_stint")},
    )
    rows_by_id = {row["source_player_id"]: row for row in rows}

    assert rows_by_id["1"]["pathway_category"] == "university"
    assert rows_by_id["1"]["any_national_team_selection"] == "yes"
    assert rows_by_id["1"]["national_team_categories"] == "A|U23"
    assert rows_by_id["1"]["moved_overseas"] == "1"

    # Player 2 has no resolved outcomes at all — kept with blanks, not dropped
    # or defaulted to a negative, matching this project's evidence-absence caution.
    assert rows_by_id["2"]["pathway_category"] == ""
    assert rows_by_id["2"]["any_national_team_selection"] == ""
    assert rows_by_id["2"]["moved_overseas"] == ""


def test_resolve_reached_j1_wikipedia_backfills_pre2014_debut():
    summary = {"reached_j1": "0", "first_j1_season": ""}
    assert resolve_reached_j1(summary, "2010") == ("1", "wikipedia_backfill", "2010")


def test_resolve_reached_j1_takes_earlier_year_when_both_exist():
    summary = {"reached_j1": "1", "first_j1_season": "2015"}
    assert resolve_reached_j1(summary, "2009") == ("1", "both", "2009")


def test_resolve_reached_j1_sfpr01_only():
    summary = {"reached_j1": "1", "first_j1_season": "2016"}
    assert resolve_reached_j1(summary, "") == ("1", "sfpr01", "2016")


def test_resolve_reached_j1_no_evidence():
    summary = {"reached_j1": "0", "first_j1_season": ""}
    assert resolve_reached_j1(summary, "") == ("0", "no_evidence", "")


def test_resolve_moved_overseas_manual_yes_wins():
    assert resolve_moved_overseas_final("1", "no", "high") == ("1", "manual_review")


def test_resolve_moved_overseas_high_confidence_wiki_yes_beats_gap_scoped_no():
    result = resolve_moved_overseas_final("0", "yes", "high")
    assert result == ("1", "wikipedia_classifier_over_gap_scoped_review")


def test_resolve_moved_overseas_flagged_wiki_yes_does_not_override_manual_no():
    assert resolve_moved_overseas_final("0", "yes", "needs_review") == ("0", "manual_review")


def test_resolve_moved_overseas_wiki_only():
    assert resolve_moved_overseas_final("", "yes", "high") == ("1", "wikipedia_classifier")
    assert resolve_moved_overseas_final("", "no", "high") == ("0", "wikipedia_classifier")


def test_resolve_moved_overseas_no_evidence():
    assert resolve_moved_overseas_final("", "", "") == ("", "no_evidence")


def test_resolve_moved_overseas_human_reviewed_source_label():
    assert resolve_moved_overseas_final("", "yes", "human_reviewed") == ("1", "human_reviewed")
    assert resolve_moved_overseas_final("", "no", "human_reviewed") == ("0", "human_reviewed")


def test_resolve_moved_overseas_human_reviewed_beats_gap_scoped_manual_no():
    result = resolve_moved_overseas_final("0", "yes", "human_reviewed")
    assert result == ("1", "human_reviewed_over_gap_scoped_review")
