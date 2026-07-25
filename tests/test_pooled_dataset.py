from jfa_talent_analysis.pooled_dataset import (
    assign_era,
    collapse_career_seasons,
    merge_label_sources,
)


def season_row(**overrides: str) -> dict[str, str]:
    row = {
        "source_player_id": "1",
        "season": "2010",
        "division": "J1",
        "appearances": "10",
        "minutes": "900",
        "goals": "0",
        "team_names": "テスト",
        "source": "pre2014_archive",
        "birth_date": "1985/04/01",
    }
    row.update(overrides)
    return row


def test_assign_era_follows_sap_birth_year_boundaries():
    assert assign_era(1981) == "era1"
    assert assign_era(1989) == "era1"
    assert assign_era(1990) == "era2"
    assert assign_era(1999) == "era2"
    assert assign_era(2000) == "era3"
    assert assign_era(1980) == "pre_era1"


def test_reached_j1_by_age25_uses_the_horizon_not_the_whole_career():
    """A J1 season after the age-25 horizon must not count for the by-25 outcome,
    but still counts for reached_j1_ever."""
    summaries = collapse_career_seasons(
        [
            season_row(season="2008", division="J2"),
            season_row(season="2013", division="J1"),  # age 28
        ]
    )
    assert summaries["1"]["reached_j1_by_age25"] == "0"
    assert summaries["1"]["reached_j1_ever"] == "1"
    assert summaries["1"]["first_j1_season"] == "2013"


def test_reached_j1_by_age25_counts_a_season_inside_the_horizon():
    summaries = collapse_career_seasons([season_row(season="2010")])  # age 25
    assert summaries["1"]["reached_j1_by_age25"] == "1"


def test_registration_only_seasons_do_not_make_a_player_eligible():
    """appearances=0 rows are squad registrations, not league participation
    (SAP §3), so a player with only those is dropped entirely."""
    assert collapse_career_seasons([season_row(appearances="0", minutes="0")]) == {}


def test_appearances_zero_season_excluded_from_career_totals():
    summaries = collapse_career_seasons(
        [season_row(season="2009", appearances="0", minutes="0"), season_row(season="2010")]
    )
    assert summaries["1"]["first_observed_season"] == "2010"
    assert summaries["1"]["seasons_observed"] == "1"
    assert summaries["1"]["career_appearances"] == "10"


def test_incomplete_horizon_is_not_eligible_for_the_confirmatory_comparison():
    summaries = collapse_career_seasons(
        [season_row(season="2024", birth_date="2001/04/01", division="J1")]
    )
    assert summaries["1"]["horizon_complete"] == "0"
    assert summaries["1"]["eligible_confirmatory"] == "0"


def test_era3_is_excluded_from_the_confirmatory_comparison():
    summaries = collapse_career_seasons(
        [season_row(season="2020", birth_date="2000/04/01", division="J1")]
    )
    assert summaries["1"]["era"] == "era3"
    assert summaries["1"]["eligible_confirmatory"] == "0"


def test_merge_label_sources_reports_conflicting_ids():
    """The two collection universes are meant to be disjoint; a disagreement
    means one drifted, so it is surfaced rather than silently resolved."""
    merged, overlaps = merge_label_sources(
        {"1": ("university", "auto_high_confidence")},
        {"1": ("high_school", "human_reviewed"), "2": ("university", "human_reviewed")},
    )
    assert overlaps == ["1"]
    assert merged["2"] == ("university", "human_reviewed")


def test_merge_label_sources_ignores_identical_duplicates():
    _, overlaps = merge_label_sources(
        {"1": ("university", "auto_high_confidence")},
        {"1": ("university", "auto_high_confidence")},
    )
    assert overlaps == []
