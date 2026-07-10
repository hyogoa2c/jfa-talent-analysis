from jfa_talent_analysis.overseas_classification import classify_overseas_stint

# Sentences below are real phrasings from this project's fetched Wikipedia corpus.


def test_named_foreign_league_with_move_verb():
    result = classify_overseas_stint(
        "2016年8月12日、エールディヴィジ・SCヘーレンフェーンへ完全移籍することを発表した。"
    )
    assert result.moved_overseas == "yes"
    assert result.confidence == "high"


def test_country_division_pattern():
    result = classify_overseas_stint("2021年、Kリーグ2（韓国2部）のFC安養に完全移籍。")
    assert result.moved_overseas == "yes"
    assert result.confidence == "high"


def test_country_club_move_pattern():
    result = classify_overseas_stint(
        "2025年7月9日、5年契約でデンマークのFCコペンハーゲンへ完全移籍加入することが発表された。"
    )
    assert result.moved_overseas == "yes"
    assert result.confidence == "high"


def test_short_study_abroad_is_not_a_move():
    result = classify_overseas_stint("1999年、シーズン終了を待たずチームから離脱し、ブラジルへ短期留学。")
    assert result.moved_overseas == "no"


def test_parents_relocation_is_not_a_move():
    result = classify_overseas_stint(
        "1996年から父の移籍に伴いドイツへ渡り、同年5歳の時にサッカーを始める。"
    )
    assert result.moved_overseas == "no"


def test_someone_elses_overseas_move_is_not_a_move():
    result = classify_overseas_stint(
        "8月、チームキャプテンの伊藤敦樹の海外移籍により、2シーズンぶりのキャプテンに就任した。"
    )
    assert result.moved_overseas == "no"


def test_own_generic_overseas_challenge_counts():
    result = classify_overseas_stint("2019年6月、海外再挑戦を目的にクラブと合意の元契約解除。")
    assert result.moved_overseas == "yes"


def test_youth_academy_abroad_is_not_a_senior_move():
    result = classify_overseas_stint(
        "2014年8月12日にシャルケ04のU-17チームに移籍し、デビュー戦でゴールを決めた。"
    )
    assert result.moved_overseas == "no"


def test_failed_trial_is_flagged_not_trusted():
    result = classify_overseas_stint(
        "2008年3月にリーグ・アンのFCメスの入団テストを受験するも不合格。"
    )
    assert result.confidence == "needs_review"


def test_bare_country_with_move_verb_is_weak_signal():
    result = classify_overseas_stint(
        "2017年からアルビレックス新潟シンガポールに完全移籍により加入した。"
    )
    assert result.moved_overseas == "yes"
    assert result.confidence == "needs_review"
    assert result.reason == "weak_country_move_signal_only"


def test_no_signal_is_high_confidence_no():
    result = classify_overseas_stint("2018年にプロデビューし、国内クラブで活躍した。")
    assert result.moved_overseas == "no"
    assert result.confidence == "high"


def test_chugoku_regional_league_is_not_china():
    """"中国サッカーリーグ"/"中国リーグ" is a real *domestic* Japanese regional
    league (Chugoku region), not a China move — a real corpus false-positive
    pattern (福山シティFC, レノファ山口FC, ベルガロッソいわみ etc., all based in
    Japan)."""
    result = classify_overseas_stint("2022年、中国サッカーリーグのFCバレイン下関へ加入した。")
    assert result.moved_overseas == "no"

    result = classify_overseas_stint("2010年、当時中国リーグに所属していたレノファ山口FCに移籍。")
    assert result.moved_overseas == "no"


def test_genuine_china_move_still_detected():
    result = classify_overseas_stint("2023年、中国スーパーリーグの上海海港へ完全移籍。")
    assert result.moved_overseas == "yes"
    assert result.confidence == "high"
