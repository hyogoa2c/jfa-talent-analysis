from jfa_talent_analysis.sources.wikidata import (
    WikidataTeamStint,
    classify_wikidata_audit,
    contains_katakana,
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
        )
    ]


def test_summarize_stints_counts_foreign_teams():
    summary = summarize_stints(
        [
            WikidataTeamStint("http://www.wikidata.org/entity/Q1", "x", "浦和", "日本", "", ""),
            WikidataTeamStint(
                "http://www.wikidata.org/entity/Q1", "x", "Hannover 96", "ドイツ", "", ""
            ),
        ]
    )

    assert summary["wikidata_person_count"] == "1"
    assert summary["wikidata_person_ids"] == "Q1"
    assert summary["wikidata_foreign_team_count"] == "1"
    assert summary["wikidata_foreign_teams"] == "Hannover 96 (ドイツ)"


def test_classify_wikidata_audit_marks_foreign_stint_candidate():
    result = classify_wikidata_audit(
        "原口 元気",
        {
            "wikidata_person_count": "1",
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
            "wikidata_foreign_team_count": "0",
        },
    )

    assert result == {
        "audit_status": "needs_manual_review",
        "manual_review_reason": "katakana_name_without_wikidata_foreign_club_hint",
    }


def test_contains_katakana():
    assert contains_katakana("シュミット ダニエル")
    assert not contains_katakana("原口 元気")
