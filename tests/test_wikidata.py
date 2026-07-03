from jfa_talent_analysis.sources.wikidata import (
    WikidataTeamStint,
    build_player_team_query,
    classify_wikidata_audit,
    contains_katakana,
    foreign_stints_in_gap,
    name_label_variants,
    parse_player_team_stints,
    summarize_stints,
)


def test_name_label_variants_includes_japanese_no_space_and_english_title():
    assert name_label_variants("原口 元気", "GENKI HARAGUCHI") == [
        ("原口 元気", "ja"),
        ("原口元気", "ja"),
        ("GENKI HARAGUCHI", "en"),
        ("Genki Haraguchi", "en"),
    ]


def test_build_player_team_query_binds_footballer_occupation_and_birth_date():
    query = build_player_team_query("原口 元気", "GENKI HARAGUCHI")

    assert "BIND(EXISTS { ?person wdt:P106 wd:Q937857 } AS ?isFootballer)" in query
    assert "OPTIONAL { ?person wdt:P569 ?birthDate. }" in query
    assert "?isFootballer ?birthDate" in query


def test_parse_player_team_stints():
    data = {
        "results": {
            "bindings": [
                {
                    "person": {"value": "http://www.wikidata.org/entity/Q1"},
                    "personLabel": {"value": "原口元気"},
                    "teamLabel": {"value": "1. FC Union Berlin"},
                    "countryLabel": {"value": "ドイツ"},
                    "start": {"value": "2021-01-01T00:00:00Z"},
                    "isFootballer": {"value": "true"},
                    "birthDate": {"value": "1991-05-09T00:00:00Z"},
                }
            ]
        }
    }

    stints = parse_player_team_stints(data)

    assert stints == [
        WikidataTeamStint(
            person_uri="http://www.wikidata.org/entity/Q1",
            person_label="原口元気",
            team_label="1. FC Union Berlin",
            country_label="ドイツ",
            start="2021-01-01T00:00:00Z",
            end="",
            person_is_footballer="1",
            person_birth_date="1991-05-09T00:00:00Z",
        )
    ]


def test_parse_player_team_stints_normalizes_missing_and_false_footballer_flag():
    data = {
        "results": {
            "bindings": [
                {
                    "person": {"value": "http://www.wikidata.org/entity/Q2"},
                    "isFootballer": {"value": "false"},
                },
                {
                    "person": {"value": "http://www.wikidata.org/entity/Q3"},
                },
            ]
        }
    }

    stints = parse_player_team_stints(data)

    assert stints[0].person_is_footballer == "0"
    assert stints[1].person_is_footballer == "0"
    assert stints[1].person_birth_date == ""


def test_summarize_stints_counts_foreign_teams():
    summary = summarize_stints(
        [
            WikidataTeamStint(
                "http://www.wikidata.org/entity/Q1", "x", "浦和", "日本", "", "", "1", ""
            ),
            WikidataTeamStint(
                "http://www.wikidata.org/entity/Q1", "x", "Hannover 96", "ドイツ", "", "", "1", ""
            ),
        ]
    )

    assert summary["wikidata_person_count"] == "1"
    assert summary["wikidata_person_ids"] == "Q1"
    assert summary["wikidata_foreign_team_count"] == "1"
    assert summary["wikidata_foreign_teams"] == "Hannover 96 (ドイツ)"


def test_summarize_stints_reports_footballer_count_and_birth_dates():
    summary = summarize_stints(
        [
            WikidataTeamStint(
                "http://www.wikidata.org/entity/Q1",
                "x",
                "浦和",
                "日本",
                "",
                "",
                "1",
                "1991-05-09T00:00:00Z",
            ),
            WikidataTeamStint(
                "http://www.wikidata.org/entity/Q1",
                "x",
                "Hannover 96",
                "ドイツ",
                "",
                "",
                "1",
                "1991-05-09T00:00:00Z",
            ),
        ]
    )

    assert summary["wikidata_footballer_person_count"] == "1"
    assert summary["wikidata_birth_dates"] == "1991-05-09"


def test_summarize_stints_excludes_non_footballer_persons_from_footballer_count():
    summary = summarize_stints(
        [
            WikidataTeamStint(
                "http://www.wikidata.org/entity/Q9", "x", "浦和", "日本", "", "", "0", ""
            ),
        ]
    )

    assert summary["wikidata_person_count"] == "1"
    assert summary["wikidata_footballer_person_count"] == "0"
    assert summary["wikidata_birth_dates"] == ""


def test_foreign_stints_in_gap_includes_overlapping_stint():
    stints = [
        WikidataTeamStint(
            "http://www.wikidata.org/entity/Q1",
            "x",
            "Hannover 96",
            "ドイツ",
            "2019-01-01T00:00:00Z",
            "2021-01-01T00:00:00Z",
        ),
    ]

    result = foreign_stints_in_gap(stints, gap_start_season=2020, gap_end_season=2020)

    assert result == ["Hannover 96 (ドイツ)"]


def test_foreign_stints_in_gap_excludes_stint_entirely_before_gap():
    stints = [
        WikidataTeamStint(
            "http://www.wikidata.org/entity/Q1",
            "x",
            "Hannover 96",
            "ドイツ",
            "2010-01-01T00:00:00Z",
            "2012-01-01T00:00:00Z",
        ),
    ]

    result = foreign_stints_in_gap(stints, gap_start_season=2020, gap_end_season=2022)

    assert result == []


def test_foreign_stints_in_gap_excludes_stint_entirely_after_gap():
    stints = [
        WikidataTeamStint(
            "http://www.wikidata.org/entity/Q1",
            "x",
            "Hannover 96",
            "ドイツ",
            "2023-01-01T00:00:00Z",
            "2024-01-01T00:00:00Z",
        ),
    ]

    result = foreign_stints_in_gap(stints, gap_start_season=2020, gap_end_season=2022)

    assert result == []


def test_foreign_stints_in_gap_excludes_stint_with_missing_start():
    stints = [
        WikidataTeamStint(
            "http://www.wikidata.org/entity/Q1",
            "x",
            "Hannover 96",
            "ドイツ",
            "",
            "2021-01-01T00:00:00Z",
        ),
    ]

    result = foreign_stints_in_gap(stints, gap_start_season=2020, gap_end_season=2022)

    assert result == []


def test_foreign_stints_in_gap_treats_missing_end_as_ongoing():
    stints = [
        WikidataTeamStint(
            "http://www.wikidata.org/entity/Q1",
            "x",
            "Hannover 96",
            "ドイツ",
            "2019-01-01T00:00:00Z",
            "",
        ),
    ]

    result = foreign_stints_in_gap(stints, gap_start_season=2020, gap_end_season=2022)

    assert result == ["Hannover 96 (ドイツ)"]


def test_foreign_stints_in_gap_excludes_ongoing_stint_starting_after_gap():
    stints = [
        WikidataTeamStint(
            "http://www.wikidata.org/entity/Q1",
            "x",
            "Hannover 96",
            "ドイツ",
            "2023-01-01T00:00:00Z",
            "",
        ),
    ]

    result = foreign_stints_in_gap(stints, gap_start_season=2020, gap_end_season=2022)

    assert result == []


def test_classify_wikidata_audit_marks_foreign_stint_candidate():
    result = classify_wikidata_audit(
        "原口 元気",
        {
            "wikidata_person_count": "1",
            "wikidata_footballer_person_count": "1",
            "wikidata_foreign_team_count": "2",
        },
    )

    assert result == {
        "audit_status": "candidate_foreign_stint",
        "manual_review_reason": "",
    }


def test_classify_wikidata_audit_keeps_unmatched_katakana_names_for_manual_review():
    result = classify_wikidata_audit(
        "シュミット ダニエル",
        {
            "wikidata_person_count": "0",
            "wikidata_foreign_team_count": "0",
        },
    )

    assert result == {
        "audit_status": "needs_manual_review",
        "manual_review_reason": "no_wikidata_person_match|katakana_name",
    }


def test_classify_wikidata_audit_keeps_katakana_no_foreign_hint_for_manual_review():
    result = classify_wikidata_audit(
        "ジョン 太郎",
        {
            "wikidata_person_count": "1",
            "wikidata_footballer_person_count": "1",
            "wikidata_foreign_team_count": "0",
        },
    )

    assert result == {
        "audit_status": "needs_manual_review",
        "manual_review_reason": "katakana_name_without_wikidata_foreign_club_hint",
    }


def test_classify_wikidata_audit_flags_single_non_footballer_match_for_manual_review():
    result = classify_wikidata_audit(
        "原口 元気",
        {
            "wikidata_person_count": "1",
            "wikidata_footballer_person_count": "0",
            "wikidata_foreign_team_count": "0",
        },
    )

    assert result == {
        "audit_status": "needs_manual_review",
        "manual_review_reason": "single_wikidata_match_not_footballer",
    }


def test_classify_wikidata_audit_appends_katakana_reason_for_non_footballer_match():
    result = classify_wikidata_audit(
        "シュミット ダニエル",
        {
            "wikidata_person_count": "1",
            "wikidata_footballer_person_count": "0",
            "wikidata_foreign_team_count": "0",
        },
    )

    assert result == {
        "audit_status": "needs_manual_review",
        "manual_review_reason": "single_wikidata_match_not_footballer|katakana_name",
    }


def test_contains_katakana():
    assert contains_katakana("シュミット ダニエル")
    assert not contains_katakana("原口 元気")
