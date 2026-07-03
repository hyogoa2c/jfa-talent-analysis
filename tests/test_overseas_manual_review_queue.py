from jfa_talent_analysis.overseas_review import (
    build_manual_review_rows,
    validate_manual_review_rows,
)


def test_build_manual_review_rows_filters_and_adds_manual_columns():
    rows = [
        {
            "source_player_id": "1",
            "name_ja": "原口 元気",
            "name_en": "Genki HARAGUCHI",
            "previous_observed_season": "2014",
            "reappearance_season": "2024",
            "absent_seasons": "9",
            "reappearance_leagues": "Ｊ１リーグ",
            "reappearance_teams": "浦和",
            "reappearance_minutes": "461",
            "wikidata_person_ids": "Q982163",
            "wikidata_foreign_teams": "Hannover 96 (ドイツ)",
            "audit_status": "candidate_foreign_stint",
            "manual_review_reason": "",
        },
        {
            "source_player_id": "2",
            "name_ja": "シュミット ダニエル",
            "name_en": "SCHMIDT Daniel",
            "previous_observed_season": "2019",
            "reappearance_season": "2025",
            "absent_seasons": "5",
            "reappearance_leagues": "Ｊ１リーグ",
            "reappearance_teams": "名古屋",
            "reappearance_minutes": "450",
            "wikidata_person_ids": "",
            "wikidata_foreign_teams": "",
            "audit_status": "needs_manual_review",
            "manual_review_reason": "no_wikidata_person_match|katakana_name",
        },
    ]

    manual_rows = build_manual_review_rows(rows)

    assert manual_rows == [
        {
            "source_player_id": "2",
            "name_ja": "シュミット ダニエル",
            "name_en": "SCHMIDT Daniel",
            "previous_observed_season": "2019",
            "reappearance_season": "2025",
            "absent_seasons": "5",
            "reappearance_leagues": "Ｊ１リーグ",
            "reappearance_teams": "名古屋",
            "reappearance_minutes": "450",
            "wikidata_person_ids": "",
            "wikidata_foreign_teams": "",
            "audit_status": "needs_manual_review",
            "manual_review_reason": "no_wikidata_person_match|katakana_name",
            "wikipedia_titles": "",
            "wikipedia_urls": "",
            "wikipedia_search_error": "",
            "manual_decision": "",
            "manual_note": "",
            "evidence_url": "",
        }
    ]


def test_build_manual_review_rows_sorts_larger_gaps_first():
    rows = [
        {
            "name_ja": "小 gap",
            "reappearance_season": "2023",
            "absent_seasons": "2",
            "audit_status": "needs_manual_review",
        },
        {
            "name_ja": "大 gap",
            "reappearance_season": "2025",
            "absent_seasons": "7",
            "audit_status": "needs_manual_review",
        },
    ]

    manual_rows = build_manual_review_rows(rows)

    assert [row["name_ja"] for row in manual_rows] == ["大 gap", "小 gap"]


def test_validate_manual_review_rows_allows_blank_decisions_before_review():
    assert validate_manual_review_rows([{"source_player_id": "1", "manual_decision": ""}]) == []


def test_validate_manual_review_rows_rejects_unknown_decisions():
    errors = validate_manual_review_rows(
        [{"source_player_id": "1", "manual_decision": "yes_foreign"}]
    )

    assert "manual_decision must be one of" in errors[0]


def test_validate_manual_review_rows_requires_evidence_for_confirmed_foreign_stint():
    errors = validate_manual_review_rows(
        [{"source_player_id": "1", "manual_decision": "confirmed_foreign_stint"}]
    )

    assert errors == ["line 2 source_player_id=1: confirmed_foreign_stint requires evidence_url"]


def test_validate_manual_review_rows_accepts_pipe_separated_urls():
    errors = validate_manual_review_rows(
        [
            {
                "source_player_id": "1",
                "manual_decision": "confirmed_foreign_stint",
                "evidence_url": "https://example.com/a|http://example.com/b",
            }
        ]
    )

    assert errors == []


def test_validate_manual_review_rows_rejects_invalid_urls():
    errors = validate_manual_review_rows(
        [
            {
                "source_player_id": "1",
                "manual_decision": "identity_resolved_no_decision",
                "evidence_url": "not-a-url",
            }
        ]
    )

    assert errors == ["line 2 source_player_id=1: evidence_url must start with http:// or https://"]


def test_validate_manual_review_rows_requires_note_for_unresolved():
    errors = validate_manual_review_rows(
        [{"source_player_id": "1", "manual_decision": "unresolved"}]
    )

    assert errors == ["line 2 source_player_id=1: unresolved requires manual_note"]
