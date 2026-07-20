import json
from pathlib import Path

from jfa_talent_analysis.pathway_classification import (
    build_pathway_label_row,
    build_pathway_review_queue_rows,
    classify_pathway_category,
)

FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "pathway_pilot_cases.json").read_text(encoding="utf-8")
)


def candidate_row(**overrides: str) -> dict[str, str]:
    row = {
        "source_player_id": "1",
        "name_ja": "山田 太郎",
        "name_en": "Taro YAMADA",
        "wikipedia_title": "山田太郎",
        "identity_check": "confirmed",
        "wikipedia_pathway_context": "○○高等学校でプレーし、卒業後にプロ入りした。",
    }
    row.update(overrides)
    return row


def test_pathway_pilot_fixtures_never_silently_mislabel():
    """Every high-confidence label must match docs/pathway_source_pilot_2026-07-03.md's
    manually-verified table. A wrong guess is acceptable only when flagged needs_review."""
    for case in FIXTURES:
        result = classify_pathway_category(case["context"])
        if result.confidence == "high":
            assert result.pathway_category == case["expected_pathway_category"], case["name_ja"]


def test_pathway_pilot_fixtures_overall_accuracy_does_not_regress():
    correct = sum(
        classify_pathway_category(case["context"]).pathway_category
        == case["expected_pathway_category"]
        for case in FIXTURES
    )
    assert correct >= 19


def test_university_beats_high_school_when_both_present():
    result = classify_pathway_category("○○高等学校を経て△△大学に進学した。")
    assert result.pathway_category == "university"
    assert result.confidence == "high"


def test_high_school_alone_is_high_confidence():
    result = classify_pathway_category("○○高等学校でプレーし、卒業後にプロ入りした。")
    assert result.pathway_category == "high_school"
    assert result.confidence == "high"


def test_incidental_schooling_around_club_academy_flags_for_review():
    result = classify_pathway_category(
        "監督に誘われ○○U-18に入団。距離があるため○○高等学校に進学し寮生活を送った。"
    )
    assert result.confidence == "needs_review"
    assert result.reason == "possible_incidental_schooling_around_club_academy"


def test_plain_school_and_club_co_occurrence_does_not_flag_for_review():
    """Most bios mention a childhood/JHS club before an independently-chosen high
    school in ordinary chronological order — that alone is not the ambiguous case
    (docs/pathway_source_pilot_2026-07-03.md's 森重真人 case: he explicitly missed
    academy promotion and chose a separate high school), so it should resolve to
    the terminal (highest-priority) stage with high confidence, not be flagged."""
    result = classify_pathway_category(
        "サンフレッチェ広島ジュニアユースに所属したが、ユースの昇格を逃す。"
        "高校からの方がプロ入りに近付けると考え、広島皆実高校に進学。"
    )
    assert result.pathway_category == "high_school"
    assert result.confidence == "high"


def test_j_club_academy_alone_is_high_confidence():
    result = classify_pathway_category("○○ユースに所属し、昇格してトップチームに入団した。")
    assert result.pathway_category == "j_club_academy"
    assert result.confidence == "high"


def test_overseas_relocation_without_domestic_institution_flags_for_review():
    result = classify_pathway_category(
        "10歳の時にドイツに移住し、現地クラブの下部組織でサッカーを始めた。"
    )
    assert result.confidence == "needs_review"
    assert result.reason == "overseas_relocation_language_no_domestic_institution"


def test_no_institution_keyword_is_unknown():
    result = classify_pathway_category("2018年にプロデビューした。")
    assert result.pathway_category == "unknown"


def test_empty_context_is_unknown_high_confidence():
    result = classify_pathway_category("")
    assert result.pathway_category == "unknown"
    assert result.confidence == "high"


def test_build_pathway_label_row_labels_confirmed_rows():
    row = build_pathway_label_row(candidate_row(), "wikipedia_pathway_context")
    assert row["pathway_category"] == "high_school"
    assert row["pathway_confidence"] == "high"


def test_build_pathway_label_row_leaves_unconfirmed_rows_blank():
    row = build_pathway_label_row(
        candidate_row(identity_check="birth_date_mismatch"), "wikipedia_pathway_context"
    )
    assert row["pathway_category"] == ""
    assert row["pathway_reason"] == "identity_not_confirmed"


def test_bare_koukou_age_reference_is_not_a_named_school():
    """"高校2年時" is a relative-age reference, not a named school (docs/pathway_
    source_pilot_2026-07-03.md's 中谷進之介 case never names a high school at all,
    only uses this age-reference form) — it should not count as high_school
    evidence, leaving j_club_academy as the only real signal."""
    result = classify_pathway_category("小学4年時から○○の下部組織に加入。高校2年時に主将を務めた。")
    assert result.pathway_category == "j_club_academy"
    assert result.confidence == "high"


def test_build_pathway_review_queue_rows_only_includes_needs_review():
    labeled_rows = [
        {
            "source_player_id": "1",
            "name_ja": "高信頼度太郎",
            "name_en": "",
            "wikipedia_title": "高信頼度太郎",
            "pathway_category": "high_school",
            "pathway_matched_categories": "high_school",
            "pathway_reason": "single_stage_tier_matched",
            "pathway_confidence": "high",
        },
        {
            "source_player_id": "2",
            "name_ja": "要確認次郎",
            "name_en": "",
            "wikipedia_title": "要確認次郎",
            "pathway_category": "high_school",
            "pathway_matched_categories": "high_school|j_club_academy",
            "pathway_reason": "possible_incidental_schooling_around_club_academy",
            "pathway_confidence": "needs_review",
        },
    ]
    rows = build_pathway_review_queue_rows(
        labeled_rows, {"2": "寮生活を送った。"}, tier="a"
    )
    assert len(rows) == 1
    assert rows[0]["source_player_id"] == "2"
    assert rows[0]["tier"] == "a"
    assert rows[0]["wikipedia_pathway_context"] == "寮生活を送った。"
    assert rows[0]["reviewed_pathway_category"] == ""
    assert rows[0]["reviewer_note"] == ""


# --- Guards from the Phase 1b era-1 pilot (docs/pre2014_pathway_pilot_2026-07-19.md).
# Pre-2014-only players' articles are dominated by post-playing careers, which produced
# three silent-wrong modes Phase 1's golden 22 never hit.


def test_coaching_role_mention_is_not_academy_evidence():
    # 栗山裕貴: no development history in the article; the only academy-like keyword is
    # a later coaching job. Must fall through to unknown, not j_club_academy.
    result = classify_pathway_category("2014年に移籍。同年限りで現役を引退し、U-15監督に就任。")
    assert result.pathway_category == "unknown"
    result = classify_pathway_category("引退後はアカデミースタッフを務めた。")
    assert result.pathway_category == "unknown"


def test_coaching_mask_keeps_real_academy_evidence():
    result = classify_pathway_category("ユースから昇格。引退後はユースコーチに就任。")
    assert result.pathway_category == "j_club_academy"
    assert result.confidence == "high"


def test_university_entry_after_pro_entry_flags_for_review():
    # 石原卓: pro entry 2007, released, THEN 2009 university. Priority alone would
    # silently pick university; the year order must route it to review.
    result = classify_pathway_category(
        "高校を経て2007年、横浜F・マリノスへ入団。2008年に戦力外。2009年、中京大学に入学しプレーした。"
    )
    assert result.pathway_category == "university"
    assert result.confidence == "needs_review"
    assert result.reason == "university_entry_after_pro_entry"


def test_university_before_pro_entry_stays_high_confidence():
    # 平松大志-shaped normal order: university first, pro entry later.
    result = classify_pathway_category(
        "帝京高校を経て2002年に中央大学へ進学した。2006年、水戸ホーリーホックへ入団。"
    )
    assert result.pathway_category == "university"
    assert result.confidence == "high"


def test_youth_dual_enrollment_school_is_j_club_academy():
    # 吉澤佑哉: 鹿島アントラーズユース（鹿島高校） — the parenthesized school is the
    # academy's partner school, so this is j_club_academy (SAP §3 addendum 2026-07-20).
    result = classify_pathway_category(
        "鹿島アントラーズユース（鹿島高校）出身。2005年にプロ契約。"
    )
    assert result.pathway_category == "j_club_academy"
    assert result.reason == "youth_dual_enrollment_school"


# --- Phase 1b measurement-equivalence fixes (docs/measurement_equivalence_phase1b_2026-07-20.md).
# Mechanisms A/B/C/D found by the era-stratified gold sets. Each test encodes the mechanism,
# not the specific player, so they guard against the class of error.


def test_university_affiliated_high_school_is_not_university():
    # Mechanism A: 大学 inside an affiliated-HS name (三渡洲舞人, 野田恭平).
    r = classify_pathway_category("ユースから流通経済大学付属柏高校へ入学。2005年にプロ入り。")
    assert r.pathway_category == "high_school"
    r = classify_pathway_category("日本大学高校在学中に強化指定選手としてプロ登録。")
    assert r.pathway_category == "high_school"


def test_koukousei_age_phrase_does_not_beat_youth():
    # Mechanism B: 高校生 age bracket must not outrank a 下部組織 signal (福島新太).
    r = classify_pathway_category(
        "小学生〜高校生年代ではU-12、U-15、U-18と一貫して名古屋の下部組織に所属。トップチームに昇格。"
    )
    assert r.pathway_category == "j_club_academy"


def test_youth_to_top_promotion_overrides_high_school():
    # Mechanism C (SAP §3 addendum): youth + top-team promotion = j_club_academy even
    # with a co-occurring high school (籾谷真弘, 數馬正浩).
    r = classify_pathway_category(
        "高校時代は堺市立工業高校に通いながらセレッソ大阪のユースに所属。2000年にトップチームに昇格。"
    )
    assert r.pathway_category == "j_club_academy"
    assert r.confidence == "high"
    assert r.reason == "youth_to_top_team_promotion"
    r = classify_pathway_category("横浜Fマリノスユースからトップチームへ昇格。高校卒業後にデビュー。")
    assert r.pathway_category == "j_club_academy"


def test_high_school_recruit_not_flipped_by_promotion_rule():
    # A high-school player joins via 入団/加入, never 昇格 — must stay high_school.
    r = classify_pathway_category("帝京高校から2006年に水戸ホーリーホックへ入団。")
    assert r.pathway_category == "high_school"


def test_declined_university_offer_routes_to_review():
    # Mechanism D: a declined university offer must not be a silent university label (鎌田大地).
    r = classify_pathway_category(
        "帝京高校で得点王。複数の強豪大学から誘いを受けるが、プロ入りを選んだ。"
    )
    assert r.confidence == "needs_review"
    assert r.reason == "possible_declined_university_offer"


def test_failed_promotion_does_not_flip_to_academy():
    # 端山豪: "トップチームに昇格することはかなわなかった" — negated promotion, then
    # university. Must not become j_club_academy (mechanism F).
    r = classify_pathway_category(
        "東京ヴェルディの下部組織出身。トップチームに昇格することはかなわなかった。"
        "高等学校卒業後は慶應義塾大学へ進学。大学在学中にプロ入り。"
    )
    assert r.pathway_category != "j_club_academy"


def test_opponent_university_name_is_not_own_university():
    # 野崎雅也: "宮崎産業経営大学戦" is an opponent, not his university; he is a Urawa
    # youth product promoted to the top team (mechanism E).
    r = classify_pathway_category(
        "浦和レッズユース所属時にトップ昇格が内定。天皇杯の宮崎産業経営大学戦で公式戦初出場。"
    )
    assert r.pathway_category == "j_club_academy"


def test_university_championship_is_still_university_evidence():
    # Guard against over-masking: 大学選手権 / 大学サッカー is real university play.
    r = classify_pathway_category("流通経済大学に進学し、全日本大学サッカー選手権で優勝。")
    assert r.pathway_category == "university"


def test_negated_promotion_su_zu_forms_do_not_flip():
    # 神山京右/橋本健人 "昇格せず...大学へ", 宇佐美 "昇格はならず...大学に" — classical
    # ~ず negation forms the first guard missed (mechanism F, extended).
    r = classify_pathway_category(
        "横浜FCのアカデミー出身。高校卒業後はトップチームに昇格せず東洋大学に進学。"
    )
    assert r.pathway_category != "j_club_academy"
    r = classify_pathway_category(
        "セレッソ大阪の下部組織に所属したが、トップ昇格はならず、関西大学に進学した。"
    )
    assert r.pathway_category != "j_club_academy"


def test_youth_promotion_competing_with_university_routes_to_review():
    # 矢田旭: "トップチーム昇格が具体化しかけたが" (not a clean negation word) then
    # university. When university competes, the flip is unreliable -> review, not academy.
    r = classify_pathway_category(
        "名古屋グランパスの下部組織で活躍。トップチーム昇格が具体化しかけたが、"
        "最終的に大学へ進学しゲームメーカーに成長した。"
    )
    assert r.confidence == "needs_review"
    assert r.reason == "youth_promotion_vs_university_ambiguous"
