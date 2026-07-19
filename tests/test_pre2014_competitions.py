from jfa_talent_analysis.pre2014_competitions import (
    CATEGORY_CHAMPIONSHIP,
    CATEGORY_J1_LEAGUE,
    CATEGORY_J2_LEAGUE,
    CATEGORY_LEAGUE_CUP,
    CATEGORY_PROMOTION_PLAYOFF,
    CATEGORY_RELEGATION_PLAYOFF,
    CATEGORY_SATELLITE,
    CATEGORY_UNCLASSIFIED,
    classify_competition_label,
    is_league_competition,
)

# Raw (pre-NFKC) label variants observed in the source audit's competition table.
OBSERVED_LABELS = {
    "１９９９Ｊリーグ　ディビジョン１　１ｓｔステージ": CATEGORY_J1_LEAGUE,
    "１９９９Ｊリーグ　ディビジョン１　２ｎｄステージ": CATEGORY_J1_LEAGUE,
    "２００５Ｊリーグ　ディビジョン１": CATEGORY_J1_LEAGUE,
    "１９９９Ｊリーグ　ディビジョン２": CATEGORY_J2_LEAGUE,
    "’９９Ｊリーグ　ヤマザキナビスコカップ": CATEGORY_LEAGUE_CUP,
    "２００５Ｊリーグヤマザキナビスコカップ 予選リーグ": CATEGORY_LEAGUE_CUP,
    "２０１３Ｊリーグヤマザキナビスコカップ　決勝トーナメント": CATEGORY_LEAGUE_CUP,
    "１９９９Ｊリーグ　サントリーチャンピオンシップ": CATEGORY_CHAMPIONSHIP,
    "２００５Ｊ１・Ｊ２入れ替え戦": CATEGORY_RELEGATION_PLAYOFF,
    "２０１３Ｊ２・ＪＦＬ入れ替え戦": CATEGORY_RELEGATION_PLAYOFF,
    "２０１３Ｊ１昇格プレーオフ": CATEGORY_PROMOTION_PLAYOFF,
    "２００５Ｊサテライトリーグ　Ａグループ": CATEGORY_SATELLITE,
}


def test_observed_labels_classify() -> None:
    for label, expected in OBSERVED_LABELS.items():
        assert classify_competition_label(label) == expected, label


def test_is_league_competition_reproduces_sfpr01_universe() -> None:
    league = {label for label in OBSERVED_LABELS if is_league_competition(label)}
    assert league == {
        "１９９９Ｊリーグ　ディビジョン１　１ｓｔステージ",
        "１９９９Ｊリーグ　ディビジョン１　２ｎｄステージ",
        "２００５Ｊリーグ　ディビジョン１",
        "１９９９Ｊリーグ　ディビジョン２",
    }


def test_unknown_label_is_unclassified_not_league() -> None:
    assert classify_competition_label("2013 謎の大会") == CATEGORY_UNCLASSIFIED
    assert not is_league_competition("2013 謎の大会")
