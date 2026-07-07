import json
from pathlib import Path

from jfa_talent_analysis.national_team_classification import (
    build_national_team_label_row,
    build_national_team_review_queue_rows,
    classify_national_team_selection,
)

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "national_team_pilot_cases.json").read_text(
        encoding="utf-8"
    )
)


def candidate_row(**overrides: str) -> dict[str, str]:
    row = {
        "source_player_id": "1",
        "name_ja": "山田 太郎",
        "name_en": "Taro YAMADA",
        "wikipedia_title": "山田太郎",
        "identity_check": "confirmed",
        "wikipedia_national_team_context": "U-18日本代表\n",
    }
    row.update(overrides)
    return row


def test_national_team_pilot_fixtures_never_silently_wrong():
    """A wrong any_national_team_selection guess is acceptable only when flagged
    needs_review, matching docs/national_team_pilot_2026-07-03.md's table."""
    for case in FIXTURES:
        result = classify_national_team_selection(case["context"])
        if result.confidence == "high":
            assert result.any_national_team_selection == case["expected_any_selection"], case[
                "name_ja"
            ]


def test_national_team_pilot_fixtures_overall_accuracy_does_not_regress():
    correct = sum(
        classify_national_team_selection(case["context"]).any_national_team_selection
        == case["expected_any_selection"]
        for case in FIXTURES
    )
    assert correct >= 20


def test_prose_a_team_debut_is_detected():
    """The compact "^日本代表$" line format only covers infobox-derived list-style
    articles; a fuller narrative bio (like 原口元気's, found by manual review to be
    a silent "no" before this pattern was added) states a senior debut in prose
    instead, e.g. "2011年10月7日、キリンチャレンジカップ・ベトナム戦で日本代表初出場"."""
    result = classify_national_team_selection(
        "2011年10月7日、キリンチャレンジカップ・ベトナム戦で日本代表初出場。"
    )
    assert result.any_national_team_selection == "yes"
    assert result.categories == ("A",)


def test_clean_youth_and_a_team_line_format():
    result = classify_national_team_selection("U-18日本代表\nU-19日本代表\n日本代表\n")
    assert result.any_national_team_selection == "yes"
    assert set(result.categories) == {"U18", "U19", "A"}
    assert result.confidence == "high"


def test_club_age_group_team_is_not_a_national_team_mention():
    """A bare "U-18" without "代表" nearby names a club's own youth team (e.g. "U-18
    には昇格せず"), not a national-team call-up — the false positive the pilot's
    高瀬生聖/遠藤貴成 cases exposed at full population scale."""
    result = classify_national_team_selection(
        "ガンバ大阪ジュニアユースに所属。U-18には昇格せず、高校へ進学した。"
    )
    assert result.any_national_team_selection == "no"
    assert result.categories == ()


def test_negated_selection_with_daihyo_is_excluded_and_flagged():
    result = classify_national_team_selection("U-17日本代表のメンバーからは落選した。")
    assert result.any_national_team_selection == "no"
    assert result.confidence == "needs_review"


def test_negation_without_daihyo_wording_is_not_flagged():
    """A negation word describing a *club* trial or a bare tournament name (no
    "代表"/"大学選抜" in the same sentence) shouldn't flag needs_review just because
    the word appears somewhere in the bio — docs/national_team_pilot_2026-07-03.md's
    Labeling Phase section found this over-flagged ~35 unrelated rows (e.g.
    福森直也's "ガンバ大阪ジュニアユースのセレクションを受けるが落選", about a club
    academy trial, not the national team) before this was narrowed."""
    result = classify_national_team_selection(
        "ガンバ大阪ジュニアユースのセレクションを受けるが落選。"
    )
    assert result.any_national_team_selection == "no"
    assert result.confidence == "high"


def test_candidate_only_wording_is_unclear():
    result = classify_national_team_selection("2021年にU-18日本代表候補に選出された。")
    assert result.any_national_team_selection == "unclear"
    assert result.confidence == "needs_review"


def test_university_select_team_maps_to_university_category():
    result = classify_national_team_selection("全日本大学選抜（2010年）")
    assert result.any_national_team_selection == "yes"
    assert result.categories == ("university",)


def test_no_evidence_is_no_high_confidence():
    result = classify_national_team_selection("2018年にプロデビューした。")
    assert result.any_national_team_selection == "no"
    assert result.confidence == "high"


def test_build_national_team_label_row_labels_confirmed_rows():
    row = build_national_team_label_row(candidate_row(), "wikipedia_national_team_context")
    assert row["any_national_team_selection"] == "yes"
    assert row["national_team_categories"] == "U18"


def test_build_national_team_label_row_leaves_unconfirmed_rows_blank():
    row = build_national_team_label_row(
        candidate_row(identity_check="no_birth_date_found"), "wikipedia_national_team_context"
    )
    assert row["any_national_team_selection"] == ""
    assert row["national_team_reason"] == "identity_not_confirmed"


def test_out_of_range_bracket_maps_to_other():
    result = classify_national_team_selection("U-22日本代表\nMirabror Usmanov Memorial Cup(2025年)")
    assert result.any_national_team_selection == "yes"
    assert result.categories == ("other",)


def test_build_national_team_review_queue_rows_only_includes_needs_review():
    labeled_rows = [
        {
            "source_player_id": "1",
            "name_ja": "高信頼度太郎",
            "name_en": "",
            "wikipedia_title": "高信頼度太郎",
            "any_national_team_selection": "no",
            "national_team_categories": "",
            "national_team_reason": "clean_signal",
            "national_team_confidence": "high",
        },
        {
            "source_player_id": "2",
            "name_ja": "要確認次郎",
            "name_en": "",
            "wikipedia_title": "要確認次郎",
            "any_national_team_selection": "no",
            "national_team_categories": "",
            "national_team_reason": "negation_or_candidate_language_present",
            "national_team_confidence": "needs_review",
        },
    ]
    rows = build_national_team_review_queue_rows(
        labeled_rows, {"2": "U-17日本代表候補に選ばれた。"}, tier="b"
    )
    assert len(rows) == 1
    assert rows[0]["source_player_id"] == "2"
    assert rows[0]["tier"] == "b"
    assert rows[0]["wikipedia_national_team_context"] == "U-17日本代表候補に選ばれた。"
    assert rows[0]["reviewed_any_national_team_selection"] == ""
    assert rows[0]["reviewed_categories"] == ""
    assert rows[0]["reviewer_note"] == ""
